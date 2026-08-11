"""
ORB Modules — DJ AI OS Feature Modules
=======================================
Each module wraps an existing app/* component into the ORB lifecycle
(start/stop/health_check/on_event) and registers with the kernel.

Modules in this package:
    config_module       — centralized config store
    platform_module     — cross-platform abstraction service
    midi_module         — MIDI I/O + XDJ-RR mapping
    hid_module          — Pioneer HID engine
    audio_module        — audio playback/analysis/stems
    beat_module         — beatgrid analysis + sync
    instrument_module   — synth instruments / drums
    beat_studio_module  — DAW (sequencer, piano roll, mixer)
    deck_studio_module  — 4-deck virtual DJ
    rekordbox_module    — Rekordbox XML bridge
    ai_brain_module     — DJ brain / set intelligence
    dj_coach_module     — live coaching
    dj_profile_module   — Style DNA profile
    cloud_module        — portal / telemetry / updates
    ui_host_module      — CustomTkinter host + neon theme
"""
from .base import OrbModule
from .config_module import ConfigModule
from .platform_module import PlatformModule
from .midi_module import MidiModule
from .hid_module import HidModule
from .audio_module import AudioModule
from .beat_module import BeatModule
from .instrument_module import InstrumentModule
from .beat_studio_module import BeatStudioModule
from .deck_studio_module import DeckStudioModule
from .rekordbox_module import RekordboxModule
from .ai_brain_module import AiBrainModule
from .dj_coach_module import DjCoachModule
from .dj_profile_module import DjProfileModule
from .cloud_module import CloudModule
from .ui_host_module import UiHostModule

__all__ = [
    "OrbModule",
    "ConfigModule", "PlatformModule",
    "MidiModule", "HidModule",
    "AudioModule", "BeatModule", "InstrumentModule",
    "BeatStudioModule", "DeckStudioModule", "RekordboxModule",
    "AiBrainModule", "DjCoachModule", "DjProfileModule",
    "CloudModule", "UiHostModule",
]