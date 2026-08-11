"""
ORB Neon — TRON-style Visual System
====================================
Neon color themes, glowing widgets, and real-time renderers.

Themes:
    tron       — Neon cyan/magenta (default)
    matrix     — Green matrix rain
    blood_night— Blood red / ember
    ice        — Ice blue / lavender
"""
from .theme import Theme, Glow, NeonColor, build_theme
from .widgets import (
    NeonButton, NeonSlider, NeonProgressBar, NeonFrame, apply_ttk_theme,
)
from .renderer import (
    Renderer, WaveformRenderer, SpectrumRenderer, ParticleEffect,
)

__all__ = [
    "Theme", "Glow", "NeonColor", "build_theme",
    "NeonButton", "NeonSlider", "NeonProgressBar", "NeonFrame",
    "apply_ttk_theme",
    "Renderer", "WaveformRenderer", "SpectrumRenderer", "ParticleEffect",
]