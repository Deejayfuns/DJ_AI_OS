"""Futuristic DJ booth canvas widgets for DJ AI OS.

All widgets are canvas-based with after() animation loops.
They share a consistent visual language: dark backgrounds,
neon glow accents, smooth phase-based animations.

Usage:
    from app.ui.dj_widgets import SpinningVinyl, BPMScope, HarmonicWheel

    vinyl = SpinningVinyl(parent, radius=90)
    vinyl.pack()
    vinyl.set_track({"name": "Track A", "bpm": 128})
"""

import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    BACKGROUND,
    CARD,
    GLASS_BG,
    GLASS_BORDER,
    NEON_BLUE,
    NEON_MAGENTA,
    NEON_PURPLE,
    PANEL,
    TEXT,
    MUTED,
    DANGER,
    WARNING,
    SUCCESS,
    SP1,
    SP2,
    R_MED,
)


# ============================================================
# Constants
# ============================================================

BOOTH_BG = "#050A15"
SCOPE_GREEN = "#00FFA3"
SCOPE_BLUE = "#22D3FF"
SCOPE_DIM = "#1A3A5C"
VINYL_COLOR = "#1A1A2E"
VINYL_GROOVE = "#252540"
VINYL_LABEL = "#0D0D1A"

# Camelot wheel colors (12 keys)
CAMELOT_COLORS = [
    "#00FFA3", "#22D3FF", "#9B5CFF", "#FF3DF2",
    "#FFB020", "#FF4D6D", "#00C896", "#2979FF",
    "#7B61FF", "#FF6B9D", "#00E5A0", "#40E0D0",
]

CAMELOT_KEYS = [
    "8B", "3B", "10B", "5B", "12B", "7B",
    "2B", "9B", "4B", "11B", "6B", "1B",
]


# ============================================================
# SpinningVinyl — animated rotating turntable
# ============================================================

class SpinningVinyl(ctk.CTkFrame):
    """Animated spinning vinyl record with groove rings and label."""

    def __init__(self, master, radius=90, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._radius = radius
        self._diameter = radius * 2 + 20
        self._phase = 0
        self._speed = 2
        self._track = {}

        self._canvas = tk.Canvas(
            self,
            width=self._diameter,
            height=self._diameter,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        self.after(60, self._tick)

    def set_track(self, track):
        self._track = dict(track or {})
        self._speed = max(1, min(5, int(self._track.get("bpm", 120) / 30)))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + self._speed) % 360
        self._render()
        self.after(50, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        cx = self._diameter / 2
        cy = self._diameter / 2
        r = self._radius

        # Outer glow
        for i in range(3, 0, -1):
            c.create_oval(
                cx - r - i * 3, cy - r - i * 3,
                cx + r + i * 3, cy + r + i * 3,
                outline=ACCENT + "15",
                width=1,
            )

        # Vinyl body
        c.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=VINYL_COLOR,
            outline="#2A2A4A",
            width=2,
        )

        # Groove rings
        for groove_r in range(int(r * 0.35), int(r * 0.95), 6):
            c.create_oval(
                cx - groove_r, cy - groove_r,
                cx + groove_r, cy + groove_r,
                outline=VINYL_GROOVE,
                width=1,
            )

        # Rotating highlight (simulates light reflection)
        angle = math.radians(self._phase)
        highlight_x = cx + math.cos(angle) * r * 0.6
        highlight_y = cy + math.sin(angle) * r * 0.6
        glow_r = 12 + 4 * math.sin(math.radians(self._phase * 2))
        c.create_oval(
            highlight_x - glow_r, highlight_y - glow_r,
            highlight_x + glow_r, highlight_y + glow_r,
            fill=ACCENT + "20",
            outline="",
        )

        # Center label
        label_r = r * 0.3
        c.create_oval(
            cx - label_r, cy - label_r,
            cx + label_r, cy + label_r,
            fill=VINYL_LABEL,
            outline=NEON_PURPLE,
            width=2,
        )

        # Center dot
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=ACCENT, outline="")

        # BPM text
        bpm = self._track.get("bpm", "--")
        c.create_text(
            cx, cy - 8,
            text=f"{bpm}",
            fill=TEXT,
            font=("Segoe UI", 14, "bold"),
        )
        c.create_text(
            cx, cy + 10,
            text="BPM",
            fill=MUTED,
            font=("Segoe UI", 7),
        )


