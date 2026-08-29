#!/usr/bin/env python3
"""
DJ AI OS — Test license generator (offline, ephemeral keys).

Kullanım:
    python tools/gen_test_license.py --plan ENTERPRISE --output test_license.json
    python tools/gen_test_license.py --plan PRO --machine-id <id> --expiry-days 30

Üretilen lisans SADECE test için geçerlidir (ephemeral keypair).
Production lisansı için vendor private key (tools/keygen.py) gerekir.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.license import signature as sig
from app.license.machine_id import MachineID


def generate_ephemeral_keypair():
    """Test için geçici Ed25519 keypair."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def build_payload(
    plan: str,
    machine_id: str,
    expiry_days: int = 365,
    max_tracks: int = None,
    updates_until_days: int = 90,
    email: str = "test@dj.local",
):
    """Lisans payload oluştur."""
    now = datetime.now(timezone.utc)
    if max_tracks is None:
        max_tracks = 0 if plan == "ENTERPRISE" else 50000

    return {
        "email": email,
        "machine_id": machine_id,
        "plan": plan,
        "expiry": (now + timedelta(days=expiry_days)).strftime("%Y-%m-%d"),
        "max_tracks": max_tracks,
        "updates_until": (now + timedelta(days=updates_until_days)).strftime("%Y-%m-%d"),
        "issued_at": now.isoformat(),
        "nonce": "test" + "a" * 28,
    }


def main():
    parser = argparse.ArgumentParser(description="Test license generator")
    parser.add_argument(
        "--plan",
        choices=["DEMO", "PRO", "DJ_ARCHIVE", "STUDIO", "ENTERPRISE"],
        default="ENTERPRISE",
        help="Plan adı (default: ENTERPRISE - en üst paket)",
    )
    parser.add_argument(
        "--machine-id",
        default=None,
        help="Hedef makine ID (default: current machine)",
    )
    parser.add_argument(
        "--expiry-days",
        type=int,
        default=365,
        help="Lisans geçerlilik gün sayısı",
    )
    parser.add_argument(
        "--updates-days",
        type=int,
        default=90,
        help="Updates active gün sayısı",
    )
    parser.add_argument(
        "--max-tracks",
        type=int,
        default=None,
        help="Max tracks (None = plan default)",
    )
    parser.add_argument(
        "--email",
        default="test@dj.local",
        help="E-posta",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Çıktı dosyası (default: stdout)",
    )
    parser.add_argument(
        "--use-current-machine",
        action="store_true",
        help="Bu makinenin machine_id'sini kullan",
    )
    parser.add_argument(
        "--print-pubkey",
        action="store_true",
        help="Test public key'i bastır (client doğrulaması için)",
    )
    args = parser.parse_args()

    # Machine ID
    if args.machine_id:
        machine_id = args.machine_id
    elif args.use_current_machine:
        machine_id = MachineID().generate()
    else:
        machine_id = MachineID().generate()

    # Ephemeral keypair
    private_pem, public_pem = generate_ephemeral_keypair()

    # Payload
    payload = build_payload(
        plan=args.plan,
        machine_id=machine_id,
        expiry_days=args.expiry_days,
        max_tracks=args.max_tracks,
        updates_until_days=args.updates_days,
        email=args.email,
    )

    # Sign
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)

    # Output
    output_json = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"[OK] Test license yazıldı: {args.output}")
        print(f"   Plan: {args.plan}")
        print(f"   Machine: {machine_id[:32]}...")
        print(f"   Expiry: {payload['expiry']}")
    else:
        print(output_json)

    if args.print_pubkey:
        print("\n=== TEST PUBLIC KEY (client doğrulaması için) ===")
        print(public_pem)
        print("=== PUBLIC KEY END ===")

    # Usage hint
    print("\n--- KULLANIM ---")
    print("1. Account -> OFFLINE LİSANS YÜKLE -> DOSYA SEÇ veya JSON yapıştır")
    print("2. Veya kodda:")
    print(f"   from app.license.license_manager import LicenseManager")
    print(f"   lm = LicenseManager()")
    print(f"   lm.license_file = 'test_license.json'")
    print(f"   lm.owner_dev_mode = False")
    print(f"   print(lm.get_plan())")


if __name__ == "__main__":
    main()