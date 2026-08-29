"""
DJ AI OS — sürüm tek kaynağı.

APP_VERSION (teknik sürüm) update karşılaştırmasında, build_exe'de ve update
manifest'inde kullanılır. BRAND (marka adı) UI'da görünen etikettir.

Kural: Teknik sürüm DEĞİŞECEĞİNDE yalnızca bu dosya düzenlenir; pyproject.toml
ve build_exe.py artık kaynak değil, okuyucudur.
"""

APP_VERSION = "0.2.0"

# Marka etiketi (UI/title/splash). Teknik sürümden bağımsızdır.
BRAND = "DJ AI OS v24 ULTRA PRODUCER"


def version():
    """Teknik sürüm — update karşılaştırmaları ve manifest'ler için."""
    return APP_VERSION


def brand():
    """Görünen marka etiketi — UI başlıkları için."""
    return BRAND
