#!/usr/bin/env python3
"""
DJ AI OS — imzalı update manifest + modül paketi üretici (vendor makinesi).

Mevcut kaynaktan güncellenebilir modül listesini tarar, her modül için sha256
ve boyut hesaplar, manifest'i vendor key ile imzalar ve `updates/` klasörüne
yazar. Çevrimdışı test: çıkan klasörü `python -m http.server` ile sunun veya
`file://` base URL'i ile engine'e verin.

Kullanım:
    python tools/build_manifest.py                              # varsayılan modüller
    python tools/build_manifest.py --version 0.2.0 --add app/ui/main_window.py
    python tools/build_manifest.py --list                       # varsayılan modül listesi

NOT: Bu araç YALNIZCA vendor makinesinde çalışır (private key gerekir).
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
OUT_DIR = PROJECT_ROOT / "updates"

# Varsayılan güncellenebilir modül seti (Faz 1 yüzeyi).
DEFAULT_MODULES = [
    "app/config/version.py",
    "app/config/vendor_public_key.py",
    "app/license/signature.py",
    "app/license/license_manager.py",
    "app/license/license_schema.py",
    "app/license/entitlements.py",
    "app/license/machine_id.py",
    "app/cloud/update_engine.py",
    "app/cloud/commercial_api.py",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(version, modules, download_url, changelog, critical):
    manifest = {
        "version": version,
        "min_client_version": "0.1.0",
        "released_at": None,  # üretim zamanı DateTime; sadece gösterim
        "critical": critical,
        "changelog": changelog or "",
        "download_url": download_url,
        "modules": [],
    }

    missing = []
    for mod in modules:
        src = PROJECT_ROOT / mod
        if not src.exists():
            missing.append(mod)
            continue
        manifest["modules"].append({
            "name": mod,
            "version": version,
            "sha256": sha256_of(src),
            "size": src.stat().st_size,
            "hot_reload": False,
        })

    if missing:
        print("Eksik modüller (atlandı):")
        for m in missing:
            print(f"  - {m}")

    return manifest


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from app.config.version import APP_VERSION
    from app.license import signature

    parser = argparse.ArgumentParser(description="DJ AI OS imzalı manifest üretici")
    parser.add_argument("--version", default=f"{APP_VERSION.rsplit('.', 1)[0]}.{int(APP_VERSION.rsplit('.', 1)[1]) + 1}",
                        help="manifest sürümü (varsayılan: APP_VERSION'un bir sonraki patch'i)")
    parser.add_argument("--add", action="append", default=[],
                        help="varsayılan listeye ek modül yolu (tekrar edilebilir)")
    parser.add_argument("--list", action="store_true",
                        help="varsayılan modül listesini bas ve çık")
    parser.add_argument("--download-url",
                        default="https://api.dj-ai-os.example/updates",
                        help="modül indirme base URL'i (offline test: file://<mutlak yok> veya http://localhost:PORT/updates)")
    parser.add_argument("--changelog", default="")
    parser.add_argument("--critical", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("\n".join(DEFAULT_MODULES))
        return

    modules = list(DEFAULT_MODULES) + [m for m in args.add if m not in DEFAULT_MODULES]
    manifest = build_manifest(
        args.version, modules, args.download_url, args.changelog, args.critical,
    )
    manifest["signature"] = signature.sign(manifest)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mod_dir = OUT_DIR / "modules"
    mod_dir.mkdir(parents=True, exist_ok=True)

    for mod in manifest["modules"]:
        src = PROJECT_ROOT / mod["name"]
        dst = mod_dir / mod["name"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )

    total = sum(m["size"] for m in manifest["modules"])
    print(f"[OK] Manifest: {OUT_DIR / 'manifest.json'}")
    print(f"  version={manifest['version']}  critical={manifest['critical']}  modules={len(manifest['modules'])}")
    print(f"  toplam {total:,} bayt")
    print("\nSunucu gerekmeden test:  python -m http.server 8080 -d updates")
    print(f"  engine offline_dir: {OUT_DIR}  veya  download_url=http://localhost:8080/updates")


if __name__ == "__main__":
    main()
