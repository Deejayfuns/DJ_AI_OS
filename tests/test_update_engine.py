"""Update engine testleri — çevrimdışı (imzalı manifest, file:// indirme)."""

import hashlib
import json

import pytest

from app.license import signature as sig
from app.cloud.update_engine import UpdateEngine


MODULE = "app/config/version.py"


@pytest.fixture
def remote(tmp_path):
    """İmzalı manifest + modül dosyası içeren sahte update sunucusu (tmp).

    Döner: (remote_dir, test_private_key_pem)
    """
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

    original = sig.VENDOR_PUBLIC_KEY_PEM
    sig.VENDOR_PUBLIC_KEY_PEM = public_pem
    try:
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()

        content = b'APP_VERSION = "0.2.0"\n'
        mod_dir = remote_dir / "modules" / MODULE
        mod_dir.parent.mkdir(parents=True)
        mod_dir.write_bytes(content)

        manifest = {
            "version": "0.2.0",
            "min_client_version": "0.1.0",
            "released_at": "2026-08-12T00:00:00Z",
            "critical": False,
            "changelog": "test",
            "download_url": f"file://{remote_dir.as_posix()}",
            "modules": [{
                "name": MODULE,
                "version": "0.2.0",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
                "hot_reload": False,
            }],
        }
        manifest["signature"] = sig.sign(manifest, private_key_pem=private_pem)
        (remote_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        yield remote_dir, private_pem
    finally:
        sig.VENDOR_PUBLIC_KEY_PEM = original


def _load_manifest(remote_dir):
    return json.loads((remote_dir / "manifest.json").read_text(encoding="utf-8"))


def _engine(tmp_path):
    app_root = tmp_path / "app_root"
    app_root.mkdir()
    target = app_root / MODULE
    target.parent.mkdir(parents=True)
    target.write_text("OLD\n", encoding="utf-8")
    return UpdateEngine(app_root=str(app_root), update_dir=str(tmp_path / "upd"))


def test_gate_blocks_when_updates_not_active(tmp_path):
    engine = _engine(tmp_path)
    result = engine.check_for_updates({"entitlements": {"updates_active": False}})
    assert result["available"] is False
    assert result["reason"] == "updates_not_active"


def test_check_detects_available(tmp_path, remote):
    remote_dir, _ = remote
    engine = _engine(tmp_path)
    result = engine.check_for_updates(
        {"entitlements": {"updates_active": True}}, offline_dir=str(remote_dir)
    )
    assert result["available"] is True
    assert result["latest"] == "0.2.0"
    assert result["manifest"]["signature"]


def test_check_rejects_bad_signature(tmp_path, remote):
    remote_dir, _ = remote
    engine = _engine(tmp_path)
    manifest = _load_manifest(remote_dir)
    manifest["version"] = "9.9.9"  # kurcala, imzalama
    (remote_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = engine.check_for_updates(
        {"entitlements": {"updates_active": True}}, offline_dir=str(remote_dir)
    )
    assert result["available"] is False
    assert result["reason"] == "manifest_bad_signature"


def test_apply_swaps_module(tmp_path, remote):
    remote_dir, _ = remote
    engine = _engine(tmp_path)
    result = engine.check_for_updates(
        {"entitlements": {"updates_active": True}}, offline_dir=str(remote_dir)
    )
    res = engine.apply_update(result["manifest"], user_approved=True)
    assert res["ok"] is True
    assert res["hot_swapped"] == 1
    target = tmp_path / "app_root" / MODULE
    assert "0.2.0" in target.read_text(encoding="utf-8")


def test_bad_checksum_rolls_back(tmp_path, remote):
    remote_dir, private_pem = remote
    engine = _engine(tmp_path)
    manifest = _load_manifest(remote_dir)
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest["signature"] = sig.sign(manifest, private_key_pem=private_pem)

    res = engine.apply_update(manifest, user_approved=True)
    assert res["ok"] is False
    assert res["reason"] == "checksum_failed"
    target = tmp_path / "app_root" / MODULE
    assert target.read_text(encoding="utf-8") == "OLD\n"  # rollback korudu


def test_non_critical_needs_approval(tmp_path, remote):
    remote_dir, _ = remote
    engine = _engine(tmp_path)
    manifest = _load_manifest(remote_dir)
    res = engine.apply_update(manifest, user_approved=False)
    assert res["ok"] is False
    assert res["reason"] == "needs_approval"


def test_critical_applies_without_approval(tmp_path, remote):
    remote_dir, private_pem = remote
    engine = _engine(tmp_path)
    manifest = _load_manifest(remote_dir)
    manifest["critical"] = True
    manifest["signature"] = sig.sign(manifest, private_key_pem=private_pem)

    res = engine.apply_update(manifest, user_approved=False)
    assert res["ok"] is True
    target = tmp_path / "app_root" / MODULE
    assert "0.2.0" in target.read_text(encoding="utf-8")