# ============================================================
# BPMScope — oscilloscope-style beat visualization
# ============================================================

class BPMScope(ctk.CTkFrame):
    """Oscilloscope-style beat visualization with grid lines."""

    def __init__(self, master, width=400, height=120, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._width = width
        self._height = height
        self._phase = 0
        self._bpm = 120
        self._energy = 0.5
        self._beat_phase = 0

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        self.after(40, self._tick)

    def update_data(self, bpm=120, energy=0.5):
        self._bpm = max(60, min(200, bpm))
        self._energy = max(0, min(1, energy))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 2) % 360
        self._beat_phase = (self._beat_phase + self._bpm / 60 * 4) % 360
        self._render()
        self.after(33, self._tick)  # ~30fps

    def _render(self):
        c = self._canvas
        c.delete("all")
        w = self._width
        h = self._height
        center_y = h / 2

        # Grid lines (beat markers)
        beat_width = max(1, int(w / max(1, (60 / self._bpm) * 4 / 0.033)))
        for x in range(0, w, max(1, beat_width)):
            is_bar = (x // max(1, beat_width)) % 4 == 0
            color = SCOPE_DIM if is_bar else "#0D1520"
            c.create_line(x, 0, x, h, fill=color, width=1 if is_bar else 1)

        # Center line
        c.create_line(0, center_y, w, center_y, fill=SCOPE_DIM, width=1)

        # Beat waveform
        points = []
        for x in range(w):
            t = x / max(1, w)
            # Composite waveform: bass + mid + treble
            bass = math.sin(2 * math.pi * t * 4 + math.radians(self._beat_phase)) * 0.4
            mid = math.sin(2 * math.pi * t * 8 + math.radians(self._phase * 1.5)) * 0.25
            treble = math.sin(2 * math.pi * t * 16 + math.radians(self._phase * 3)) * 0.15

            # Beat accent
            beat_pos = (self._beat_phase / 360) % 1
            beat_dist = abs(t - beat_pos)
            beat_pulse = max(0, 1 - beat_dist * 8) * 0.3

            value = (bass + mid + treble + beat_pulse) * self._energy
            y = center_y - value * (h / 2 - 10)
            points.append((x, y))

        # Draw waveform
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            intensity = abs(y1 - center_y) / (h / 2)
            if intensity > 0.6:
                color = "#EAF2FF"
            elif intensity > 0.3:
                color = SCOPE_GREEN
            else:
                color = SCOPE_BLUE
            c.create_line(x1, y1, x2, y2, fill=color, width=2)

        # Beat position marker
        beat_x = int((self._beat_phase / 360 % 1) * w)
        c.create_line(beat_x, 0, beat_x, h, fill=ACCENT, width=2, dash=(3, 3))


# ============================================================
# EnergyOrb — pulsating energy sphere
# ============================================================

class EnergyOrb(ctk.CTkFrame):
    """Pulsating energy sphere with outer reaction rings."""

    def __init__(self, master, radius=40, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._radius = radius
        self._diameter = radius * 2 + 40
        self._phase = 0
        self._energy = 0.5

        self._canvas = tk.Canvas(
            self,
            width=self._diameter,
            height=self._diameter,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        self.after(60, self._tick)

    def set_energy(self, energy):
        self._energy = max(0, min(1, float(energy)))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 2) % 360
        self._render()
        self.after(60, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        cx = self._diameter / 2
        cy = self._diameter / 2
        r = self._radius

        # Outer reaction rings
        for ring in range(3):
            pulse = math.sin(math.radians(self._phase * 2 + ring * 40)) * 0.3
            ring_r = r + 8 + ring * 8 + pulse * r * 0.2
            alpha_val = max(10, 40 - ring * 12)
            # Color based on energy
            if self._energy > 0.7:
                ring_color = f"#FF3DF2{alpha_val:02x}"
            elif self._energy > 0.4:
                ring_color = f"#9B5CFF{alpha_val:02x}"
            else:
                ring_color = f"#22D3FF{alpha_val:02x}"

            c.create_oval(
                cx - ring_r, cy - ring_r,
                cx + ring_r, cy + ring_r,
                outline=ring_color,
                width=1,
            )

        # Main orb
        # Gradient effect via concentric circles
        for i in range(5):
            shrink = i * (r / 6)
            orb_r = r - shrink
            t = i / 5

            if self._energy > 0.7:
                red = int(0 + 255 * t)
                green = int(255 * (1 - t * 0.5))
                blue = int(242 * (1 - t))
            elif self._energy > 0.4:
                red = int(155 * t)
                green = int(92 + 163 * (1 - t))
                blue = int(255 * (1 - t * 0.3))
            else:
                red = int(34 * t)
                green = int(211 * (1 - t * 0.5))
                blue = int(255)

            color = f"#{red:02x}{green:02x}{blue:02x}"
            c.create_oval(
                cx - orb_r, cy - orb_r,
                cx + orb_r, cy + orb_r,
                fill=color if i == 4 else "",
                outline=color if i < 4 else "",
                width=1,
            )

        # Center bright point
        c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#FFFFFF", outline="")

        # Energy percentage
        c.create_text(
            cx, cy + r + 18,
            text=f"{int(self._energy * 100)}%",
            fill=ACCENT,
            font=("Segoe UI", 10, "bold"),
        )


# ============================================================
# HarmonicWheel — interactive Camelot wheel
# ============================================================

class HarmonicWheel(ctk.CTkFrame):
    """Interactive Camelot harmonic compatibility wheel."""

    COMPATIBLE_KEYS = {
        "8B": ["8B", "9B", "7B", "8A"],
        "9B": ["9B", "10B", "8B", "9A"],
        "10B": ["10B", "11B", "9B", "10A"],
        "11B": ["11B", "12B", "10B", "11A"],
        "12B": ["12B", "1B", "11B", "12A"],
        "1B": ["1B", "2B", "12B", "1A"],
        "2B": ["2B", "3B", "1B", "2A"],
        "3B": ["3B", "4B", "2B", "3A"],
        "4B": ["4B", "5B", "3B", "4A"],
        "5B": ["5B", "6B", "4B", "5A"],
        "6B": ["6B", "7B", "5B", "6A"],
        "7B": ["7B", "8B", "6B", "7A"],
        "8A": ["8A", "9A", "7A", "8B"],
        "9A": ["9A", "10A", "8A", "9B"],
        "10A": ["10A", "11A", "9A", "10B"],
        "11A": ["11A", "12A", "10A", "11B"],
        "12A": ["12A", "1A", "11A", "12B"],
        "1A": ["1A", "2A", "12A", "1B"],
        "2A": ["2A", "3A", "1A", "2B"],
        "3A": ["3A", "4A", "2A", "3B"],
        "4A": ["4A", "5A", "3A", "4B"],
        "5A": ["5A", "6A", "4A", "5B"],
        "6A": ["6A", "7A", "5A", "6B"],
        "7A": ["7A", "8A", "6A", "7B"],
    }

    def __init__(self, master, radius=110, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._radius = radius
        self._diameter = radius * 2 + 40
        self._phase = 0
        self._selected_key = "8A"
        self._deck_a_key = ""
        self._deck_b_key = ""

        self._canvas = tk.Canvas(
            self,
            width=self._diameter,
            height=self._diameter,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()
        self._canvas.bind("<Button-1>", self._on_click)

        self.after(100, self._tick)

    def set_keys(self, deck_a="", deck_b=""):
        self._deck_a_key = deck_a
        self._deck_b_key = deck_b
        if deck_a:
            self._selected_key = deck_a

    def _on_click(self, event):
        cx = self._diameter / 2
        cy = self._diameter / 2
        dx = event.x - cx
        dy = event.y - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > self._radius + 10 or dist < self._radius * 0.25:
            return

        angle = math.degrees(math.atan2(dy, dx))
        # Convert angle to key index (0-11)
        index = int(((angle + 90) % 360) / 30) % 12
        if index < 12:
            self._selected_key = CAMELOT_KEYS[index]

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 1) % 360
        self._render()
        self.after(80, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        cx = self._diameter / 2
        cy = self._diameter / 2
        r = self._radius

        # Outer ring
        c.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4,
                       outline=GLASS_BORDER, width=1)

        # Inner ring
        c.create_oval(cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3,
                       outline=SCOPE_DIM, width=1)

        # 12 slices
        compatible = set(self.COMPATIBLE_KEYS.get(self._selected_key, []))

        for i in range(12):
            start_angle = -90 + i * 30
            end_angle = start_angle + 30
            key = CAMELOT_KEYS[i]
            color_idx = i % 12

            # Determine fill
            is_compatible = key in compatible
            is_selected = key == self._selected_key
            is_deck_a = key == self._deck_a_key
            is_deck_b = key == self._deck_b_key

            if is_selected:
                fill_color = ACCENT + "40"
            elif is_compatible:
                fill_color = CAMELOT_COLORS[color_idx] + "20"
            else:
                fill_color = BOOTH_BG

            # Draw slice
            c.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=start_angle, extent=30,
                fill=fill_color,
                outline=CAMELOT_COLORS[color_idx] + "30",
                width=1,
            )

            # Key label
            label_r = r * 0.7
            label_angle = math.radians(start_angle + 15)
            lx = cx + math.cos(label_angle) * label_r
            ly = cy + math.sin(label_angle) * label_r

            text_color = ACCENT if is_selected else (
                CAMELOT_COLORS[color_idx] if is_compatible else MUTED
            )
            font_size = 9 if is_selected else 7

            c.create_text(
                lx, ly,
                text=key,
                fill=text_color,
                font=("Segoe UI", font_size, "bold" if is_selected else ""),
            )

            # Deck markers
            marker_r = r * 0.5
            mx = cx + math.cos(label_angle) * marker_r
            my = cy + math.sin(label_angle) * marker_r

            if is_deck_a:
                c.create_text(mx, my - 4, text="A", fill=SCOPE_GREEN,
                              font=("Segoe UI", 7, "bold"))
            if is_deck_b:
                c.create_text(mx, my + 6, text="B", fill=SCOPE_BLUE,
                              font=("Segoe UI", 7, "bold"))

        # Center text
        c.create_text(cx, cy - 6, text=self._selected_key, fill=ACCENT,
                       font=("Segoe UI", 16, "bold"))
        c.create_text(cx, cy + 12, text="KEY", fill=MUTED,
                       font=("Segoe UI", 8))


# ============================================================
# VUMeter — analog-style level meter
# ============================================================

class VUMeter(ctk.CTkFrame):
    """Vertical analog-style VU meter with dB scale."""

    def __init__(self, master, height=120, width=24, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._height = height
        self._width = width
        self._level = 0.0
        self._peak = 0.0
        self._phase = 0

        self._canvas = tk.Canvas(
            self,
            width=width + 30,
            height=height,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        self.after(50, self._tick)

    def set_level(self, level):
        self._level = max(0, min(1, float(level)))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 3) % 360
        # Decay peak
        self._peak = max(self._level, self._peak * 0.95)
        self._render()
        self.after(40, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        h = self._height
        w = self._width

        # Meter background
        c.create_rectangle(4, 2, w + 4, h - 2, fill="#0A0E18", outline=GLASS_BORDER)

        # Level bars
        bar_h = int(h * self._level)
        for i in range(bar_h):
            y = h - 4 - i
            t = i / max(1, h - 8)
            if t > 0.85:
                color = DANGER
            elif t > 0.65:
                color = WARNING
            else:
                color = SUCCESS
            c.create_line(5, y, w + 3, y, fill=color, width=1)

        # Peak marker
        peak_y = h - 4 - int(h * self._peak)
        c.create_line(5, peak_y, w + 3, peak_y, fill="#FFFFFF", width=2)

        # dB labels
        for db in [0, -6, -12, -24, -48]:
            y = h - 4 - int(h * (1 + db / 48))
            if 0 < y < h:
                c.create_text(w + 16, y, text=str(db), fill=MUTED,
                              font=("Segoe UI", 6), anchor="w")


# ============================================================
# Crossfader — visual crossfader slider
# ============================================================

class Crossfader(ctk.CTkFrame):
    """Visual crossfader between Deck A and Deck B."""

    def __init__(self, master, width=300, height=30, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._width = width
        self._height = height
        self._position = 0.5  # 0=A, 1=B
        self._phase = 0

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)

        self.after(80, self._tick)

    def set_position(self, pos):
        self._position = max(0, min(1, float(pos)))

    def _on_click(self, event):
        self._position = max(0, min(1, event.x / self._width))

    def _on_drag(self, event):
        self._position = max(0, min(1, event.x / self._width))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 2) % 360
        self._render()
        self.after(60, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        w = self._width
        h = self._height
        mid_y = h / 2

        # Track
        c.create_rectangle(0, mid_y - 3, w, mid_y + 3,
                           fill="#0A1020", outline=GLASS_BORDER)

        # Active fill
        fill_w = int(w * self._position)
        if fill_w > 0:
            # Gradient from green (A) to blue (B)
            for x in range(0, fill_w, 2):
                t = x / max(1, w)
                r = int(0 + 34 * t)
                g = int(255 - 44 * t)
                b = int(163 + 92 * t)
                color = f"#{r:02x}{g:02x}{b:02x}"
                c.create_line(x, mid_y - 2, x + 2, mid_y + 2, fill=color, width=3)

        # Handle
        handle_x = int(w * self._position)
        handle_r = 8 + 2 * math.sin(math.radians(self._phase * 2))
        c.create_oval(
            handle_x - handle_r, mid_y - handle_r,
            handle_x + handle_r, mid_y + handle_r,
            fill=ACCENT,
            outline="#FFFFFF",
            width=2,
        )

        # Labels
        c.create_text(12, h - 2, text="A", fill=SCOPE_GREEN,
                       font=("Segoe UI", 8, "bold"), anchor="sw")
        c.create_text(w - 12, h - 2, text="B", fill=SCOPE_BLUE,
                       font=("Segoe UI", 8, "bold"), anchor="se")


# ============================================================
# SetEnergyCurve — energy flow across the set
# ============================================================

class SetEnergyCurve(ctk.CTkFrame):
    """Energy flow visualization across the entire set."""

    def __init__(self, master, width=600, height=60, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._width = width
        self._height = height
        self._phase = 0
        self._energies = []
        self._current_index = 0

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=BOOTH_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        self.after(80, self._tick)

    def set_energies(self, energies, current_index=0):
        self._energies = list(energies or [])
        self._current_index = current_index

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 1) % 360
        self._render()
        self.after(80, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        w = self._width
        h = self._height

        if not self._energies:
            c.create_text(w / 2, h / 2, text="ENERGY FLOW — set olusturunca gorunur",
                           fill=MUTED, font=("Segoe UI", 9))
            return

        n = len(self._energies)
        step = max(1, w // max(1, n))

        # Fill area under curve
        points = []
        for i, energy in enumerate(self._energies):
            x = int(i * step + step / 2)
            y = h - 8 - int(energy * (h - 16))
            points.append((x, y))

        # Gradient fill
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2 = points[i + 1][0]
            energy = self._energies[i]
            t = energy
            r = int(0 + 255 * t)
            g = int(255 * (1 - t * 0.3))
            b = int(163 * (1 - t))
            color = f"#{r:02x}{g:02x}{b:02x}30"
            c.create_rectangle(x1, y1, x2, h - 8, fill=color, outline="")

        # Curve line
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            energy = self._energies[i]
            if energy > 0.7:
                color = NEON_MAGENTA
            elif energy > 0.4:
                color = ACCENT
            else:
                color = SCOPE_BLUE
            c.create_line(x1, y1, x2, y2, fill=color, width=2)

        # Current position marker
        if 0 <= self._current_index < len(points):
            cx, cy = points[self._current_index]
            pulse = 4 + 2 * math.sin(math.radians(self._phase * 3))
            c.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse,
                           fill=ACCENT, outline="#FFFFFF", width=2)

        # Phase labels
        labels = ["WARMUP", "GROOVE", "PEAK", "COOL"]
        for i, label in enumerate(labels):
            x = int((i + 0.5) * w / len(labels))
            c.create_text(x, h - 2, text=label, fill=MUTED,
                           font=("Segoe UI", 7), anchor="s")
