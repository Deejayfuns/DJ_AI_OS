"""
ASTRA i18n — Multi-language support for DJ AI OS.
Languages: tr (Türkçe), en (English), de (Deutsch), fr (Français).
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Language codes
LANG_TR = "tr"
LANG_EN = "en"
LANG_DE = "de"
LANG_FR = "fr"

SUPPORTED_LANGS = [LANG_TR, LANG_EN, LANG_DE, LANG_FR]
DEFAULT_LANG = LANG_TR

# Language display names
LANG_NAMES = {
    LANG_TR: "Türkçe",
    LANG_EN: "English",
    LANG_DE: "Deutsch",
    LANG_FR: "Français",
}

# Current language (module-level state)
_current_lang = DEFAULT_LANG
_translations: Dict[str, Dict[str, str]] = {}


def _load_translations() -> None:
    """Load all translation files from the locales directory."""
    global _translations
    base = Path(__file__).parent / "locales"
    for lang in SUPPORTED_LANGS:
        path = base / f"{lang}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _translations[lang] = json.load(f)
            except Exception:
                _translations[lang] = {}
        else:
            _translations[lang] = {}


def set_language(lang: str) -> bool:
    """Set the active language. Returns True if language is supported."""
    global _current_lang
    if lang in SUPPORTED_LANGS:
        _current_lang = lang
        return True
    return False


def get_language() -> str:
    """Get the current active language code."""
    return _current_lang


def get_language_name(lang: Optional[str] = None) -> str:
    """Get display name for a language code."""
    code = lang or _current_lang
    return LANG_NAMES.get(code, code)


def t(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    """
    Translate a key with optional formatting.

    Usage:
        t("welcome.captain")           -> "Hoş geldin Kaptan"
        t("status.online", lang="en")  -> "ONLINE"
        t("tracks.count", count=42)    -> "42 parça"
    """
    target_lang = lang or _current_lang
    translations = _translations.get(target_lang, {})

    # Support nested keys like "welcome.captain"
    keys = key.split(".")
    value = translations
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # Fallback to Turkish, then to key itself
            fallback = _translations.get(LANG_TR, {})
            for k2 in keys:
                if isinstance(fallback, dict) and k2 in fallback:
                    fallback = fallback[k2]
                else:
                    return key
            value = fallback
            break

    if isinstance(value, str):
        try:
            return value.format(**kwargs)
        except Exception:
            return value
    return key


def available_languages() -> list[tuple[str, str]]:
    """Return list of (code, display_name) for all supported languages."""
    return [(code, LANG_NAMES[code]) for code in SUPPORTED_LANGS]


# Initialize on import
_load_translations()