"""UI Enhancements — Pro DJ UX for DJ AI OS.

Features:
- Toast Notifications: clean slide-in notifications for actions
- Mini Player: persistent bottom playback controls
- Quick Stats Bar: real-time library stats in footer
"""

import math
import time
import threading
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    # Backward compat
    ACCENT, ACCENT_SOFT, BACKGROUND, CARD, F_BODY, F_BODY_BOLD, F_META,
    GLASS_BG, GLASS_BORDER, HOVER, MUTED, NEON_BLUE, NEON_MAGENTA,
    NEON_PURPLE, PANEL, SELECTED, SUBTLE, TEXT, WARNING,
)


# ============================================================
# Toast Notification
# ============================================================

class ToastNotification(ctk.CTkToplevel):
    """Clean toast notification that auto-dismisses."""

    def __init__(self, message, toast_type="info", duration=3000):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Colors — clean, no neon
        colors = {
            "info":    (GREEN,  BG),
            "success": (GREEN,  BG),
            "warning": (AMBER,  BG),
            "error":   (RED,    BG),
        }
        accent, bg = colors.get(toast_type, colors["info"])

        self.configure(fg_color=bg)
        self.configure(width=360, height=48)

        # Center bottom of screen
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"360x48+{w // 2 - 180}+{h - 80}")

        # Left accent bar
        bar = ctk.CTkFrame(self, width=4, fg_color=accent)
        bar.pack(side="left", fill="y")

        # Message
        ctk.CTkLabel(
            self,
            text=message,
            font=("Segoe UI", 12),
            text_color=TEXT_PRIMARY,
            wraplength=330,
        ).pack(padx=(12, 12), pady=12, side="left")

        # Border
        self.configure(border_width=1, border_color=BORDER, corner_radius=6)

        # Auto-dismiss
        self.after(duration, self.destroy)


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
            fg_color=SURFACE,
            corner_radius=0,
            height=48,
            **kwargs,
        )
        self.pack_propagate(False)

        self.on_play = on_play
        self.on_stop = on_stop
        self.on_next = on_next
        self.on_prev = on_prev
        self._playing = False
        self._current_track = ""

        self._build()

    def _build(self):
        # Top separator
        top_sep = ctk.CTkFrame(self, height=1, fg_color=BORDER)
        top_sep.pack(fill="x", side="top")

        # Left: play controls
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(side="left", padx=12)

        self.prev_btn = ctk.CTkButton(
            controls, text="⏮", width=32, height=32,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            font=("Segoe UI", 14),
            command=lambda: self.on_prev() if self.on_prev else None,
        )
        self.prev_btn.pack(side="left", padx=2)

        self.play_btn = ctk.CTkButton(
            controls, text="▶", width=36, height=32,
            fg_color=RED, hover_color=RED_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            command=self._on_play,
        )
        self.play_btn.pack(side="left", padx=2)

        self.next_btn = ctk.CTkButton(
            controls, text="⏭", width=32, height=32,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            font=("Segoe UI", 14),
            command=lambda: self.on_next() if self.on_next else None,
        )
        self.next_btn.pack(side="left", padx=2)

        self.stop_btn = ctk.CTkButton(
            controls, text="⏹", width=32, height=32,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            font=("Segoe UI", 14),
            command=self._on_stop_action,
        )
        self.stop_btn.pack(side="left", padx=(6, 0))

        # Separator
        sep = ctk.CTkFrame(controls, width=1, height=24, fg_color=BORDER)
        sep.pack(side="left", padx=10)

        # Center: track info
        self.track_label = ctk.CTkLabel(
            self, text="No track loaded",
            font=("Segoe UI", 12), text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.track_label.pack(side="left", padx=8, fill="x", expand=True)

        # Right: status
        self.status_label = ctk.CTkLabel(
            self, text="STOPPED",
            font=F_META, text_color=TEXT_DIM,
        )
        self.status_label.pack(side="right", padx=12)

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
            self.status_label.configure(text="PLAYING", text_color=GREEN)
        else:
            self.play_btn.configure(text="▶")
            self.status_label.configure(text="STOPPED", text_color=TEXT_DIM)

    def _on_play(self):
        if self.on_play:
            self.on_play()

    def _on_stop_action(self):
        if self.on_stop:
            self.on_stop()


# ============================================================
# Quick Stats Bar
# ============================================================

class QuickStatsBar(ctk.CTkFrame):
    """Bottom bar showing real-time library stats."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master, fg_color=SURFACE, corner_radius=0, height=28, **kwargs
        )
        self.pack_propagate(False)

        self._build()

    def _build(self):
        self.version = ctk.CTkLabel(
            self, text="DJ AI OS v24", font=F_META, text_color=TEXT_DIM
        )
        self.version.pack(side="left", padx=12)

        sep1 = ctk.CTkFrame(self, width=1, height=16, fg_color=BORDER)
        sep1.pack(side="left", padx=8)

        self.tracks_label = ctk.CTkLabel(
            self, text="0 tracks", font=F_META, text_color=TEXT_SECONDARY
        )
        self.tracks_label.pack(side="left", padx=8)

        self.genres_label = ctk.CTkLabel(
            self, text="0 genres", font=F_META, text_color=TEXT_SECONDARY
        )
        self.genres_label.pack(side="left", padx=8)

        self.duplicates_label = ctk.CTkLabel(
            self, text="0 dupes", font=F_META, text_color=TEXT_SECONDARY
        )
        self.duplicates_label.pack(side="left", padx=8)

        sep2 = ctk.CTkFrame(self, width=1, height=16, fg_color=BORDER)
        sep2.pack(side="left", padx=8)

        self.health_label = ctk.CTkLabel(
            self, text="Health: --", font=F_META, text_color=GREEN
        )
        self.health_label.pack(side="left", padx=8)

        self.dna_label = ctk.CTkLabel(
            self, text="DNA: ---", font=F_META, text_color=BLUE_BRIGHT
        )
        self.dna_label.pack(side="right", padx=12)

    def update_stats(self, tracks=0, genres=0, duplicates=0,
                     health=0, dna="---"):
        self.tracks_label.configure(text=f"{tracks} tracks")
        self.genres_label.configure(text=f"{genres} genres")
        self.duplicates_label.configure(
            text=f"{duplicates} dupes",
            text_color=AMBER if duplicates > 0 else TEXT_SECONDARY,
        )
        self.health_label.configure(
            text=f"Health: {health}/100",
            text_color=GREEN if health >= 80 else AMBER,
        )
        self.dna_label.configure(text=f"DNA: {dna}")


# ============================================================
# Smooth View Transition
# ============================================================

# ============================================================
# Theme Switcher (stub — Pro DJ uses single dark theme)
# ============================================================

class ThemeSwitcher(ctk.CTkFrame):
    """Theme switcher placeholder — Pro DJ has one dark theme."""

    def __init__(self, master, on_change=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self, text="THEME: PRO DJ DARK", font=F_META, text_color=TEXT_DIM
        ).pack(side="left")


# ============================================================
# Smooth View Transition
# ============================================================

def smooth_transition(container, new_content_builder, duration_ms=200):
    """Fade out old content, build new content, fade in.
    (Placeholder — full animation requires complex Tkinter hackery)
    """
    new_content_builder()
