"""
ORB Neon — Cyberpunk UI Widgets
===============================
CustomTkinter-compatible neon widgets with glow effects.
"""
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from .theme import Theme, Glow


class NeonButton(tk.Canvas):
    """TRON-style glowing button."""

    def __init__(self, master, text: str, command: Callable = None,
                 theme: Theme = None, width: int = 120, height: int = 36,
                 accent: str = "accent", font: tuple = None, **kwargs):
        self.theme = theme or Theme()
        self.accent = accent
        self.command = command
        self._hover = False
        self._pressed = False

        super().__init__(master, width=width, height=height,
                        bg=self.theme.c("bg_panel"),
                        highlightthickness=0, bd=0, **kwargs)

        self.text = text
        self._draw()

        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self):
        """Draw button."""
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = 120
        if h <= 1:
            h = 36

        color = self.theme.c(self.accent)
        if self._hover:
            color = Glow.pulse(color, 1.3)
        if self._pressed:
            color = Glow.pulse(color, 0.6)

        # Border glow (outer)
        self.create_rectangle(2, 2, w - 2, h - 2, outline=color, width=1,
                             dash=(4, 3))
        # Inner fill
        self.create_rectangle(4, 4, w - 4, h - 4, fill=self.theme.c("bg_panel"),
                             outline=color, width=1)

        # Text
        self.create_text(w // 2, h // 2, text=self.text,
                        fill=color, font=self.theme_style)

    @property
    def theme_style(self):
        return ("Consolas", 11, "bold")

    def _on_enter(self, e):
        self._hover = True
        self._draw()

    def _on_leave(self, e):
        self._hover = False
        self._pressed = False
        self._draw()

    def _on_press(self, e):
        self._pressed = True
        self._draw()

    def _on_release(self, e):
        self._pressed = False
        self._draw()
        if self.command:
            self.command()

    def set_text(self, text: str):
        self.text = text
        self._draw()


