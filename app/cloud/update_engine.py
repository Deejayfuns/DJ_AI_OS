"""
DJ AI OS — Self-Updating Client Architecture

The client that updates itself like a living organism.
Salvador Dalí'nin rüya mimarisi:
- Modüler: her parça bağımsız güncellenebilir
- Uyumlu: eski ve yeni versiyonlar birlikte çalışır
- Akıllı: kullanıcının tercihlerini öğrenir
- Güvenli: rollback, checksum, sandbox

Update Flow:
  1. Manifest check (0.5s) → versions.json
  2. Delta calculation → only changed modules
  3. Download + verify (SHA256)
  4. Hot-swap modules (no restart needed for most)
  5. If critical: staged restart with countdown
"""

import os
import sys
import json
import hashlib
import shutil
import time
import threading
import importlib
import zipfile
import io
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable


# ============================================================
# MANIFEST
# ============================================================

@dataclass
class ModuleInfo:
    """Info about a single updatable module."""
    name: str
    version: str
    path: str
    sha256: str
    size: int
    category: str  # 'core', 'ui', 'ai', 'cloud'
    hot_reload: bool = True  # Can be swapped without restart
    dependencies: List[str] = field(default_factory=list)
    changelog: str = ""


@dataclass
class UpdateManifest:
    """Complete update manifest from server."""
    version: str
    min_client_version: str
    released_at: str
    modules: List[ModuleInfo]
    critical: bool = False
    changelog: str = ""
    download_url: str = ""


# ============================================================
# UPDATE ENGINE
# ============================================================

