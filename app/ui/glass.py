"""
DJ AI OS — Pro DJ Glass/Visual Primitives

Clean, professional drawing helpers for tkinter canvas.
Replaces neon glow with subtle shadows, clean borders, and energy bars.

Usage:
    from app.ui.glass import draw_energy_bar, draw_stat_card, draw_separator

    draw_energy_bar(canvas, x, y, w, h, value=0.75)
    draw_separator(parent, width=100)
"""

import math
import tkinter as tk
import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, BLUE_BRIGHT, GREEN, AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, RED_DIM,
)


# ============================================================
# COLOR UTILS
# ============================================================

def safe_alpha(hex_color, alpha_pct):
    """Blend hex color with background at given alpha (0.0–1.0)."""
    try:
        r1, g1, b1 = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r2, g2, b2 = int(BG[1:3], 16), int(BG[3:5], 16), int(BG[5:7], 16)
        a = max(0.0, min(1.0, alpha_pct))
        r = int(r1 * a + r2 * (1 - a))
        g = int(g1 * a + g2 * (1 - a))
        b = int(b1 * a + b2 * (1 - a))
        return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        return hex_color


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")[:6]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def value_to_color(value, low_color=BLUE_BRIGHT, mid_color=GREEN, high_color=RED):
    """Map a 0.0–1.0 value to a color gradient."""
    if value < 0.5:
        t = value * 2
        r1, g1, b1 = _hex_to_rgb(low_color)
        r2, g2, b2 = _hex_to_rgb(mid_color)
    else:
        t = (value - 0.5) * 2
        r1, g1, b1 = _hex_to_rgb(mid_color)
        r2, g2, b2 = _hex_to_rgb(high_color)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# CANVAS PRIMITIVES
# ============================================================

def draw_energy_bar(canvas, x, y, width, height, value=0.0, label=""):
    """Draw a horizontal energy bar (clean, no glow)."""
    canvas.create_rectangle(x, y, x + width, y + height, fill=BG, outline=BORDER)

    fill_w = max(0, int(width * max(0.0, min(1.0, value))))
    color = value_to_color(value)

    if fill_w > 0:
        canvas.create_rectangle(x, y, x + fill_w, y + height, fill=color, outline="")

    if label:
        canvas.create_text(x + width + 8, y + height // 2, text=label, fill=TEXT_SECONDARY, anchor="w")


def draw_progress_bar(parent, value=0.0, height=4, color=RED):
    """Create a progress bar widget."""
    bar = ctk.CTkFrame(parent, fg_color=BG, height=height, corner_radius=2)
    bar.pack_propagate(False)

    fill = ctk.CTkFrame(bar, fg_color=color, height=height, corner_radius=2)
    fill.place(relx=0, rely=0, relwidth=max(0.0, min(1.0, value)), relheight=1.0)

    return bar


def draw_stat_badge(parent, label, value, color=RED, font=("Segoe UI", 11)):
    """Draw a compact stat badge (label: value)."""
    frame = ctk.CTkFrame(parent, fg_color=BG, corner_radius=4, border_width=1, border_color=BORDER)
    frame.pack(side="left", padx=4, pady=2)

    ctk.CTkLabel(frame, text=label, font=font, text_color=TEXT_SECONDARY).pack(side="left", padx=(8, 2), pady=4)
    ctk.CTkLabel(frame, text=str(value), font=font, text_color=color).pack(side="left", padx=(2, 8), pady=4)

    return frame


def draw_separator(parent, width=None, color=BORDER):
    """Draw a horizontal separator line."""
    sep = ctk.CTkFrame(parent, height=1, fg_color=color)
    if width:
        sep.pack(fill="x", padx=0)
    else:
        sep.pack(fill="x", padx=0)
    return sep


def draw_glow_rect(canvas, x0, y0, x1, y1, radius=8, color=RED, layers=2):
    """Clean rounded rect outline — no glow, just clean border."""
    canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=1, radius=radius)


# ============================================================
# WIDGET: GlassCard → ProCard
# ============================================================

class ProCard(ctk.CTkFrame):
    """Clean card with subtle border — replaces GlassCard."""

    def __init__(self, master, fg_color=SURFACE, border_color=BORDER, corner_radius=8, **kwargs):
        super().__init__(master, fg_color=fg_color, border_width=1, border_color=border_color,
                         corner_radius=corner_radius, **kwargs)

        # Top accent line (optional, thin)
        self._accent_line = ctk.CTkFrame(self, height=2, fg_color=RED, corner_radius=0)
        self._accent_line.pack(fill="x", side="top")


# ============================================================
# WIDGET: GlowDot → StatusDot
# ============================================================

class StatusDot(ctk.CTkFrame):
    """Small status indicator dot (static, no pulse animation)."""

    def __init__(self, master, color=GREEN, size=10, **kwargs):
        super().__init__(master, fg_color="transparent", width=size, height=size, **kwargs)
        self.pack_propagate(False)

        self._canvas = tk.Canvas(self, width=size, height=size, bg=BG, highlightthickness=0)
        self._canvas.pack()

        mid = size / 2
        self._canvas.create_oval(mid - 3, mid - 3, mid + 3, mid + 3, fill=color, outline="")

    def set_color(self, color):
        self._canvas.delete("all")
        mid = self._winfo_reqwidth() / 2
        self._canvas.create_oval(mid - 3, mid - 3, mid + 3, mid + 3, fill=color, outline="")


# ============================================================
# WIDGET: NeonMeter → ProMeter
# ============================================================

class ProMeter(ctk.CTkFrame):
    """Clean progress meter — replaces NeonMeter."""

    def __init__(self, master, fg_color=RED, height=4, **kwargs):
        super().__init__(master, fg_color=BG, height=height, **kwargs)
        self.pack_propagate(False)
        self._fg = fg_color

        self._bar = ctk.CTkFrame(self, fg_color=fg_color, height=height, corner_radius=2)
        self._bar.place(relx=0, rely=0, relwidth=0, relheight=1.0)

    def set(self, value):
        self._bar.place_configure(relwidth=max(0.0, min(1.0, float(value))))

    # Backward compat
    def _draw(self, **kwargs):
        pass


# ============================================================
# BACKWARD COMPAT ALIASES
# ============================================================
GlowDot = StatusDot
NeonMeter = ProMeter
GlassCard = ProCard
