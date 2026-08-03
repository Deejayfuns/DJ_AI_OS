import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    BACKGROUND,
    CARD,
    MUTED,
    NEON_BLUE,
    NEON_MAGENTA,
    NEON_PURPLE,
    NEON_PURPLE_DARK,
    PANEL,
    TEXT,
)


class NeonBoothPanel(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(
            master,
            fg_color=PANEL,
            corner_radius=8,
            border_width=1,
            border_color=NEON_PURPLE_DARK
        )

        self.phase = 0
        self.track = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            header,
            text="NEON DJ BOOTH",
            font=("Segoe UI", 16, "bold"),
            text_color=NEON_MAGENTA
        ).pack(side="left")

        self.now_label = ctk.CTkLabel(
            header,
            text="NO TRACK LOADED",
            font=("Segoe UI", 11, "bold"),
            text_color=MUTED
        )
        self.now_label.pack(side="right")

        self.canvas = tk.Canvas(
            self,
            height=170,
            bg=BACKGROUND,
            highlightthickness=0
        )
        self.canvas.pack(fill="x", padx=10, pady=10)

        self.after(90, self.animate)

    def update_track(self, track):

        self.track = dict(track or {})
        name = self.track.get("name", "NO TRACK LOADED")

        if len(name) > 54:
            name = name[:51] + "..."

        self.now_label.configure(text=name)

    def animate(self):

        if not self.winfo_exists():
            return

        self.phase = (self.phase + 1) % 360
        self.draw()
        self.after(90, self.animate)

    def draw(self):

        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = 170

        self.draw_grid(width, height)
        self.draw_deck(width, height, "DECK A", 24, self.track)
        self.draw_deck(width, height, "DECK B", width - 224, {})
        self.draw_spectrum(width, height)
        self.draw_center_meter(width, height)

    def draw_grid(self, width, height):

        for x in range(0, width, 34):
            self.canvas.create_line(x, 0, x, height, fill="#111536")

        for y in range(0, height, 24):
            self.canvas.create_line(0, y, width, y, fill="#10132D")

        self.canvas.create_rectangle(
            1,
            1,
            width - 2,
            height - 2,
            outline=NEON_PURPLE_DARK,
            width=2
        )

    def draw_deck(self, width, height, label, x, track):

        y = 24
        deck_w = 200
        deck_h = 118
        energy = self.number(track.get("energy"), 0.38 if label == "DECK B" else 0.55)
        bpm = track.get("bpm") or "--"
        key = track.get("camelot") or track.get("key") or "--"

        self.canvas.create_rectangle(
            x,
            y,
            x + deck_w,
            y + deck_h,
            fill=CARD,
            outline=NEON_PURPLE,
            width=1
        )
        self.canvas.create_text(
            x + 14,
            y + 16,
            text=label,
            fill=NEON_BLUE,
            anchor="w",
            font=("Segoe UI", 10, "bold")
        )
        self.canvas.create_text(
            x + 14,
            y + 42,
            text=f"{bpm} BPM",
            fill=TEXT,
            anchor="w",
            font=("Segoe UI", 20, "bold")
        )
        self.canvas.create_text(
            x + 14,
            y + 70,
            text=f"KEY {key}",
            fill=MUTED,
            anchor="w",
            font=("Segoe UI", 10, "bold")
        )

        for index in range(12):
            bar_h = int((energy * 52) * (0.45 + ((index % 4) / 5)))
            bx = x + 20 + index * 12
            by = y + deck_h - 16
            color = ACCENT if index < 8 else NEON_MAGENTA
            self.canvas.create_rectangle(
                bx,
                by - bar_h,
                bx + 7,
                by,
                fill=color,
                outline=""
            )

    def draw_spectrum(self, width, height):

        center_x = width / 2
        base_y = height - 26
        bars = 28
        max_w = max(220, width - 520)
        start_x = center_x - max_w / 2

        for index in range(bars):
            phase = math.radians(self.phase * 3 + index * 18)
            value = 0.45 + (math.sin(phase) + 1) * 0.27
            bar_h = int(value * 82)
            x = start_x + index * (max_w / bars)
            color = ACCENT if index % 3 else NEON_PURPLE
            self.canvas.create_rectangle(
                x,
                base_y - bar_h,
                x + 6,
                base_y,
                fill=color,
                outline=""
            )

        self.canvas.create_text(
            center_x,
            22,
            text="LIVE SPECTRUM / MIX MASTER RADAR",
            fill=NEON_BLUE,
            font=("Segoe UI", 10, "bold")
        )

    def draw_center_meter(self, width, height):

        center_x = width / 2
        center_y = 86
        radius = 42 + math.sin(math.radians(self.phase * 2)) * 3

        self.canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline=NEON_MAGENTA,
            width=2
        )
        self.canvas.create_oval(
            center_x - 26,
            center_y - 26,
            center_x + 26,
            center_y + 26,
            outline=ACCENT,
            width=2
        )
        self.canvas.create_text(
            center_x,
            center_y - 5,
            text="AI",
            fill=TEXT,
            font=("Segoe UI", 16, "bold")
        )
        self.canvas.create_text(
            center_x,
            center_y + 15,
            text="MASTER",
            fill=MUTED,
            font=("Segoe UI", 8, "bold")
        )

    def number(self, value, default):

        try:
            return max(0, min(1, float(value)))
        except (TypeError, ValueError):
            return default
