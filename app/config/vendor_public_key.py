"""
DJ AI OS — gömülü vendor public key (Ed25519).

Bu YALNIZCA public key'tir; imza DOĞRULAMAK için client'a gömülür. Private key
ASLA bu repoda/client'ta bulunmaz — vendor makinesinde (DJ_AI_OS_LICENSE_PRIVATE_KEY
env veya gitignored vendor_private_key.pem) ve gelecekte sunucuda durur.

Rotasyon: tools/keygen.py ile yeni keypair üret, bu dosyadaki PEM'i güncelle ve
sürüm yayınla. Eski anahtarla imzalanmış lisanslar geçersiz olur.
"""

# Aşağıdaki PEM, tools/keygen.py çıktısından (public key) gömülmüştür.
VENDOR_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAww3SHhBwzDr5dTeBAQoeTQ07rFnLOvyk3NGsTclZJOc=
-----END PUBLIC KEY-----"""
