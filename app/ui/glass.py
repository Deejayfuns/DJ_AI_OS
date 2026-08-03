"""Reusable neon-glass UI primitives for DJ AI OS.

Draws on top of customtkinter / tkinter canvas.  All helpers are pure — they
do not hold state, so they can be called from any ``after()`` animation loop.

Usage examples:

    from app.ui.glass import draw_glow_rect, GlassCard, GlowDot

    # canvas glow
    draw_glow_rect(canvas, 10, 10, 200, 80, radius=10, color="#00FFA3")

    # glass frame widget
    card = GlassCard(parent)
    card.pack(fill="x", padx=12, pady=8)
"""

import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    BACKGROUND,
    GLASS_BG,
    GLASS_BORDER,
    GLASS_HIGHLIGHT,
    GLASS_BG_HOVER,
    GLOW_ACCENT,
    GLOW_BLUE,
    GLOW_MAGENTA,
    GLOW_PURPLE,
    MUTED,
    NEON_BLUE,
    NEON_PURPLE,
    NEON_PURPLE_DARK,
    PANEL,
    SP1,
    SP3,
    R_MED,
    TEXT,
)


def safe_alpha(hex_color, alpha_pct):
    """Convert hex color + alpha to a valid tkinter hex color (no alpha channel)."""
    try:
        r1, g1, b1 = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        r2, g2, b2 = int(BACKGROUND[1:3], 16), int(BACKGROUND[3:5], 16), int(BACKGROUND[5:7], 16)
        a = max(0, min(1, alpha_pct))
        r = int(r1 * a + r2 * (1 - a))
        g = int(g1 * a + g2 * (1 - a))
        b = int(b1 * a + b2 * (1 - a))
        return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        return hex_color


# ============================================================
# Canvas glow / gradient drawing helpers
# ============================================================

def draw_glow_rect(
    canvas,
    x0, y0, x1, y1,
    radius=12,
    color=GLOW_ACCENT,
    layers=5,
    width_expand=3,
):
    """Draw an outer glow halo around a rounded rectangle.

    Each *layer* expands outward by *width_expand* pixels with decreasing
    opacity (simulated via increasingly dark version of *color*).
    """
    r, g, b = _hex_to_rgb(color)
    alpha = int(color[7:9], 16) if len(color) == 9 else 48  # default alpha

    for i in range(layers, 0, -1):
        expand = i * width_expand
        fade = max(10, alpha - i * 7)
        fill = f"#{r:02x}{g:02x}{b:02x}{fade:02x}"
        canvas.create_rectangle(
            x0 - expand,
            y0 - expand,
            x1 + expand,
            y1 + expand,
            outline=fill,
            width=1,
        )


def draw_gradient(canvas, x0, y0, x1, y1, top_color, bottom_color, steps=24):
    """Fill a rectangular region with a vertical linear gradient."""
    r1, g1, b1 = _hex_to_rgb(top_color)
    r2, g2, b2 = _hex_to_rgb(bottom_color)
    height = max(1, y1 - y0)
    step = max(1, height // steps)

    for i in range(steps):
        t = i / max(1, steps - 1)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        sy = y0 + i * step
        ey = min(y0 + (i + 1) * step, y1)
        canvas.create_rectangle(x0, sy, x1, ey, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")


def draw_glow_line(canvas, x0, y, x1, color=NEON_PURPLE, width=1, glow_expand=4):
    """Draw a horizontal line with a soft vertical glow."""
    r, g, b = _hex_to_rgb(color)
    for dy in range(-glow_expand, glow_expand + 1):
        alpha = max(12, 48 - abs(dy) * 8)
        canvas.create_line(x0, y + dy, x1, y + dy, fill=f"#{r:02x}{g:02x}{b:02x}{alpha:02x}", width=1)
    canvas.create_line(x0, y, x1, y, fill=color, width=width)


def _hex_to_rgb(hex_color):
    """Parse ``#RRGGBB`` to ``(r, g, b)``."""
    h = hex_color.lstrip("#")[:6]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ============================================================
# Widget: GlassCard
# ============================================================

class GlassCard(ctk.CTkFrame):
    """A frame with glass surface, subtle gradient and accent border."""

    def __init__(
        self,
        master,
        fg_color=GLASS_BG,
        border_color=GLASS_BORDER,
        corner_radius=R_MED,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=fg_color,
            border_width=1,
            border_color=border_color,
            corner_radius=corner_radius,
            **kwargs,
        )

        # top highlight strip (bright line at very top)
        self._highlight = ctk.CTkFrame(
            self,
            height=2,
            fg_color=GLASS_HIGHLIGHT,
            corner_radius=0,
        )
        self._highlight.pack(fill="x", side="top")


# ============================================================
# Widget: GlowDot — pulsing status indicator
# ============================================================

class GlowDot(ctk.CTkFrame):
    """Small circular pulsing status dot using a canvas."""

    def __init__(self, master, color=ACCENT, size=14, **kwargs):
        super().__init__(master, fg_color="transparent", width=size, height=size, **kwargs)
        self.pack_propagate(False)

        self._color = color
        self._size = size
        self._phase = 0

        self._canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            bg="transparent",
            highlightthickness=0,
        )
        self._canvas.pack()
        self.after(100, self._tick)

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 3) % 360
        self._draw()
        self.after(80, self._tick)

    def _draw(self):
        c = self._canvas
        c.delete("all")
        s = self._size
        mid = s / 2
        pulse = 1.0 + 0.22 * math.sin(math.radians(self._phase))

        # outer glow
        r = mid * pulse
        c.create_oval(mid - r - 2, mid - r - 2, mid + r + 2, mid + r + 2,
                       outline=safe_alpha(self._color, 0.25), width=1)
        # solid core
        c.create_oval(mid - 3, mid - 3, mid + 3, mid + 3,
                       fill=self._color, outline="")


# ============================================================
# Widget: NeonMeter — animated glow progress bar
# ============================================================

class NeonMeter(ctk.CTkFrame):
    """A thin animated progress bar with glow."""

    def __init__(self, master, fg_color=ACCENT, height=6, **kwargs):
        super().__init__(master, fg_color="transparent", height=height, **kwargs)
        self.pack_propagate(False)
        self._fg = fg_color
        self._value = 0.0
        self._phase = 0

        self._canvas = tk.Canvas(
            self,
            height=height,
            bg=PANEL,
            highlightthickness=0,
        )
        self._canvas.pack(fill="both", expand=True)
        self.after(90, self._tick)

    def set(self, value):
        self._value = max(0.0, min(1.0, float(value)))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 2) % 360
        self._draw()
        self.after(80, self._tick)

    def _draw(self):
        c = self._canvas
        c.delete("all")
        w = max(1, c.winfo_width())
        h = self._height() or 6
        bar_w = max(0, int(w * self._value))

        if bar_w > 0:
            # main bar
            c.create_rectangle(0, 0, bar_w, h, fill=self._fg, outline="")
            # glow at tip
            pulse = 1.5 + 0.5 * math.sin(math.radians(self._phase))
            c.create_oval(
                bar_w - 4, -pulse,
                bar_w + 4, h + pulse,
                fill=self._fg + "50",
                outline="",
            )

    def _height(self):
        try:
            return self.winfo_height()
        except Exception:
            return 6
