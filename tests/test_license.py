"""Lisans doğrulama + paket/limit testleri (app.license.license_manager)."""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from app.license import signature as sig
from app.license.license_manager import LicenseManager


@pytest.fixture
def keypair():
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


@pytest.fixture
def patched_pubkey(keypair):
    """Test public key'ini signature modülüne geçici göm (vendor key'ine dokunmaz)."""
    private_pem, public_pem = keypair
    original = sig.VENDOR_PUBLIC_KEY_PEM
    sig.VENDOR_PUBLIC_KEY_PEM = public_pem
    try:
        yield private_pem
    finally:
        sig.VENDOR_PUBLIC_KEY_PEM = original


def _manager(tmp_path):
    lm = LicenseManager()
    lm.license_file = str(tmp_path / "license.key")
    # Kaynak ağacı testlerini baypas et — test deterministik olsun.
    lm.owner_dev_mode = False
    return lm


def _write(tmp_path, data):
    path = tmp_path / "license.key"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _license_payload(plan="PRO", machine_id=None, expiry=None, updates_until=None):
    now = datetime.now(timezone.utc)
    return {
        "email": "test@dj.local",
        "machine_id": machine_id or LicenseManager().machine_id_display(),
        "plan": plan,
        "expiry": (expiry or (now + timedelta(days=365))).strftime("%Y-%m-%d"),
        "max_tracks": 50000,
        "updates_until": (updates_until or (now + timedelta(days=90))).strftime("%Y-%m-%d"),
        "issued_at": now.isoformat(),
        "nonce": "a" * 32,
    }


def test_no_license_is_demo(tmp_path):
    lm = _manager(tmp_path)
    plan = lm.get_plan()
    assert plan["plan"] == "DEMO"
    assert plan["licensed"] is False
    assert plan["reason"] == "NO LICENSE"


def test_demo_max_tracks_is_1000_not_10000(tmp_path):
    # Audit H5: DEMO limiti entitlements ile tutarlı (1000), 10000 değil.
    lm = _manager(tmp_path)
    assert lm.get_plan()["max_tracks"] == 1000
    from app.license.entitlements import EntitlementManager
    assert EntitlementManager.PLAN_FEATURES["DEMO"]["max_tracks"] == 1000


def test_valid_signed_license_is_pro(tmp_path, patched_pubkey):
    private_pem = patched_pubkey
    payload = _license_payload()
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    _write(tmp_path, payload)

    lm = _manager(tmp_path)
    plan = lm.get_plan()
    assert plan["licensed"] is True
    assert plan["plan"] == "PRO"
    assert plan["entitlements"]["updates_active"] is True


def test_unsigned_license_is_rejected(tmp_path, patched_pubkey):
    payload = _license_payload()
    # signature anahtarı var ama boş → yapı geçer, imza doğrulanamaz
    payload["signature"] = ""
    _write(tmp_path, payload)
    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is False
    assert plan["reason"] == "INVALID SIGNATURE"


def test_tampered_license_is_rejected(tmp_path, patched_pubkey):
    private_pem = patched_pubkey
    payload = _license_payload()
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    # kurcala: planı ENTERPRISE'a çıkar, sınırsız yap
    payload["plan"] = "ENTERPRISE"
    payload["max_tracks"] = 0
    _write(tmp_path, payload)

    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is False
    assert plan["reason"] == "INVALID SIGNATURE"


def test_expired_license(tmp_path, patched_pubkey):
    private_pem = patched_pubkey
    payload = _license_payload(expiry=datetime.now(timezone.utc) - timedelta(days=1))
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    _write(tmp_path, payload)

    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is False
    assert plan["reason"] == "EXPIRED"


def test_wrong_machine(tmp_path, patched_pubkey):
    private_pem = patched_pubkey
    payload = _license_payload(machine_id="0" * 64)
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    _write(tmp_path, payload)

    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is False
    assert plan["reason"] == "WRONG MACHINE"


def test_corrupt_expiry_does_not_crash(tmp_path, patched_pubkey):
    # Audit M7: hatalı expiry boot'u çökertmemeli.
    private_pem = patched_pubkey
    payload = _license_payload()
    payload["expiry"] = "not-a-date"
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    _write(tmp_path, payload)

    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is False
    assert plan["reason"] == "INVALID EXPIRY"


def test_demo_plan_has_no_updates(tmp_path):
    lm = _manager(tmp_path)
    assert lm.get_plan()["entitlements"]["updates_active"] is False


def test_updates_window_expired(tmp_path, patched_pubkey):
    private_pem = patched_pubkey
    past = datetime.now(timezone.utc) - timedelta(days=1)
    payload = _license_payload(updates_until=past)
    payload["signature"] = sig.sign(payload, private_key_pem=private_pem)
    _write(tmp_path, payload)

    plan = _manager(tmp_path).get_plan()
    assert plan["licensed"] is True  # lisans geçerli
    assert plan["entitlements"]["updates_active"] is False  # ama update kapalı
