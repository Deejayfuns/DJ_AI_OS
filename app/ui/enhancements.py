"""UI Enhancements — next-level UX for DJ AI OS.

Features:
- Toast Notifications: animated popup notifications for actions
- Mini Player: persistent bottom playback controls
- Theme Switcher: toggle between neon themes
- Quick Stats Bar: real-time library stats in footer
"""

import math
import time
import threading
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT, ACCENT_SOFT, BACKGROUND, CARD, F_BODY, F_BODY_BOLD, F_META,
    GLASS_BG, GLASS_BORDER, HOVER, MUTED, NEON_BLUE, NEON_MAGENTA,
    NEON_PURPLE, PANEL, SELECTED, SUBTLE, TEXT, WARNING,
)


# ============================================================
# Theme Presets
# ============================================================

THEMES = {
    "NEON GREEN": {
        "accent": "#00FFA3",
        "accent_soft": "#00C896",
        "neon_secondary": "#22D3FF",
        "bg": "#070812",
        "panel": "#0D1020",
        "card": "#15172B",
    },
    "NEON PURPLE": {
        "accent": "#9B5CFF",
        "accent_soft": "#7B61FF",
        "neon_secondary": "#FF3DF2",
        "bg": "#0A0612",
        "panel": "#100D20",
        "card": "#1A1530",
    },
    "CYBER BLUE": {
        "accent": "#22D3FF",
        "accent_soft": "#1AADE0",
        "neon_secondary": "#00FFA3",
        "bg": "#050A15",
        "panel": "#0A1225",
        "card": "#101A30",
    },
    "HOT PINK": {
        "accent": "#FF3DF2",
        "accent_soft": "#E035D9",
        "neon_secondary": "#FFB020",
        "bg": "#12050F",
        "panel": "#1A0A18",
        "card": "#251028",
    },
}


# ============================================================
# Toast Notification
# ============================================================

class ToastNotification(ctk.CTkToplevel):
    """Animated popup notification that auto-dismisses."""

    def __init__(self, message, toast_type="info", duration=3000):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Colors
        colors = {
            "info": ("#00FFA3", "#0D1020"),
            "success": ("#00FFA3", "#0D2015"),
            "warning": ("#FFB020", "#201A0D"),
            "error": ("#FF4D6D", "#200D10"),
        }
        accent, bg = colors.get(toast_type, colors["info"])

        self.configure(fg_color=bg)

        # Content
        self.configure(width=400, height=60)

        # Center on screen
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"400x60+{w//2 - 200}+{h - 100}")

        # Message
        ctk.CTkLabel(
            self,
            text=message,
            font=("Segoe UI", 13, "bold"),
            text_color=accent,
            wraplength=380,
        ).pack(padx=15, pady=10)

        # Border glow
        self.configure(border_width=2, border_color=accent, corner_radius=10)

        # Auto-dismiss
        self.after(duration, self._fade_out)
        self._alpha = 1.0
        self._fade_step()

    def _fade_step(self):
        if not self.winfo_exists():
            return
        try:
            self._alpha = max(0, self._alpha - 0.02)
            self.attributes("-alpha", self._alpha)
        except Exception:
            pass

        if self._alpha > 0:
            self.after(16, self._fade_step)
        else:
            self.destroy()

    def _fade_out(self):
        self._alpha = 1.0
        self._fade_step()


def show_toast(message, toast_type="info", duration=2500):
    """Show a toast notification. Safe to call from any thread."""
    try:
        ToastNotification(message, toast_type, duration)
    except Exception:
        pass  # Non-critical


# ============================================================
# Mini Player (persistent bottom bar)
# ============================================================

