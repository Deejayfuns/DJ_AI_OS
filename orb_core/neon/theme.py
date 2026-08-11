"""
ORB Neon — TRON-style Visual System
====================================
Neon color palette, glow effects, and cyberpunk widget theming.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class NeonColor:
    """A color with optional glow."""
    hex: str
    glow: str = None  # Glow color (usually lighter)
    name: str = ""


class Theme:
    """Neon color theme system."""

    def __init__(self, name: str = "tron"):
        self.name = name
        self._palettes = {
            "tron": {
                "bg": "#0a0a12",
                "bg_dark": "#05050a",
                "bg_panel": "#10101f",
                "bg_panel_alt": "#16162a",
                "fg": "#e8e8f0",
                "fg_dim": "#8a8aa5",
                "fg_bright": "#ffffff",
                "accent": "#00f0ff",       # Neon cyan
                "accent2": "#ff00e5",      # Neon magenta
                "accent3": "#00ff88",      # Neon green
                "accent4": "#ffcc00",      # Neon yellow
                "accent5": "#ff6600",      # Neon orange
                "danger": "#ff3333",       # Neon red
                "warning": "#ffcc00",
                "success": "#00ff88",
                "info": "#00f0ff",
                "border": "#1a1a35",
                "border_active": "#00f0ff",
                "glow_cyan": "#00f0ff",
                "glow_magenta": "#ff00e5",
                "glow_green": "#00ff88",
                "glow_amber": "#ffcc00",
                "grid": "#101030",
                "selection": "#0022aa",
                "hover": "#0a0a25",
                "disabled": "#3a3a55",
                "success_dim": "#006644",
                "danger_dim": "#660022",
                "waveform": "#00f0ff",
                "waveform_playing": "#00ff88",
                "waveform_queued": "#ffcc00",
                "spectrum": "#ff00e5",
            },
            "matrix": {
                "bg": "#000000",
                "bg_dark": "#000000",
                "bg_panel": "#001100",
                "bg_panel_alt": "#002200",
                "fg": "#00ff00",
                "fg_dim": "#008800",
                "fg_bright": "#00ff00",
                "accent": "#00ff00",
                "accent2": "#00cc00",
                "accent3": "#ccff00",
                "accent4": "#00ff88",
                "accent5": "#88ff00",
                "danger": "#ff0000",
                "warning": "#ffff00",
                "success": "#00ff00",
                "info": "#00ffff",
                "border": "#003300",
                "border_active": "#00ff00",
                "glow_cyan": "#00ff00",
                "glow_magenta": "#00ff00",
                "glow_green": "#00ff00",
                "glow_amber": "#ffff00",
                "grid": "#002200",
                "selection": "#003300",
                "hover": "#002200",
                "disabled": "#005500",
                "success_dim": "#005500",
                "danger_dim": "#550000",
                "waveform": "#00ff00",
                "waveform_playing": "#ccff00",
                "waveform_queued": "#88ff00",
                "spectrum": "#00ff88",
            },
            "blood_night": {
                "bg": "#0d0508",
                "bg_dark": "#060203",
                "bg_panel": "#15080d",
                "bg_panel_alt": "#1c0a10",
                "fg": "#f0e0e8",
                "fg_dim": "#a08088",
                "fg_bright": "#ffffff",
                "accent": "#ff2266",       # Blood red
                "accent2": "#ff00e5",      # Magenta
                "accent3": "#ff8800",      # Ember
                "accent4": "#ffcc00",      # Gold
                "accent5": "#ff4444",
                "danger": "#ff0000",
                "warning": "#ff8800",
                "success": "#00ff88",
                "info": "#00ccff",
                "border": "#2a1018",
                "border_active": "#ff2266",
                "glow_cyan": "#ff2266",
                "glow_magenta": "#ff00e5",
                "glow_green": "#00ff88",
                "glow_amber": "#ffcc00",
                "grid": "#200a10",
                "selection": "#4a0022",
                "hover": "#200a10",
                "disabled": "#4a2030",
                "success_dim": "#006644",
                "danger_dim": "#660022",
                "waveform": "#ff2266",
                "waveform_playing": "#00ff88",
                "waveform_queued": "#ffcc00",
                "spectrum": "#ff00e5",
            },
            "ice": {
                "bg": "#050a12",
                "bg_dark": "#02060c",
                "bg_panel": "#0a1420",
                "bg_panel_alt": "#0e1a2a",
                "fg": "#e0f0ff",
                "fg_dim": "#80a0c0",
                "fg_bright": "#ffffff",
                "accent": "#4dc3ff",       # Ice blue
                "accent2": "#b388ff",      # Lavender
                "accent3": "#00e5ff",      # Cyan
                "accent4": "#fff59d",      # Ice yellow
                "accent5": "#ff80ab",      # Ice pink
                "danger": "#ff5252",
                "warning": "#ffd740",
                "success": "#69f0ae",
                "info": "#40c4ff",
                "border": "#16283a",
                "border_active": "#4dc3ff",
                "glow_cyan": "#4dc3ff",
                "glow_magenta": "#b388ff",
                "glow_green": "#69f0ae",
                "glow_amber": "#ffd740",
                "grid": "#0e1f30",
                "selection": "#1a3350",
                "hover": "#0e1a2a",
                "disabled": "#2a4058",
                "success_dim": "#1a5c3a",
                "danger_dim": "#5c1a1a",
                "waveform": "#4dc3ff",
                "waveform_playing": "#69f0ae",
                "waveform_queued": "#ffd740",
                "spectrum": "#b388ff",
            },
        }
        self.current = self._palettes.get(name, self._palettes["tron"])

    def c(self, key: str) -> str:
        """Get color by key."""
        return self.current.get(key, "#ffffff")

    def set_theme(self, name: str) -> None:
        """Switch theme."""
        if name in self._palettes:
            self.name = name
            self.current = self._palettes[name]

    def list_themes(self) -> List[str]:
        """List available themes."""
        return list(self._palettes.keys())

    def glow_style(self, key: str = "accent") -> str:
        """Generate CSS/Tkinter glow style for a color."""
        color = self.c(key)
        return f"glow_{key}::{color}"

    def css(self) -> str:
        """Generate CSS variables for web-based UI."""
        return "\n".join(
            f"  --orb-{k.replace('_', '-')}: {v};"
            for k, v in self.current.items()
        )

    def tcl_colors(self) -> Dict[str, str]:
        """Convert theme to Tkinter-compatible color names."""
        return {k: v for k, v in self.current.items()}


class Glow:
    """Glow effect calculations."""

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    @staticmethod
    def lerp(c1: str, c2: str, t: float) -> str:
        """Interpolate between two colors."""
        r1, g1, b1 = Glow.hex_to_rgb(c1)
        r2, g2, b2 = Glow.hex_to_rgb(c2)
        return Glow.rgb_to_hex((
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    @staticmethod
    def pulse(color: str, intensity: float = 1.0) -> str:
        """Return color with pulsing intensity."""
        r, g, b = Glow.hex_to_rgb(color)
        return Glow.rgb_to_hex((
            int(r * intensity),
            int(g * intensity),
            int(b * intensity),
        ))

    @staticmethod
    def waveform_colors(base: str, frames: int) -> List[str]:
        """Generate gradient waveform colors."""
        return [Glow.lerp("#05050a", base, (i + 1) / frames) for i in range(frames)]


def build_theme(name: str = "tron") -> Theme:
    """Factory for theme creation."""
    return Theme(name)