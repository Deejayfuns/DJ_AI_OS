#!/usr/bin/env python3
"""
DJ AI OS — vendor Ed25519 keypair üretici (YALNIZCA vendor makinesi).

Kullanım:
    python tools/keygen.py              # private key'i vendor_private_key.pem'e yazar
    python tools/keygen.py --no-write   # yazmadan sadece bastır

Çıktı:
- Public key PEM  -> app/config/vendor_public_key.py'ye gömelin (VENDOR_PUBLIC_KEY_PEM)
- Private key PEM -> vendor_private_key.pem (gitignored) VEYA env DJ_AI_OS_LICENSE_PRIVATE_KEY

GÜVENLİK: private key'i asla public key'in gömüldüğü repoya commit etmeyin.
Bu araç yalnızca ilk kurulumda ve anahtar rotasyonunda kullanılır.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIVATE_KEY_FILE = PROJECT_ROOT / "vendor_private_key.pem"


def generate():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def main():
    # Türkçe Windows konsolunda emoji/UTF-8 çıktısı patlamasın.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="DJ AI OS vendor Ed25519 keypair")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="private key'i dosyaya yazma (yalnızca bastır)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="mevcut vendor_private_key.pem üzerine yaz",
    )
    args = parser.parse_args()

    private_pem, public_pem = generate()
    public_text = public_pem.decode("utf-8").strip()

    if not args.no_write:
        if PRIVATE_KEY_FILE.exists() and not args.force:
            print(
                f"⚠️  {PRIVATE_KEY_FILE.name} zaten var. Üzerine yazmak için --force "
                "(bu mevcut lisansları geçersiz kılar!)"
            )
            sys.exit(1)
        PRIVATE_KEY_FILE.write_bytes(private_pem)
        print(f"✅ Private key yazıldı: {PRIVATE_KEY_FILE} (GITIGNORED, saklayın)")

    print("\n=== PUBLIC KEY (bunu app/config/vendor_public_key.py'ye gömelin) ===\n")
    print(public_text)
    print("=== PUBLIC KEY BİTTİ ===\n")
    print("Fingerprint:", public_text.encode("utf-8"))
    import hashlib
    print(hashlib.sha256(public_text.encode("utf-8")).hexdigest()[:16].upper())
    print("\nAlternatif: private key'i env olarak kullan: set DJ_AI_OS_LICENSE_PRIVATE_KEY")
    print("(PEM içeriği tek satıra \\n ile gömülerek verilebilir veya dosya yolu)")


if __name__ == "__main__":
    main()