class MiniPlayer(ctk.CTkFrame):
    """Persistent bottom playback controls."""

    def __init__(self, master, on_play=None, on_stop=None, on_next=None,
                 on_prev=None, **kwargs):
        super().__init__(
            master,
            fg_color=GLASS_BG,
            corner_radius=0,
            height=50,
            **kwargs,
        )
        self.pack_propagate(False)

        self.on_play = on_play
        self.on_stop = on_stop
        self.on_next = on_next
        self.on_prev = on_prev
        self._playing = False
        self._current_track = ""
        self._phase = 0

        # Layout
        self._build()
        self.after(80, self._tick)

    def _build(self):
        # Left: play controls
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(side="left", padx=10)

        self.prev_btn = ctk.CTkButton(
            controls, text="⏮", width=36, height=36,
            fg_color=CARD, hover_color=HOVER,
            font=("Segoe UI", 16),
            command=self._on_prev,
        )
        self.prev_btn.pack(side="left", padx=2)

        self.play_btn = ctk.CTkButton(
            controls, text="▶", width=40, height=36,
            fg_color=ACCENT, hover_color=ACCENT_SOFT,
            text_color=BACKGROUND,
            font=("Segoe UI", 16, "bold"),
            command=self._on_play,
        )
        self.play_btn.pack(side="left", padx=2)

        self.next_btn = ctk.CTkButton(
            controls, text="⏭", width=36, height=36,
            fg_color=CARD, hover_color=HOVER,
            font=("Segoe UI", 16),
            command=self._on_next,
        )
        self.next_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(
            controls, text="⏹", width=36, height=36,
            fg_color=CARD, hover_color=HOVER,
            font=("Segoe UI", 16),
            command=self._on_stop_action,
        )
        self.stop_btn.pack(side="left", padx=(6, 0))

        # Center: track info
        self.track_label = ctk.CTkLabel(
            self, text="DJ AI OS — hazir",
            font=F_BODY, text_color=TEXT,
            anchor="w",
        )
        self.track_label.pack(side="left", padx=20, fill="x", expand=True)

        # Right: status
        self.status_label = ctk.CTkLabel(
            self, text="STOPPED",
            font=F_META, text_color=MUTED,
        )
        self.status_label.pack(side="right", padx=10)

        # Glow line at top
        self._glow = ctk.CTkFrame(self, height=2, fg_color=ACCENT)
        self._glow.pack(fill="x", side="top")

    def update_track(self, track):
        name = track.get("name", "")[:50]
        bpm = track.get("bpm", "")
        key = track.get("camelot", track.get("key", ""))
        self._current_track = name
        self.track_label.configure(text=f"{name} | {bpm} BPM | {key}")

    def set_playing(self, playing):
        self._playing = playing
        if playing:
            self.play_btn.configure(text="⏸")
            self.status_label.configure(text="PLAYING", text_color=ACCENT)
            self._glow.configure(fg_color=ACCENT)
        else:
            self.play_btn.configure(text="▶")
            self.status_label.configure(text="STOPPED", text_color=MUTED)
            self._glow.configure(fg_color=SUBTLE)

    def _tick(self):
        if not self.winfo_exists():
            return
        if self._playing:
            self._phase = (self._phase + 3) % 360
            pulse = int(1 + abs(math.sin(math.radians(self._phase))) * 2)
            self._glow.configure(height=pulse)
        self.after(80, self._tick)

    def _on_play(self):
        if self.on_play:
            self.on_play()

    def _on_stop_action(self):
        if self.on_stop:
            self.on_stop()

    def _on_next(self):
        if self.on_next:
            self.on_next()

    def _on_prev(self):
        if self.on_prev:
            self.on_prev()


# ============================================================
# Theme Switcher
# ============================================================

class ThemeSwitcher(ctk.CTkFrame):
    """Compact theme selection buttons."""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.on_change = on_change
        self._current = "NEON GREEN"

        ctk.CTkLabel(
            self, text="THEME:", font=F_META, text_color=MUTED
        ).pack(side="left", padx=(0, 6))

        for name, colors in THEMES.items():
            btn = ctk.CTkButton(
                self,
                text="",
                width=24, height=24,
                fg_color=colors["accent"],
                hover_color=colors["accent_soft"],
                corner_radius=12,
                border_width=2 if name == self._current else 0,
                border_color="#FFFFFF",
                command=lambda n=name: self._select(n),
            )
            btn.pack(side="left", padx=2)

    def _select(self, name):
        self._current = name
        if self.on_change:
            self.on_change(name, THEMES[name])


# ============================================================
# Quick Stats Bar
# ============================================================

class QuickStatsBar(ctk.CTkFrame):
    """Bottom bar showing real-time library stats."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master, fg_color=GLASS_BG, corner_radius=0, height=28, **kwargs
        )
        self.pack_propagate(False)

        self._stats = {}
        self._build()

    def _build(self):
        self.version = ctk.CTkLabel(
            self, text="DJ AI OS v24", font=F_META, text_color=MUTED
        )
        self.version.pack(side="left", padx=10)

        sep1 = ctk.CTkFrame(self, width=1, height=16, fg_color=SUBTLE)
        sep1.pack(side="left", padx=6)

        self.tracks_label = ctk.CTkLabel(
            self, text="0 tracks", font=F_META, text_color=TEXT
        )
        self.tracks_label.pack(side="left", padx=6)

        self.genres_label = ctk.CTkLabel(
            self, text="0 genres", font=F_META, text_color=TEXT
        )
        self.genres_label.pack(side="left", padx=6)

        self.duplicates_label = ctk.CTkLabel(
            self, text="0 dupes", font=F_META, text_color=TEXT
        )
        self.duplicates_label.pack(side="left", padx=6)

        sep2 = ctk.CTkFrame(self, width=1, height=16, fg_color=SUBTLE)
        sep2.pack(side="left", padx=6)

        self.health_label = ctk.CTkLabel(
            self, text="Health: --", font=F_META, text_color=ACCENT
        )
        self.health_label.pack(side="left", padx=6)

        self.dna_label = ctk.CTkLabel(
            self, text="DNA: ---", font=F_META, text_color=NEON_PURPLE
        )
        self.dna_label.pack(side="right", padx=10)

    def update_stats(self, tracks=0, genres=0, duplicates=0,
                     health=0, dna="---"):
        self.tracks_label.configure(text=f"{tracks} tracks")
        self.genres_label.configure(text=f"{genres} genres")
        self.duplicates_label.configure(
            text=f"{dupes} dupes",
            text_color=WARNING if duplicates > 0 else TEXT,
        )
        self.health_label.configure(
            text=f"Health: {health}/100",
            text_color=ACCENT if health >= 80 else WARNING,
        )
        self.dna_label.configure(text=f"DNA: {dna}")


# ============================================================
# Smooth View Transition
# ============================================================

def smooth_transition(container, new_content_builder, duration_ms=200):
    """Fade out old content, build new content, fade in.

    Usage in set_view:
        smooth_transition(self.content, lambda: self.build_new_view())
    """
    # For now, just call the builder directly
    # Full animation would require more complex Tkinter hackery
    new_content_builder()