class NeonSlider(tk.Canvas):
    """TRON-style glowing slider."""

    def __init__(self, master, from_: float = 0.0, to: float = 1.0,
                 command: Callable = None, theme: Theme = None,
                 width: int = 200, height: int = 40, orientation: str = "horizontal",
                 accent: str = "accent", **kwargs):
        self.theme = theme or Theme()
        self.accent = accent
        self.command = command
        self.orientation = orientation
        self._value = 0.5
        self._min = from_
        self._max = to
        self._dragging = False

        super().__init__(master, width=width, height=height,
                        bg=self.theme.c("bg_panel"),
                        highlightthickness=0, bd=0, **kwargs)

        self._draw()

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self):
        """Draw slider."""
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = 200
        if h <= 1:
            h = 40

        color = self.theme.c(self.accent)
        track_color = self.theme.c("border")

        if self.orientation == "horizontal":
            # Track
            self.create_line(10, h // 2, w - 10, h // 2, fill=track_color, width=2)
            # Fill
            fill_end = 10 + int((w - 20) * self._value)
            self.create_line(10, h // 2, fill_end, h // 2, fill=color, width=2)
            # Knob
            knob_x = fill_end
            self.create_oval(knob_x - 6, h // 2 - 6, knob_x + 6, h // 2 + 6,
                            fill=color, outline=self.theme.c("bg_dark"), width=2)
        else:
            # Vertical
            self.create_line(w // 2, 10, w // 2, h - 10, fill=track_color, width=2)
            fill_end = h - 10 - int((h - 20) * self._value)
            self.create_line(w // 2, h - 10, w // 2, fill_end, fill=color, width=2)
            knob_y = fill_end
            self.create_oval(w // 2 - 6, knob_y - 6, w // 2 + 6, knob_y + 6,
                            fill=color, outline=self.theme.c("bg_dark"), width=2)

    def _pos_to_value(self, x, y):
        w = self.winfo_width()
        h = self.winfo_height()
        if self.orientation == "horizontal":
            rel = (x - 10) / max(1, w - 20)
        else:
            rel = 1.0 - (y - 10) / max(1, h - 20)
        rel = max(0.0, min(1.0, rel))
        return self._min + rel * (self._max - self._min)

    def _on_press(self, e):
        self._dragging = True
        self._value = self._pos_to_value(e.x, e.y)
        self._draw()
        if self.command:
            self.command(self._value)

    def _on_drag(self, e):
        if self._dragging:
            self._value = self._pos_to_value(e.x, e.y)
            self._draw()
            if self.command:
                self.command(self._value)

    def _on_release(self, e):
        self._dragging = False

    def get(self) -> float:
        return self._value

    def set(self, value: float):
        self._value = max(self._min, min(self._max, value))
        self._draw()


class NeonProgressBar(tk.Canvas):
    """TRON-style glowing progress bar."""

    def __init__(self, master, value: float = 0.0, theme: Theme = None,
                 width: int = 200, height: int = 8, accent: str = "success", **kwargs):
        self.theme = theme or Theme()
        self.accent = accent
        self._value = value

        super().__init__(master, width=width, height=height,
                        bg=self.theme.c("bg_panel"),
                        highlightthickness=0, bd=0, **kwargs)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = 200
        if h <= 1:
            h = 8

        color = self.theme.c(self.accent)
        # Track
        self.create_rectangle(0, 0, w, h, fill=self.theme.c("bg_dark"),
                             outline=self.theme.c("border"), width=1)
        # Fill
        fill_w = int(w * max(0.0, min(1.0, self._value)))
        if fill_w > 0:
            self.create_rectangle(1, 1, fill_w, h - 1, fill=color, outline="")

    def set(self, value: float):
        self._value = value
        self._draw()


class NeonFrame(tk.Frame):
    """TRON-style bordered panel."""

    def __init__(self, master, theme: Theme = None, border_color: str = None,
                 title: str = None, **kwargs):
        self.theme = theme or Theme()
        self.border_color = border_color or self.theme.c("border")
        self.title = title

        super().__init__(master, bg=self.theme.c("bg_panel"), **kwargs)

        self._build()

    def _build(self):
        # Title
        if self.title:
            label = tk.Label(self, text=f"◢ {self.title.upper()} ◣",
                            bg=self.theme.c("bg_panel"),
                            fg=self.theme.c("accent"),
                            font=("Consolas", 10, "bold"))
            label.pack(anchor="w", padx=8, pady=(6, 2))

        # Content area
        self.content = tk.Frame(self, bg=self.theme.c("bg_panel"))
        self.content.pack(fill="both", expand=True, padx=6, pady=6)

    def style_frame(self, frame):
        """Apply neon border to a standard frame."""
        frame.configure(bg=self.theme.c("bg_panel"), highlightthickness=1,
                        highlightbackground=self.border_color)
        return frame


def apply_ttk_theme(root, theme: Theme):
    """Apply neon theme to ttk widgets."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TFrame", background=theme.c("bg_panel"))
    style.configure("TLabel", background=theme.c("bg_panel"),
                   foreground=theme.c("fg"),
                   font=("Consolas", 10))
    style.configure("Neon.TLabel", background=theme.c("bg_panel"),
                   foreground=theme.c("accent"),
                   font=("Consolas", 11, "bold"))
    style.configure("Title.TLabel", background=theme.c("bg_panel"),
                   foreground=theme.c("fg_bright"),
                   font=("Consolas", 16, "bold"))
    style.configure("Accent.TButton",
                   background=theme.c("accent"),
                   foreground=theme.c("bg_dark"),
                   borderwidth=1,
                   font=("Consolas", 10, "bold"))
    style.map("Accent.TButton",
             background=[("pressed", theme.c("accent2")),
                        ("active", theme.c("glow_cyan"))])
    style.configure("TButton",
                   background=theme.c("bg_panel_alt"),
                   foreground=theme.c("fg"),
                   borderwidth=1,
                   font=("Consolas", 10))
    style.map("TButton",
             background=[("pressed", theme.c("accent")),
                        ("active", theme.c("bg_panel"))])
    style.configure("TEntry", fieldbackground=theme.c("bg_dark"),
                   foreground=theme.c("fg"),
                   insertcolor=theme.c("accent"),
                   bordercolor=theme.c("border"))
    style.configure("Neon.Horizontal.TProgressbar",
                   background=theme.c("accent"),
                   troughcolor=theme.c("bg_dark"),
                   bordercolor=theme.c("border"))
    style.configure("Neon.Vertical.TScale",
                   background=theme.c("accent"),
                   troughcolor=theme.c("bg_dark"))
    return style