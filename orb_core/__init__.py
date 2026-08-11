"""
ORB Core — Astra Nexus Runtime Kernel
=====================================
Modüler, hot-reload'lu, cross-platform DJ Studio runtime'ı.

Architecture:
    Kernel -> Module Registry -> Event Bus -> IPC Transport
                    -> Sandbox Loader -> Platform Abstraction
                    -> Config Store -> Neon Visual System

Usage:
    from orb_core import Kernel
    kernel = Kernel("orb_manifest.yaml")
    await kernel.start()
"""
from .kernel import Kernel, ModuleSpec, ModuleState, EventBus, Event
from .manifest import Manifest, ModuleManifest, Capability, ModuleType
from .ipc import (
    Transport, Protocol, Message, Discovery, ServiceInfo,
    create_transport, get_registry,
)
from .sandbox import Loader, Permissions, Limits, SandboxedModule, PermissionDenied
from .config import (
    Schema, ConfigStore,
    AppConfig, AudioConfig, MidiConfig, UiConfig, NetworkConfig, OrmConfig,
    CompleteConfig, ConfigSource,
)
from .platform import (
    Audio, MIDI, HID, FS, Process,
    current_platform, is_windows, is_linux, is_macos, Platform,
)
from .neon import (
    Theme, Glow, Renderer, WaveformRenderer, SpectrumRenderer,
    ParticleEffect, NeonButton, NeonSlider, NeonProgressBar, NeonFrame,
    build_theme, apply_ttk_theme,
)

__version__ = "0.1.0"
__all__ = [
    "Kernel", "ModuleSpec", "ModuleState", "EventBus", "Event",
    "Manifest", "ModuleManifest", "Capability", "ModuleType",
    "Transport", "Protocol", "Message", "Discovery", "ServiceInfo",
    "create_transport", "get_registry",
    "Loader", "Permissions", "Limits", "SandboxedModule", "PermissionDenied",
    "Schema", "ConfigStore",
    "AppConfig", "AudioConfig", "MidiConfig", "UiConfig",
    "NetworkConfig", "OrmConfig", "CompleteConfig", "ConfigSource",
    "Audio", "MIDI", "HID", "FS", "Process",
    "current_platform", "is_windows", "is_linux", "is_macos", "Platform",
    "Theme", "Glow", "Renderer", "WaveformRenderer", "SpectrumRenderer",
    "ParticleEffect", "NeonButton", "NeonSlider", "NeonProgressBar", "NeonFrame",
    "build_theme", "apply_ttk_theme",
]