"""
DJ AI OS — Boot/Assistant voice model selection
================================================

Centralizes the selectable neural TTS voices used by the boot greeting and the
assistant. The user can switch between several models at runtime (Settings →
VOICE AI). The choice persists to the per-user app-data directory so it survives
restarts and the installed (frozen) build.

Default (demo/standard) voice is a neutral male Turkish neural voice so a fresh
install greets the user in clean, standard Turkish.
"""
import json
from pathlib import Path
from typing import Dict, List

from app.core import paths


# Selectable voices. `is_default` marks the demo/standard voice used on a fresh
# install. Keep this list small and language-correct (no phonetic-butchery
# engines — these are all neural edge-tts voices).
VOICE_MODELS: List[Dict[str, str]] = [
    {
        "id": "tr-TR-AhmetNeural",
        "label": "Ahmet (Erkek · Standart)",
        "lang": "tr",
        "gender": "male",
        "is_default": False,
    },
    {
        "id": "tr-TR-EmelNeural",
        "label": "Emel (Kadın · Neural)",
        "lang": "tr",
        "gender": "female",
        "is_default": True,
    },
    {
        "id": "en-US-JennyNeural",
        "label": "Jenny (Kadın · EN)",
        "lang": "en",
        "gender": "female",
        "is_default": False,
    },
    {
        "id": "en-US-GuyNeural",
        "label": "Guy (Erkek · EN)",
        "lang": "en",
        "gender": "male",
        "is_default": False,
    },
    {
        "id": "de-DE-KatjaNeural",
        "label": "Katja (Kadın · DE)",
        "lang": "de",
        "gender": "female",
        "is_default": False,
    },
    {
        "id": "fr-FR-DeniseNeural",
        "label": "Denise (Kadın · FR)",
        "lang": "fr",
        "gender": "female",
        "is_default": False,
    },
]


DEFAULT_VOICE_ID = next(
    (m["id"] for m in VOICE_MODELS if m.get("is_default")),
    "tr-TR-AhmetNeural",
)


def _config_path() -> Path:
    return paths.get_app_data_dir() / "voice_config.json"


def get_voice_models() -> List[Dict[str, str]]:
    """Return the list of selectable voice models (caller-safe copy)."""
    return [dict(m) for m in VOICE_MODELS]


def get_voice_id() -> str:
    """Return the currently selected voice id (falls back to default)."""
    try:
        p = _config_path()
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            vid = data.get("voice_id")
            if vid and any(m["id"] == vid for m in VOICE_MODELS):
                return vid
    except Exception:
        pass
    return DEFAULT_VOICE_ID


def get_voice_model(voice_id: str = None) -> Dict[str, str]:
    """Return the model dict for `voice_id`, or the default if None/invalid."""
    vid = voice_id or get_voice_id()
    for m in VOICE_MODELS:
        if m["id"] == vid:
            return dict(m)
    return dict(next(m for m in VOICE_MODELS if m["id"] == DEFAULT_VOICE_ID))


def set_voice_id(voice_id: str) -> bool:
    """Persist the selected voice id. Returns True if valid and saved."""
    if not voice_id or not any(m["id"] == voice_id for m in VOICE_MODELS):
        return False
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["voice_id"] = voice_id
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


# Boot greeting lines, keyed by the voice model's language. Default Turkish line
# is the "future tech" welcome requested by the user.
BOOT_LINES = {
    "tr": (
        "Merhaba, Geleceğin Teknolojisi ile tanışmaya hazır mısın?\n"
        "Ben senin Yapay Zeka Asistanınım.\n"
        "Program içinde sana yardımcı olmaya hazırım.\n"
        "Görüşmek üzere."
    ),
    "en": (
        "Hello! Are you ready for the technology of the future? "
        "I am your AI assistant, ready to help you inside the program. "
        "See you around."
    ),
    "de": (
        "Hallo! Bereit fur die Technologie der Zukunft? "
        "Ich bin dein KI-Assistent und helfe dir im Programm. Bis bald."
    ),
    "fr": (
        "Bonjour ! Pret pour la technologie du futur ? "
        "Je suis ton assistant IA, pret a t'aider dans le programme. A bientot."
    ),
}


def get_boot_line(voice_id: str = None) -> str:
    """Return the boot greeting for the selected voice's language."""
    model = get_voice_model(voice_id)
    return BOOT_LINES.get(model["lang"], BOOT_LINES["tr"])
