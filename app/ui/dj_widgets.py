"""
DJ AI OS — Pro DJ Widgets

Professional DJ booth widgets: vinyl, waveform, VU meters, crossfader.
Rekordbox/Serato inspired — clean, high-contrast, club-proof.
"""

import math
import tkinter as tk
import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER,
    RED, RED_HOVER, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
)

# Pro DJ constants
BOOTH_BG = "#08080C"
VINYL_BG = "#1A1A1E"
VINYL_GROOVE = "#25252E"
VINYL_LABEL = RED
SCOPE_GREEN = GREEN
SCOPE_RED = RED
SCOPE_DIM = "#1A1A1E"


class SpinningVinyl(tk.Canvas):
    """Animated vinyl record that spins when playing."""

    def __init__(self, master, radius=90, **kwargs):
        self._size = radius * 2 + 20
        super().__init__(master, width=self._size, height=self._size,
                         bg=BOOTH_BG, highlightthickness=0, **kwargs)
        self._radius = radius
        self._angle = 0
        self._spinning = False
        self._track_name = ""
        self._after_id = None
        self._draw()

    def set_track(self, track):
        self._track_name = track.get("name", "")[:20]

    def start_spin(self):
        self._spinning = True
        self._animate()

    def stop_spin(self):
        self._spinning = False

    def _animate(self):
        if not self._spinning:
            return
        self._angle = (self._angle + 2) % 360
        self._draw()
        self._after_id = self.after(40, self._animate)

    def _draw(self):
        self.delete("all")
        cx = self._size / 2
        cy = self._size / 2
        r = self._radius

        # Outer ring
        self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=VINYL_BG, outline="#333", width=2)

        # Grooves
        for groove_r in range(int(r*0.35), int(r*0.9), 4):
            self.create_oval(cx-groove_r, cy-groove_r, cx+groove_r, cy+groove_r,
                              outline=VINYL_GROOVE, width=1)

        # Center label
        label_r = int(r * 0.3)
        self.create_oval(cx-label_r, cy-label_r, cx+label_r, cy+label_r,
                          fill=VINYL_LABEL, outline="")

        # Spindle
        self.create_oval(cx-4, cy-4, cx+4, cy+4, fill=TEXT_PRIMARY, outline="")

        # Rotating dot to show spin
        if self._spinning:
            rad = math.radians(self._angle)
            dot_x = cx + math.cos(rad) * (label_r - 5)
            dot_y = cy + math.sin(rad) * (label_r - 5)
            self.create_oval(dot_x-3, dot_y-3, dot_x+3, dot_y+3, fill="white", outline="")

        # Track name
        if self._track_name:
            self.create_text(cx, cy + r + 12, text=self._track_name,
                              fill=TEXT_SECONDARY, font=("Segoe UI", 9))


