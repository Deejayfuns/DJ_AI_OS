"""
DJ AI OS — Ed25519 imza / doğrulama (lisans + update manifest).

Güvenlik modeli:
- Vendor private key ASLA client'ta bulunmaz; yalnızca vendor makinesinde
  (env `DJ_AI_OS_LICENSE_PRIVATE_KEY`) veya repo-root'taki gitignored
  `vendor_private_key.pem` dosyasında durur. Gelecekte sunucuda da aynı key.
- Client SADECE gömülü public key (`app/config/vendor_public_key.py`) ile
  DOĞRULAR. Forge etmek için private key gerekir; public key yardımcı olmaz.
- İmza, payload'daki "signature" dışındaki tüm alanların sort_keys canonical
  JSON'u üzerinde — license.key ve update manifest'i aynı şemayı kullanır.

`cryptography` kütüphanesi gerekir (requirements.txt'te). Kütüphane yoksa
verify() fail-closed (False) döner — asla güvensiz geçmez.
"""

import hashlib
import json
import os
from pathlib import Path

from app.config.vendor_public_key import VENDOR_PUBLIC_KEY_PEM


# Repo-root'taki gitignored vendor private key (env'e alternatif).
_PRIVATE_KEY_FILE = (
    Path(__file__).resolve().parent.parent.parent / "vendor_private_key.pem"
)


def canonical_json(payload):
    """İmzalanacak canonical bytes: 'signature' hariç, sort_keys, compact."""
    data = {
        key: value
        for key, value in payload.items()
        if key != "signature"
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def has_signing_key():
    """Vendor makinesinde private key var mı? (env veya gitignored dosya)"""
    if os.environ.get("DJ_AI_OS_LICENSE_PRIVATE_KEY", "").strip():
        return True
    try:
        return _PRIVATE_KEY_FILE.exists()
    except Exception:
        return False


def _load_private_key_pem():
    """Private key'i env'den veya gitignored dosyadan oku (vendor makinesi)."""
    env_pem = os.environ.get("DJ_AI_OS_LICENSE_PRIVATE_KEY", "").strip()
    if env_pem:
        return env_pem.encode("utf-8")

    if _PRIVATE_KEY_FILE.exists():
        return _PRIVATE_KEY_FILE.read_bytes()

    raise ValueError(
        "DJ_AI_OS_LICENSE_PRIVATE_KEY (env) veya vendor_private_key.pem "
        "bulunamadı — bu yalnızca vendor makinesinde çalışır."
    )


def sign(payload, private_key_pem=None):
    """Payload'ı imzala (vendor makinesi). Hex string döner."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    pem = (
        private_key_pem
        if private_key_pem is not None
        else _load_private_key_pem()
    )
    if isinstance(pem, str):
        pem = pem.encode("utf-8")

    private_key = serialization.load_pem_private_key(pem, password=None)
    signature = private_key.sign(canonical_json(payload))
    return signature.hex()


def verify(payload, signature_hex, public_key_pem=None):
    """İmzayı public key ile doğrula. Fail-closed: her hata -> False."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    pem = public_key_pem or VENDOR_PUBLIC_KEY_PEM
    if not pem:
        return False

    try:
        if isinstance(pem, str):
            pem = pem.encode("utf-8")
        public_key = serialization.load_pem_public_key(pem)
        public_key.verify(bytes.fromhex(str(signature_hex)), canonical_json(payload))
        return True
    except Exception:
        # Fail-closed: InvalidSignature, bozuk hex, kütüphane hatası — hepsi geçersiz.
        return False


def public_key_fingerprint(public_key_pem=None):
    """Public key'in kısa parmak izi (Account ekranına göstermek için)."""
    pem = public_key_pem or VENDOR_PUBLIC_KEY_PEM
    if not pem:
        return "NO_PUBLIC_KEY"
    raw = pem.encode("utf-8") if isinstance(pem, str) else pem
    return hashlib.sha256(raw).hexdigest()[:16].upper()
