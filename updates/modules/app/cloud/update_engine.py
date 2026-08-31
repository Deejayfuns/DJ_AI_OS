"""
DJ AI OS — Self-Updating Client (lisanslı kullanıcılar için)

Sadece `updates_active` entitlement'ı açık olan lisanslı kullanıcılar update
alabilir. DEMO/aktif olmayan lisans reddedilir.

Update Flow:
  1. updates_active gate (entitlement)
  2. Manifest check (HTTP /update/manifest VEYA offline_dir dosyası)
  3. Manifest imzasını gömülü vendor public key ile doğrula (Ed25519)
  4. min_client_version kontrolü
  5. Delta hesabı → sadece değişen modüller
  6. İndir (HTTP / file://) → SHA256 doğrula
  7. Atomic swap (backup → .new yaz → os.replace) → hata olursa rollback
  8. Kritik update otomatik uygulanır; kritik olmayan kullanıcı onayı ister

Güvenlik: imza private key'i gerektirir; client'ta sadece public key vardır.
Manifest kurcalanırsa veya imzasızsa uygulama REDDEDİLİR.
"""

import hashlib
import json
import os
import shutil
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from app.config.version import APP_VERSION
from app.license import signature as sig


class UpdateError(Exception):
    """Update akışındaki beklenen hatalar için."""


