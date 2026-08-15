"""Ed25519 imza/doğrulama testleri (app.license.signature)."""

import pytest

from app.license import signature as sig
from app.config.vendor_public_key import VENDOR_PUBLIC_KEY_PEM


def _new_keypair():
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
def keypair():
    """Ephemeral Ed25519 keypair (vendor key'ine dokunmaz)."""
    return _new_keypair()


def test_roundtrip(keypair):
    private_pem, public_pem = keypair
    payload = {"email": "a@b.c", "plan": "PRO", "max_tracks": 50000}
    sig_hex = sig.sign(payload, private_key_pem=private_pem)
    assert len(sig_hex) == 128  # 64 bayt Ed25519, hex
    assert sig.verify(payload, sig_hex, public_key_pem=public_pem) is True


def test_tampered_rejected(keypair):
    private_pem, public_pem = keypair
    payload = {"email": "a@b.c", "plan": "PRO", "max_tracks": 50000}
    sig_hex = sig.sign(payload, private_key_pem=private_pem)
    tampered = dict(payload)
    tampered["plan"] = "ENTERPRISE"
    assert sig.verify(tampered, sig_hex, public_key_pem=public_pem) is False


def test_wrong_key_rejected(keypair):
    private_pem, _ = keypair
    payload = {"email": "a@b.c"}
    sig_hex = sig.sign(payload, private_key_pem=private_pem)
    _, other_public = _new_keypair()  # GERÇEKTEN farklı bir keypair
    assert sig.verify(payload, sig_hex, public_key_pem=other_public) is False


def test_canonical_json_excludes_signature(keypair):
    private_pem, public_pem = keypair
    payload = {"signature": "x" * 128, "plan": "PRO"}
    # canonical_json 'signature' anahtarını atlar — imzalanan içerik signature'sız.
    assert b'"signature"' not in sig.canonical_json(payload)
    sig_hex = sig.sign(payload, private_key_pem=private_pem)
    # signature alanı imzaya karışmaz; aynı payload üzerinde roundtrip doğrulanır.
    assert sig.verify(payload, sig_hex, public_key_pem=public_pem) is True


def test_malformed_signature_rejected(keypair):
    _, public_pem = keypair
    payload = {"plan": "PRO"}
    assert sig.verify(payload, "not-hex", public_key_pem=public_pem) is False
    assert sig.verify(payload, "", public_key_pem=public_pem) is False
    assert sig.verify(payload, None, public_key_pem=public_pem) is False


def test_embedded_public_key_present():
    assert VENDOR_PUBLIC_KEY_PEM.startswith("-----BEGIN PUBLIC KEY-----")
    assert sig.verify({"x": 1}, "0" * 128) is False  # gömülü key ile doğrulanamaz


def test_has_signing_key_returns_bool():
    assert isinstance(sig.has_signing_key(), bool)