class WaveformDisplay(tk.Canvas):
    """Serato-style colored waveform display."""

    def __init__(self, master, width=800, height=120, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._waveform = []
        self._playhead = 0.0  # 0.0 - 1.0
        self._bpm = 0
        self._key = ""
        self._playing = False

    def set_waveform(self, waveform):
        self._waveform = waveform or []
        self._draw()

    def set_playhead(self, position):
        self._playhead = max(0.0, min(1.0, position))
        self._draw()

    def set_info(self, bpm=0, key=""):
        self._bpm = bpm
        self._key = key

    def _draw(self):
        self.delete("all")
        w = max(self.winfo_width(), 800)
        h = max(self.winfo_height(), 120)
        cy = h // 2

        # Center line
        self.create_line(0, cy, w, cy, fill=BORDER, width=1)

        if not self._waveform:
            self.create_text(w//2, cy, text="Drop track to see waveform",
                              fill=TEXT_DIM, font=("Segoe UI", 10))
            # BPM/KEY overlay
            if self._bpm:
                self.create_text(12, 12, text=f"{self._bpm:.0f} BPM", fill=RED,
                                  font=("Consolas", 11, "bold"), anchor="w")
            if self._key:
                self.create_text(12, 28, text=f"KEY {self._key}", fill=BLUE_BRIGHT,
                                  font=("Consolas", 10), anchor="w")
            return

        # Draw waveform bars
        n = len(self._waveform)
        step = max(1, w / n)

        for i, val in enumerate(self._waveform):
            x = i * step
            v = abs(val) if isinstance(val, (int, float)) else 0.5
            bar_h = int(v * cy * 0.9)
            bar_h = max(1, min(cy - 2, bar_h))

            if v < 0.35:
                color = GREEN
            elif v < 0.65:
                color = AMBER
            else:
                color = RED

            self.create_line(x, cy - bar_h, x, cy + bar_h, fill=color, width=max(1, step))

        # Playhead
        ph_x = self._playhead * w
        self.create_line(ph_x, 0, ph_x, h, fill=TEXT_PRIMARY, width=2)

        # BPM/KEY overlay
        if self._bpm:
            self.create_text(w - 12, 12, text=f"{self._bpm:.0f} BPM", fill=RED,
                              font=("Consolas", 11, "bold"), anchor="e")
        if self._key:
            self.create_text(w - 12, 28, text=f"KEY {self._key}", fill=BLUE_BRIGHT,
                              font=("Consolas", 10), anchor="e")


class VUMeter(tk.Canvas):
    """Vertical VU meter with level bars."""

    def __init__(self, master, height=150, width=20, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._level = 0.0
        self._peak = 0.0

    def set_level(self, level):
        self._level = max(0.0, min(1.0, level))
        self._peak = max(self._peak - 0.02, self._level)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        # Background
        self.create_rectangle(0, 0, w, h, fill=BG, outline=BORDER)

        # Level bars
        num_bars = int(h / 6)
        filled = int(num_bars * self._level)

        for i in range(num_bars):
            y = h - (i + 1) * 6
            ratio = i / num_bars

            if ratio < 0.6:
                color = GREEN
            elif ratio < 0.8:
                color = AMBER
            else:
                color = RED

            if i < filled:
                self.create_rectangle(2, y, w - 2, y + 4, fill=color, outline="")
            else:
                self.create_rectangle(2, y, w - 2, y + 4, fill=SCOPE_DIM, outline="")

        # Peak indicator
        peak_y = h - int(num_bars * self._peak) * 6
        self.create_rectangle(2, peak_y, w - 2, peak_y + 2, fill=TEXT_PRIMARY, outline="")


class Crossfader(tk.Canvas):
    """Horizontal crossfader with visual position."""

    def __init__(self, master, width=500, height=30, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._position = 0.5  # 0.0 = A, 1.0 = B
        self._draw()

    def set_position(self, pos):
        self._position = max(0.0, min(1.0, pos))
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        cy = h // 2

        # Track
        self.create_rectangle(20, cy - 3, w - 20, cy + 3, fill=SCOPE_DIM, outline=BORDER)

        # Fill from center
        center = w // 2
        fader_x = 20 + (w - 40) * self._position
        if self._position < 0.5:
            self.create_rectangle(fader_x, cy - 2, center, cy + 2, fill=BLUE_BRIGHT, outline="")
        else:
            self.create_rectangle(center, cy - 2, fader_x, cy + 2, fill=RED, outline="")

        # Handle
        self.create_rectangle(fader_x - 8, cy - 10, fader_x + 8, cy + 10,
                              fill=TEXT_PRIMARY, outline=BORDER, width=1)

        # Labels
        self.create_text(12, cy, text="A", fill=BLUE_BRIGHT, font=("Consolas", 10, "bold"))
        self.create_text(w - 12, cy, text="B", fill=RED, font=("Consolas", 10, "bold"))


class HotCuePads(tk.Canvas):
    """8 hot cue pads that light up on trigger."""

    def __init__(self, master, deck="A", width=400, height=60, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._deck = deck
        self._pads = [None] * 8
        self._colors = ["#00FFA3", "#FF3DF2", "#FFB020", "#22D3FF",
                        "#9B5CFF", "#FF4D6D", "#457B9D", "#FFFFFF"]
        self._active = [False] * 8
        self._draw()

    def set_pad(self, index, active=True, color=None):
        if 0 <= index < 8:
            self._active[index] = active
            if color:
                self._colors[index] = color
            self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        pad_w = (w - 20) // 8
        cy = self.winfo_height() // 2

        for i in range(8):
            x = 10 + i * (pad_w + 2)
            color = self._colors[i] if self._active[i] else SCOPE_DIM

            self.create_rectangle(x, 5, x + pad_w, cy * 2 - 5,
                                  fill=color, outline=BORDER, width=1)

            self.create_text(x + pad_w // 2, cy,
                              text=f"C{i+1}", fill=TEXT_PRIMARY if self._active[i] else TEXT_DIM,
                              font=("Consolas", 9, "bold"))


class BPMCounter(tk.Canvas):
    """Large BPM display with animated tempo indicator."""

    def __init__(self, master, width=160, height=80, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._bpm = 0
        self._confidence = 0
        self._draw()

    def set_bpm(self, bpm, confidence=0):
        self._bpm = bpm
        self._confidence = confidence
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        cx = w // 2
        cy = h // 2

        # Background
        self.create_rectangle(0, 0, w, h, fill=BG, outline=BORDER, width=1)

        # BPM number (large)
        self.create_text(cx, cy - 5, text=f"{self._bpm:.0f}", fill=TEXT_PRIMARY,
                          font=("Consolas", 28, "bold"))

        # Label
        self.create_text(cx, cy + 22, text="BPM", fill=TEXT_DIM,
                          font=("Consolas", 9))

        # Confidence bar
        bar_w = int((w - 20) * self._confidence)
        self.create_rectangle(10, h - 8, 10 + bar_w, h - 4, fill=GREEN, outline="")
        self.create_rectangle(10 + bar_w, h - 8, w - 10, h - 4, fill=SCOPE_DIM, outline="")


class KeyDisplay(tk.Canvas):
    """Camelot key display with compatibility indicator."""

    def __init__(self, master, width=100, height=80, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._key = ""
        self._compatible = False
        self._draw()

    def set_key(self, key, compatible=False):
        self._key = key
        self._compatible = compatible
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        cx = w // 2
        cy = h // 2

        color = BLUE_BRIGHT if self._compatible else TEXT_PRIMARY

        self.create_rectangle(0, 0, w, h, fill=BG, outline=BORDER, width=1)
        self.create_text(cx, cy - 5, text=self._key, fill=color,
                          font=("Consolas", 20, "bold"))
        self.create_text(cx, cy + 20, text="KEY", fill=TEXT_DIM,
                          font=("Consolas", 9))

        # Compatibility indicator
        if self._compatible:
            self.create_oval(w - 16, 4, w - 4, 16, fill=GREEN, outline="")


class EnergyCurve(tk.Canvas):
    """Set energy flow visualization."""

    def __init__(self, master, width=600, height=60, **kwargs):
        super().__init__(master, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._energies = []
        self._current_idx = 0

    def set_energies(self, energies, current_idx=0):
        self._energies = energies
        self._current_idx = current_idx
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        if not self._energies:
            self.create_text(w//2, h//2, text="Set energy curve", fill=TEXT_DIM,
                              font=("Segoe UI", 9))
            return

        n = len(self._energies)
        step = max(1, (w - 20) / n)

        for i, energy in enumerate(self._energies):
            x = 10 + i * step
            bar_h = int(energy * (h - 10))
            y = h - 5 - bar_h

            is_current = (i == self._current_idx)
            color = RED if is_current else (AMBER if energy > 0.7 else GREEN if energy > 0.4 else BLUE_BRIGHT)

            self.create_rectangle(x, y, x + step - 1, h - 5, fill=color, outline="")

        # Current position marker
        if self._current_idx < n:
            cx = 10 + self._current_idx * step + step // 2
            self.create_line(cx, 0, cx, h, fill=TEXT_PRIMARY, width=2)


# ============================================================
# BACKWARD COMPATIBILITY ALIASES
# ============================================================

# Old names that other modules still import
class HarmonicWheel(tk.Canvas):
    """Compatibility wrapper for old HarmonicWheel interface."""

    COMPATIBLE_KEYS = {
        "1A": ["1A", "2A", "12A", "1B"], "2A": ["2A", "1A", "3A", "2B"],
        "3A": ["3A", "2A", "4A", "3B"], "4A": ["4A", "3A", "5A", "4B"],
        "5A": ["5A", "4A", "6A", "5B"], "6A": ["6A", "5A", "7A", "6B"],
        "7A": ["7A", "6A", "8A", "7B"], "8A": ["8A", "7A", "9A", "8B"],
        "9A": ["9A", "8A", "10A", "9B"], "10A": ["10A", "9A", "11A", "10B"],
        "11A": ["11A", "10A", "12A", "11B"], "12A": ["12A", "11A", "1A", "12B"],
        "1B": ["1B", "2B", "12B", "1A"], "2B": ["2B", "1B", "3B", "2A"],
        "3B": ["3B", "2B", "4B", "3A"], "4B": ["4B", "3B", "5B", "4A"],
        "5B": ["5B", "4B", "6B", "5A"], "6B": ["6B", "5B", "7B", "6A"],
        "7B": ["7B", "6B", "8B", "7A"], "8B": ["8B", "7B", "9B", "8A"],
        "9B": ["9B", "8B", "10B", "9A"], "10B": ["10B", "9B", "11B", "10A"],
        "11B": ["11B", "10B", "12B", "11A"], "12B": ["12B", "11B", "1B", "12A"],
    }

    def __init__(self, master, radius=95, **kwargs):
        size = radius * 2 + 20
        super().__init__(master, width=size, height=size, bg=BG, highlightthickness=0, **kwargs)
        self._radius = radius
        self._deck_a_key = ""
        self._deck_b_key = ""
        self._draw()

    def set_keys(self, deck_a="", deck_b=""):
        self._deck_a_key = deck_a
        self._deck_b_key = deck_b
        self._draw()

    def _draw(self):
        self.delete("all")
        cx = self.winfo_width() / 2
        cy = self.winfo_height() / 2
        r = self._radius

        # Draw wheel
        self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=BG, outline=BORDER, width=2)

        # Draw 12 segments
        for i in range(12):
            angle = math.radians(i * 30 - 90)
            x = cx + math.cos(angle) * (r - 15)
            y = cy + math.sin(angle) * (r - 15)
            key = f"{i+1}A"
            self.create_text(x, y, text=key, fill=TEXT_DIM, font=("Consolas", 7))

        # Highlight active keys
        if self._deck_a_key:
            self._draw_key_highlight(cx, cy, r, self._deck_a_key, BLUE_BRIGHT)
        if self._deck_b_key:
            self._draw_key_highlight(cx, cy, r, self._deck_b_key, RED)

    def _draw_key_highlight(self, cx, cy, r, key, color):
        try:
            num = int(key[:-1])
            letter = key[-1]
            idx = num - 1 if letter == "A" else num - 1 + 12
            angle = math.radians(idx * 30 - 90)
            x = cx + math.cos(angle) * (r - 15)
            y = cy + math.sin(angle) * (r - 15)
            self.create_oval(x-8, y-8, x+8, y+8, fill=color, outline="")
            self.create_text(x, y, text=key, fill="white", font=("Consolas", 7, "bold"))
        except Exception:
            pass


# Old widget names for backward compat
GlassCard = None  # Will be imported from glass.py if needed
