#!/usr/bin/env python3
"""
DJ AI OS — çevrimdışı imzalı lisans üretici (YALNIZCA vendor makinesi).

Kullanım:
    python tools/issue_license.py --email dj@example.com --plan PRO \
        --machine-id <64hex> --months 12 --out license.key

    python tools/issue_license.py --email x@y.com --plan ENTERPRISE \
        --machine-id <64hex> --expiry 2099-12-31 --updates-until 2099-12-31 \
        --max-tracks 0

Plan: DEMO | PRO | DJ_ARCHIVE | STUDIO | ENTERPRISE (entitlements.py ile aynı).
max_tracks plan varsayılanından (0 = sınırsız) devralınır, --max-tracks ile
ezilebilir. imza, signature.py'nin Ed25519 şemasıyla atılır — client bu imzayı
gömülü public key ile doğrular.
"""

import argparse
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# license_manager/entitlements ile aynı değerler (tek kaynak: entitlements.py)
import app.license.entitlements as entitlements_mod


def plan_defaults(plan):
    features = entitlements_mod.EntitlementManager.PLAN_FEATURES.get(
        str(plan or "").upper(), entitlements_mod.EntitlementManager.PLAN_FEATURES["DEMO"]
    )
    return features.get("max_tracks", 1000)


def build_license(email, plan, machine_id, months, expiry, updates_until, max_tracks):
    now = datetime.now(timezone.utc)

    if expiry:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
    else:
        expiry_date = now + timedelta(days=months * 30)

    if updates_until:
        updates_date = datetime.strptime(updates_until, "%Y-%m-%d")
    else:
        updates_date = now + timedelta(days=months * 30)

    if max_tracks is None:
        max_tracks = plan_defaults(plan)

    license_data = {
        "email": email,
        "machine_id": machine_id,
        "plan": str(plan or "").upper(),
        "expiry": expiry_date.strftime("%Y-%m-%d"),
        "max_tracks": int(max_tracks),
        "updates_until": updates_date.strftime("%Y-%m-%d"),
        "issued_at": now.isoformat(),
        "nonce": secrets.token_hex(16),
    }
    return license_data


def main():
    # Türkçe Windows konsolunda UTF-8 çıktısı için.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="DJ AI OS imzalı lisans üretici (vendor)")
    parser.add_argument("--email", required=True)
    parser.add_argument("--plan", required=True,
                        help="DEMO | PRO | DJ_ARCHIVE | STUDIO | ENTERPRISE")
    parser.add_argument("--machine-id", required=True,
                        help="Kullanıcının makine kimliği (Account ekranındaki MACHINE ID)")
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--expiry", help="YYYY-MM-DD (--months yerine)")
    parser.add_argument("--updates-until", help="YYYY-MM-DD (varsayılan: expiry)")
    parser.add_argument("--max-tracks", type=int, default=None,
                        help="0 = sınırsız; varsayılan plan değeri")
    parser.add_argument("--out", default=str(PROJECT_ROOT / "license.key"),
                        help="çıktı dosyası (varsayılan: ./license.key)")
    args = parser.parse_args()

    from app.license import signature

    license_data = build_license(
        args.email, args.plan, args.machine_id,
        args.months, args.expiry, args.updates_until, args.max_tracks,
    )
    license_data["signature"] = signature.sign(license_data)

    out_path = Path(args.out)
    out_path.write_text(
        json.dumps(license_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[OK] Lisans yazıldı: {out_path}")
    print(f"  plan={license_data['plan']}  max_tracks={license_data['max_tracks']}")
    print(f"  expiry={license_data['expiry']}  updates_until={license_data['updates_until']}")
    print(f"  machine_id={license_data['machine_id'][:16]}...")
    print(f"  signature={license_data['signature'][:24]}...")


if __name__ == "__main__":
    main()
