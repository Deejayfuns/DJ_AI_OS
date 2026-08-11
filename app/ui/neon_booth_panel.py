"""
DJ AI OS — Now Playing Panel (Pro DJ style)

Clean deck display: BPM, KEY, energy bars.
Minimal — no neon, no glow, no animated spectrum.
"""

import math
import tkinter as tk
import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, BORDER, RED, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_META, F_MONO,
)


class NeonBoothPanel(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)

        self.track = {}

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(header, text="NOW PLAYING", font=("Segoe UI", 12, "bold"),
                      text_color=TEXT_SECONDARY).pack(side="left")

        self.now_label = ctk.CTkLabel(header, text="NO TRACK", font=F_META, text_color=TEXT_DIM)
        self.now_label.pack(side="right")

        # Canvas
        self.canvas = tk.Canvas(self, height=120, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="x", padx=10, pady=(0, 10))

    def update_track(self, track):
        self.track = dict(track or {})
        name = self.track.get("name", "NO TRACK")
        if len(name) > 54:
            name = name[:51] + "..."
        self.now_label.configure(text=name)
        self._draw()

    def _draw(self, **kwargs):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 1)
        h = 120

        track = self.track
        bpm = track.get("bpm", "--")
        key = track.get("camelot") or track.get("key", "--")
        energy = 0.5
        try:
            energy = max(0, min(1, float(track.get("energy", 0.5))))
        except (TypeError, ValueError):
            pass

        # DECK A (left)
        self._draw_deck_box(10, 10, 200, 100, "DECK A", bpm, key, energy)

        # DECK B (right — empty)
        self._draw_deck_box(w - 210, 10, 200, 100, "DECK B", "--", "--", 0.35)

        # Center: crossfader position
        cx = w / 2
        self.canvas.create_rectangle(cx - 60, h / 2 - 2, cx + 60, h / 2 + 2, fill=BORDER, outline="")
        self.canvas.create_rectangle(cx - 3, h / 2 - 8, cx + 3, h / 2 + 8, fill=TEXT_PRIMARY, outline="")

    def _draw_deck_box(self, x, y, w, h, label, bpm, key, energy):
        self.canvas.create_rectangle(x, y, x + w, y + h, fill=BG, outline=BORDER, width=1)

        # Label
        self.canvas.create_text(x + 10, y + 12, text=label, fill=BLUE_BRIGHT,
                                 anchor="w", font=("Consolas", 9, "bold"))

        # BPM (large)
        self.canvas.create_text(x + 10, y + 40, text=f"{bpm}", fill=TEXT_PRIMARY,
                                 anchor="w", font=("Consolas", 18, "bold"))

        # KEY
        self.canvas.create_text(x + 10, y + 64, text=f"KEY {key}", fill=TEXT_DIM,
                                 anchor="w", font=("Consolas", 9))

        # Energy bars (right side of deck)
        for i in range(8):
            bx = x + w - 70 + i * 7
            bar_h = int(energy * 60 * (0.4 + (i % 4) / 5))
            by = y + h - 12
            color = RED if i < 6 else AMBER
            self.canvas.create_rectangle(bx, by - bar_h, bx + 4, by, fill=color, outline="")