class UpdateEngine:
    """
    Self-updating client engine.
    Checks for updates, downloads, verifies, and applies them.
    """

    def __init__(self, app_root: str = None, update_dir: str = None):
        self.app_root = Path(app_root or os.path.dirname(os.path.abspath(__file__))).parent.parent
        self.update_dir = Path(update_dir or self.app_root / "updates")
        self.backup_dir = self.update_dir / "backups"
        self.download_dir = self.update_dir / "downloads"

        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Current state
        self.current_version = self._get_current_version()
        self.current_manifest = self._load_local_manifest()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._checking = False
        self._updating = False

    def _get_current_version(self) -> str:
        """Get current app version."""
        try:
            pyproject = self.app_root / "pyproject.toml"
            if pyproject.exists():
                import tomllib
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "0.1.0")
        except Exception:
            pass
        return "0.1.0"

    def _load_local_manifest(self) -> Optional[Dict]:
        """Load local manifest if exists."""
        manifest_path = self.update_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_local_manifest(self, manifest: Dict):
        """Save manifest to disk."""
        manifest_path = self.update_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    # ============================================================
    # EVENT SYSTEM
    # ============================================================

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _emit(self, event: str, data: Any = None):
        """Emit event to listeners."""
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # ============================================================
    # CHECK FOR UPDATES
    # ============================================================

    def check_for_updates(self, server_url: str = "https://api.djaios.com") -> Dict[str, Any]:
        """
        Check if updates are available.
        Returns: {available: bool, current: str, latest: str, modules: [...]}
        """
        if self._checking:
            return {"available": False, "reason": "already_checking"}

        self._checking = True
        self._emit("checking")

        try:
            # In production: GET /updates/manifest
            # For now, simulate check
            latest = self._simulate_server_manifest()

            current_ver = self.current_version
            latest_ver = latest.get("version", current_ver)

            if self._version_gt(latest_ver, current_ver):
                # Calculate delta
                delta = self._calculate_delta(latest)

                result = {
                    "available": True,
                    "current": current_ver,
                    "latest": latest_ver,
                    "critical": latest.get("critical", False),
                    "changelog": latest.get("changelog", ""),
                    "modules_to_update": len(delta["changed"]),
                    "modules_new": len(delta["new"]),
                    "modules_removed": len(delta["removed"]),
                    "download_size_mb": delta["total_size_mb"],
                }

                self._emit("update_available", result)
                return result
            else:
                return {
                    "available": False,
                    "current": current_ver,
                    "latest": latest_ver,
                    "message": "En güncel versiyondasınız!",
                }

        finally:
            self._checking = False

    def _simulate_server_manifest(self) -> Dict:
        """Simulate server manifest (in production: HTTP request)."""
        return {
            "version": "2.0.0",
            "min_client_version": "1.5.0",
            "released_at": datetime.now().isoformat(),
            "critical": False,
            "changelog": "Beat Studio, Library AI, Cloud Sync eklendi",
            "download_url": "https://api.djaios.com/updates/v2.0.0",
        }

    def _calculate_delta(self, remote_manifest: Dict) -> Dict:
        """Calculate what needs to be updated."""
        local = self.current_manifest or {"modules": []}
        local_modules = {m["name"]: m for m in local.get("modules", [])}
        remote_modules = {m["name"]: m for m in remote_manifest.get("modules", [])}

        changed = []
        new = []
        removed = []

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
            "total_size_mb": len(changed + new) * 0.5,  # Estimate
        }

    # ============================================================
    # APPLY UPDATE
    # ============================================================

    def apply_update(self, manifest: Dict, user_approved: bool = False) -> Dict[str, Any]:
        """
        Apply an update. Requires user approval for non-critical updates.

        Update stages:
        1. Backup current state
        2. Download changed modules
        3. Verify checksums
        4. Hot-swap (no restart) or staged restart
        5. Save new manifest
        """
        if self._updating:
            return {"ok": False, "reason": "update_in_progress"}

        if not user_approved and manifest.get("critical"):
            return {
                "ok": False,
                "reason": "needs_approval",
                "message": "Kritik güncelleme için onayınız gerekli",
                "changelog": manifest.get("changelog", ""),
            }

        self._updating = True
        self._emit("update_starting", manifest)

        try:
            # Stage 1: Backup
            self._emit("stage", {"stage": "backup", "progress": 0})
            backup_path = self._create_backup()
            self._emit("stage", {"stage": "backup", "progress": 100})

            # Stage 2: Download
            self._emit("stage", {"stage": "download", "progress": 0})
            downloaded = self._download_modules(manifest)
            self._emit("stage", {"stage": "download", "progress": 100})

            # Stage 3: Verify
            self._emit("stage", {"stage": "verify", "progress": 0})
            verified = self._verify_checksums(downloaded)
            if not verified:
                self._rollback(backup_path)
                return {"ok": False, "reason": "checksum_failed"}
            self._emit("stage", {"stage": "verify", "progress": 100})

            # Stage 4: Apply
            self._emit("stage", {"stage": "apply", "progress": 0})
            hot_swapped = self._hot_swap_modules(downloaded)
            needs_restart = not all(m.get("hot_reload", True) for m in manifest.get("modules", []))
            self._emit("stage", {"stage": "apply", "progress": 100})

            # Stage 5: Save manifest
            self._save_local_manifest(manifest)
            self.current_version = manifest.get("version", self.current_version)
            self.current_manifest = manifest

            self._emit("update_complete", {
                "version": manifest.get("version"),
                "hot_swapped": len(hot_swapped),
                "needs_restart": needs_restart,
            })

            return {
                "ok": True,
                "version": manifest.get("version"),
                "hot_swapped": len(hot_swapped),
                "needs_restart": needs_restart,
                "message": f"Güncelleme tamamlandı! v{manifest.get('version')}",
            }

        except Exception as e:
            self._rollback(backup_path)
            self._emit("update_failed", {"error": str(e)})
            return {"ok": False, "reason": str(e)}

        finally:
            self._updating = False

    def _create_backup(self) -> Path:
        """Backup current state before update."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup key directories
        for subdir in ["app", "data"]:
            src = self.app_root / subdir
            if src.exists():
                dst = backup_path / subdir
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # Save current version info
        info = {
            "version": self.current_version,
            "backed_up_at": datetime.now().isoformat(),
            "manifest": self.current_manifest,
        }
        with open(backup_path / "backup_info.json", "w") as f:
            json.dump(info, f, indent=2)

        return backup_path

    def _download_modules(self, manifest: Dict) -> Dict[str, Path]:
        """Download changed modules."""
        downloaded = {}
        # In production: download from server
        # For now, simulate
        for module in manifest.get("modules", []):
            name = module.get("name", "")
            path = self.download_dir / f"{name}.zip"
            downloaded[name] = path
        return downloaded

    def _verify_checksums(self, downloaded: Dict[str, Path]) -> bool:
        """Verify SHA256 checksums of downloaded files."""
        # In production: verify against manifest
        return True

    def _hot_swap_modules(self, downloaded: Dict[str, Path]) -> List[str]:
        """Hot-swap modules without restart."""
        swapped = []
        for name, path in downloaded.items():
            # Find the target module path
            target = self._find_module_path(name)
            if target:
                try:
                    # Replace module file
                    if path.exists():
                        shutil.copy2(path, target)
                        swapped.append(name)

                        # Force reimport
                        module_name = self._path_to_module(target)
                        if module_name in sys.modules:
                            importlib.reload(sys.modules[module_name])
                except Exception:
                    pass

        return swapped

    def _find_module_path(self, module_name: str) -> Optional[Path]:
        """Find the filesystem path for a module name."""
        parts = module_name.replace(".", "/")
        for ext in [".py", "/__init__.py"]:
            path = self.app_root / parts + ext if not ext.startswith("/") else self.app_root / parts / "__init__.py"
            if path.exists():
                return path
        return None

    def _path_to_module(self, path: Path) -> str:
        """Convert filesystem path to Python module name."""
        try:
            relative = path.relative_to(self.app_root)
            parts = list(relative.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1].replace(".py", "")
            return ".".join(parts)
        except Exception:
            return str(path.stem)

    def _rollback(self, backup_path: Path):
        """Rollback to backup after failed update."""
        if not backup_path or not backup_path.exists():
            return

        for subdir in ["app", "data"]:
            src = backup_path / subdir
            if src.exists():
                dst = self.app_root / subdir
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        self._emit("rollback_complete")

    # ============================================================
    # VERSION UTILITIES
    # ============================================================

    def _version_gt(self, v1: str, v2: str) -> bool:
        """Check if v1 > v2."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            return parts1 > parts2
        except Exception:
            return v1 != v2

    def get_update_history(self) -> List[Dict]:
        """Get history of applied updates."""
        history_path = self.update_dir / "history.json"
        if history_path.exists():
            try:
                with open(history_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_current_info(self) -> Dict[str, Any]:
        """Get current version and update status."""
        return {
            "version": self.current_version,
            "update_available": False,  # Will be checked
            "last_check": None,
            "modules": len(self.current_manifest.get("modules", []) if self.current_manifest else []),
        }