class UpdateEngine:
    """
    Kendini güncelleyen client motoru (yalnızca lisanslı/aktif update).
    """

    def __init__(self, app_root: str = None, update_dir: str = None):
        self.app_root = Path(app_root or self._default_app_root())
        self.update_dir = Path(update_dir or self._default_update_dir())
        self.backup_dir = self.update_dir / "backups"
        self.download_dir = self.update_dir / "downloads"

        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Current state
        self.current_version = APP_VERSION
        self.current_manifest = self._load_local_manifest()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._checking = False
        self._updating = False

    # -------------------------
    # PATHS
    # -------------------------

    @staticmethod
    def _default_app_root() -> Path:
        # app/cloud/update_engine.py -> repo/uygulama kökü (3 yukarı)
        return Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def _default_update_dir() -> Path:
        # Kullanıcı verisi: paketlenmiş build'de CWD/Program Files yazılamaz
        # olabileceği için %APPDATA%/DJ_AI_OS/updates kullanılır.
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "DJ_AI_OS" / "updates"

    def _load_local_manifest(self) -> Optional[Dict]:
        manifest_path = self.update_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_local_manifest(self, manifest: Dict):
        with open(self.update_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    # -------------------------
    # EVENT SYSTEM
    # -------------------------

    def on(self, event: str, callback: Callable):
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _emit(self, event: str, data: Any = None):
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # -------------------------
    # CHECK FOR UPDATES
    # -------------------------

    def check_for_updates(
        self,
        plan: Dict[str, Any],
        base_url: str = None,
        offline_dir: str = None,
    ) -> Dict[str, Any]:
        """
        Güncelleme var mı? Yalnızca updates_active kapısından geçen lisanslar.

        Returns: {available: bool, reason, current, latest, ...}
        """
        if self._checking:
            return {"available": False, "reason": "already_checking"}

        entitlements = (plan or {}).get("entitlements", {})
        if not entitlements.get("updates_active"):
            return {
                "available": False,
                "reason": "updates_not_active",
                "message": "Güncellemeler aktif değil — lisansını yenile.",
            }

        self._checking = True
        self._emit("checking")

        try:
            remote = self._fetch_manifest(base_url, offline_dir)
            if not remote:
                return {
                    "available": False,
                    "reason": "manifest_unavailable",
                    "message": "Update manifest'ine ulaşılamadı.",
                }

            if not self._verify_manifest_signature(remote):
                return {
                    "available": False,
                    "reason": "manifest_bad_signature",
                    "message": "Update manifest imzası geçersiz — reddedildi.",
                }

            latest = remote.get("version", "0.0.0")

            minc = remote.get("min_client_version")
            if minc and self._version_gt(minc, self.current_version):
                return {
                    "available": False,
                    "reason": "client_too_old",
                    "min_client_version": minc,
                    "message": (
                        f"Client sürümü eski ({self.current_version}); "
                        f"en az {minc} gerekli."
                    ),
                }

            if not self._version_gt(latest, self.current_version):
                return {
                    "available": False,
                    "current": self.current_version,
                    "latest": latest,
                    "message": "En güncel versiyondasınız.",
                }

            delta = self._calculate_delta(remote)
            result = {
                "available": True,
                "current": self.current_version,
                "latest": latest,
                "critical": bool(remote.get("critical")),
                "changelog": remote.get("changelog", ""),
                "download_url": remote.get("download_url", ""),
                "modules_to_update": len(delta["changed"]),
                "modules_new": len(delta["new"]),
                "modules_removed": len(delta["removed"]),
                "download_size_mb": delta["total_size_mb"],
                # apply_update'un kullanması için tam manifest
                "manifest": remote,
            }
            self._emit("update_available", result)
            return result

        finally:
            self._checking = False

    # ORB runtime (modules/cloud_module.py) uyumluluğu için takma ad.
    def check(self, plan: Dict[str, Any] = None) -> Dict[str, Any]:
        return self.check_for_updates(plan or {"entitlements": {}})

    def _fetch_manifest(self, base_url: str = None, offline_dir: str = None) -> Optional[Dict]:
        """Manifest'i offline klasörden veya HTTP /api/update/manifest'ten oku."""
        if offline_dir:
            manifest_path = Path(offline_dir) / "manifest.json"
            if manifest_path.exists():
                try:
                    return json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception:
                    return None
            return None

        if base_url:
            url = f"{base_url.rstrip('/')}/api/update/manifest"
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception:
                return None

        return None

    def _verify_manifest_signature(self, manifest: Dict) -> bool:
        if not isinstance(manifest, dict):
            return False
        return sig.verify(manifest, manifest.get("signature", ""))

    def _calculate_delta(self, remote_manifest: Dict) -> Dict:
        local = self.current_manifest or {"modules": []}
        local_modules = {m["name"]: m for m in local.get("modules", [])}
        remote_modules = {m["name"]: m for m in remote_manifest.get("modules", [])}

        changed, new, removed = [], [], []
        for name, remote_mod in remote_modules.items():
            if name in local_modules:
                if remote_mod.get("sha256") != local_modules[name].get("sha256"):
                    changed.append(name)
            else:
                new.append(name)

        for name in local_modules:
            if name not in remote_modules:
                removed.append(name)

        return {
            "changed": changed,
            "new": new,
            "removed": removed,
            "total_size_mb": round(
                sum(m.get("size", 0) for m in remote_manifest.get("modules", [])) / 1_048_576, 2
            ),
        }

    # -------------------------
    # APPLY UPDATE
    # -------------------------

    def apply_update(self, manifest: Dict, user_approved: bool = False) -> Dict[str, Any]:
        """
        Güncellemeyi uygula.

        Onay mantığı: KRİTİK update otomatik uygulanır (kullanıcı onayı
        gerekmez); kritik olmayan update kullanıcı onayı ister.

        Adımlar: manifest imza -> backup -> indir -> SHA256 -> atomic swap ->
        yerel manifest kaydet. Herhangi bir aşama başarısız olursa rollback.
        """
        if self._updating:
            return {"ok": False, "reason": "update_in_progress"}

        if not isinstance(manifest, dict):
            return {"ok": False, "reason": "invalid_manifest"}

        critical = bool(manifest.get("critical"))
        if not critical and not user_approved:
            return {
                "ok": False,
                "reason": "needs_approval",
                "message": "Güncelleme için onayınız gerekli.",
                "changelog": manifest.get("changelog", ""),
            }

        if not self._verify_manifest_signature(manifest):
            return {"ok": False, "reason": "manifest_bad_signature"}

        self._updating = True
        self._emit("update_starting", manifest)

        applied = []  # (target, backup_path) — rollback için
        try:
            # Stage 1: Backup metadata
            self._emit("stage", {"stage": "backup", "progress": 0})
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_root = self.backup_dir / f"backup_{stamp}"
            backup_root.mkdir(parents=True, exist_ok=True)
            self._emit("stage", {"stage": "backup", "progress": 100})

            # Stage 2: Download
            self._emit("stage", {"stage": "download", "progress": 0})
            downloaded = self._download_modules(manifest)
            self._emit("stage", {"stage": "download", "progress": 100})

            # Stage 3: Verify checksums
            self._emit("stage", {"stage": "verify", "progress": 0})
            if not self._verify_checksums(downloaded, manifest):
                raise UpdateError("checksum_failed")
            self._emit("stage", {"stage": "verify", "progress": 100})

            # Stage 4: Atomic swap
            self._emit("stage", {"stage": "apply", "progress": 0})
            swapped = self._apply_modules(downloaded, backup_root, applied)
            self._emit("stage", {"stage": "apply", "progress": 100})

            # Stage 5: Save manifest
            self._save_local_manifest(manifest)
            self.current_version = manifest.get("version", self.current_version)
            self.current_manifest = manifest

            self._emit("update_complete", {
                "version": manifest.get("version"),
                "hot_swapped": len(swapped),
                "needs_restart": True,
            })

            return {
                "ok": True,
                "version": manifest.get("version"),
                "hot_swapped": len(swapped),
                "needs_restart": True,
                "message": f"Güncelleme tamamlandı: v{manifest.get('version')}",
            }

        except UpdateError as e:
            self._rollback(applied)
            self._emit("update_failed", {"error": str(e)})
            return {"ok": False, "reason": str(e)}

        except Exception as e:
            self._rollback(applied)
            self._emit("update_failed", {"error": str(e)})
            return {"ok": False, "reason": str(e)}

        finally:
            self._updating = False

    def _download_modules(self, manifest: Dict) -> Dict[str, Path]:
        """Manifest'teki modülleri download_dir'e indir/kopyala."""
        base = manifest.get("download_url", "")
        downloaded = {}

        for mod in manifest.get("modules", []):
            name = mod.get("name", "")
            if not name:
                continue
            dst = self.download_dir / name
            dst.parent.mkdir(parents=True, exist_ok=True)

            if not self._fetch_module(base, name, dst):
                raise UpdateError(f"download_failed:{name}")

            downloaded[name] = dst

        return downloaded

    def _fetch_module(self, base: str, name: str, dst: Path) -> bool:
        """Modülü download_url'den (http/https/file) hedefe çek."""
        if not base:
            return False
        source = f"{base.rstrip('/')}/modules/{name}"

        try:
            if source.startswith("file://"):
                src_path = Path(source[len("file://"):])
                if not src_path.exists():
                    return False
                shutil.copyfile(src_path, dst)
                return True

            with urllib.request.urlopen(source, timeout=30) as resp:
                with open(dst, "wb") as out:
                    shutil.copyfileobj(resp, out)
                return True
        except Exception:
            return False

    def _verify_checksums(self, downloaded: Dict[str, Path], manifest: Dict) -> bool:
        modules = {m["name"]: m for m in manifest.get("modules", [])}
        for name, path in downloaded.items():
            expected = modules.get(name, {}).get("sha256")
            if not expected or self._sha256(path) != expected:
                return False
        return True

    def _apply_modules(
        self, downloaded: Dict[str, Path], backup_root: Path, applied: List
    ) -> List[str]:
        """
        Her modülü atomik değiştir: backup kopyala -> .new yaz -> os.replace.
        `applied` listesi rollback için (target, backup_path) çiftlerini toplar.
        """
        swapped = []
        for name, dl in downloaded.items():
            target = self._module_target(name)
            backup_path = backup_root / name
            had_original = target.exists()

            if had_original:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_path)

            target.parent.mkdir(parents=True, exist_ok=True)
            new_path = target.with_suffix(target.suffix + ".new")
            shutil.copy2(dl, new_path)
            os.replace(new_path, target)  # Windows'ta aynı sürücüde atomik

            applied.append((target, backup_path if had_original else None))
            swapped.append(name)

            self._reload_module(name)

        return swapped

    def _module_target(self, module_name: str) -> Path:
        """Manifest modül adını disk hedefine çevir: app_root / name."""
        return self.app_root / module_name

    def _find_module_path(self, module_name: str) -> Optional[Path]:
        """Eski/uyumluluk yöntemi: modül adından disk yolunu bul (TypeError düzeltildi)."""
        parts = module_name.replace(".", "/")
        for candidate in (
            self.app_root / f"{parts}.py",
            self.app_root / parts / "__init__.py",
        ):
            if candidate.exists():
                return candidate
        return None

    def _reload_module(self, name: str):
        """Modül import edilmişse reload dene (güvenli başarısız)."""
        try:
            import importlib
            import sys
            mod_name = name.replace("/", ".").replace("\\", ".").removesuffix(".py")
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        except Exception:
            pass

    def _rollback(self, applied: List):
        """Uygulanan modülleri backup'tan geri yükle (hata durumu)."""
        for target, backup_path in reversed(applied):
            try:
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, target)
                else:
                    if target.exists():
                        target.unlink()
            except Exception:
                pass
        self._emit("rollback_complete")

    # -------------------------
    # VERSION UTILITIES
    # -------------------------

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _version_gt(self, v1: str, v2: str) -> bool:
        try:
            p1 = [int(x) for x in str(v1).split(".")]
            p2 = [int(x) for x in str(v2).split(".")]
            return p1 > p2
        except Exception:
            return str(v1) != str(v2)

    def get_update_history(self) -> List[Dict]:
        history_path = self.update_dir / "history.json"
        if history_path.exists():
            try:
                with open(history_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_current_info(self) -> Dict[str, Any]:
        return {
            "version": self.current_version,
            "update_available": False,
            "last_check": None,
            "modules": len(self.current_manifest.get("modules", []) if self.current_manifest else []),
        }
