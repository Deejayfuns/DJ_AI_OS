"""
DJ AI OS — Waveform View (Serato-style)

Red/Green color-coded waveform:
- Green = quiet / bass-heavy sections
- Red = loud / peak sections
Clean grid overlay, BPM/KEY labels.
"""

import customtkinter as ctk
import tkinter as tk
import math
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, GREEN, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_META, F_MONO,
)

try:
    import windnd
except Exception:
    windnd = None


# Serato-style waveform colors
WAVEFORM_GREEN = "#1DB954"
WAVEFORM_RED = "#E63946"
WAVEFORM_MID = "#F5A623"
GRID_COLOR = "#1A1A24"
PHASE_COLOR_START = "#2ECC71"
PHASE_COLOR_BUILD = "#F5A623"
PHASE_COLOR_PEAK = "#E63946"
PHASE_COLOR_OUTRO = "#457B9D"


class WaveformView(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(
            fg_color=SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=BORDER,
        )

        # BPM / Key header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=24)
        self.header.pack(fill="x", padx=8, pady=(6, 0))
        self.header.pack_propagate(False)

        self.bpm_label = ctk.CTkLabel(
            self.header, text="-- BPM", font=F_MONO, text_color=RED
        )
        self.bpm_label.pack(side="left", padx=4)

        self.key_label = ctk.CTkLabel(
            self.header, text="-- KEY", font=F_MONO, text_color=BLUE_BRIGHT
        )
        self.key_label.pack(side="left", padx=4)

        self.duration_label = ctk.CTkLabel(
            self.header, text="0:00 / 0:00", font=F_MONO, text_color=TEXT_DIM
        )
        self.duration_label.pack(side="right", padx=4)

        # Canvas
        self.canvas = tk.Canvas(
            self,
            bg=BG,
            height=200,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=4, pady=(2, 6))

    def enable_drag_drop(self, callback):
        if windnd is None:
            return
        for widget in (self, self.canvas):
            try:
                windnd.hook_dropfiles(widget, func=callback)
            except Exception:
                pass

    def draw_waveform(self, waveform, phrase_points=None, bpm=0, duration=0):
        self.canvas.delete("all")

        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 200)

        # Update header labels
        self.bpm_label.configure(text=f"{bpm:.0f} BPM" if bpm else "-- BPM")
        self.duration_label.configure(text=f"0:00 / {self._fmt_dur(duration)}" if duration else "0:00 / 0:00")

        if not waveform:
            self.canvas.create_text(
                w // 2, h // 2,
                text="Drop a track to see waveform",
                fill=TEXT_DIM,
                font=("Segoe UI", 12),
            )
            return

        center_y = h // 2

        # Draw waveform — Serato-style colored bars
        n = len(waveform)
        if n == 0:
            return

        step = max(1, w / n)

        for i, val in enumerate(waveform):
            x = i * step
            v = abs(val) if isinstance(val, (int, float)) else 0.5
            bar_h = int(v * center_y * 0.9)
            bar_h = max(1, min(center_y - 2, bar_h))

            # Color mapping: low=green, mid=amber, high=red
            if v < 0.35:
                color = WAVEFORM_GREEN
            elif v < 0.65:
                color = WAVEFORM_MID
            else:
                color = WAVEFORM_RED

            # Draw bar from center up and down
            self.canvas.create_line(
                x, center_y - bar_h,
                x, center_y + bar_h,
                fill=color,
                width=max(1, step),
            )

        # Center line
        self.canvas.create_line(0, center_y, w, center_y, fill=BORDER, width=1)

        # Draw phrase regions
        if phrase_points:
            for pp in phrase_points:
                pos = pp.get("position", 0)
                label = pp.get("label", "").upper()
                x = int(pos * w)

                color_map = {
                    "START": WAVEFORM_GREEN,
                    "BUILD": WAVEFORM_MID,
                    "PEAK": WAVEFORM_RED,
                    "DROP": WAVEFORM_RED,
                    "OUTRO": BLUE_BRIGHT,
                }
                line_color = color_map.get(label, TEXT_DIM)

                self.canvas.create_line(x, 0, x, h, fill=line_color, width=1, dash=(4, 4))
                self.canvas.create_text(
                    x + 4, 10,
                    text=label,
                    fill=line_color,
                    font=("Consolas", 8),
                    anchor="w",
                )

    def _fmt_dur(self, seconds):
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m}:{s:02d}"
