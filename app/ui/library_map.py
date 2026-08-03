"""Library DNA Map — scatter plot visualization of the entire library.

Shows all tracks as colored dots in a 2D space:
- X axis: Energy (0→1)
- Y axis: Brightness (0→1)
- Color: genre family
- Size: AI Ear score (quality)

Reveals hidden patterns in the library:
- Genre clusters
- Energy/brightness sweet spots
- Undiscovered zones (gaps = opportunity)
"""

import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    BACKGROUND,
    CARD,
    F_BODY_BOLD,
    F_META,
    GLASS_BG,
    GLASS_BORDER,
    MUTED,
    NEON_BLUE,
    NEON_MAGENTA,
    NEON_PURPLE,
    TEXT,
    WARNING,
)


# Genre family colors
GENRE_COLORS = {
    "HOUSE": "#00FFA3",
    "TECHNO": "#9B5CFF",
    "TRANCE": "#22D3FF",
    "BASS": "#FF3DF2",
    "HIP HOP": "#FFB020",
    "COMMERCIAL": "#FF4D6D",
    "LATIN": "#FF6B9D",
    "WEDDING & EVENT": "#00C896",
    "CHILL": "#2979FF",
    "ROCK": "#EAF2FF",
    "UNKNOWN": "#3A4652",
}


class LibraryMap(ctk.CTkFrame):
    """Interactive scatter plot of the entire library."""

    def __init__(self, master, width=800, height=500, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._width = width
        self._height = height
        self._tracks = []
        self._hover_track = None
        self._phase = 0

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=GLASS_BG,
            highlightthickness=0,
        )
        self._canvas.pack()
        self._canvas.bind("<Motion>", self._on_hover)

        # Info label
        self._info = ctk.CTkLabel(
            self,
            text="Kutuphaneyi yukleyin — parcalar burada gozukecek",
            font=F_META,
            text_color=MUTED,
        )
        self._info.pack(anchor="w", pady=(4, 0))

        self.after(100, self._tick)

    def set_tracks(self, tracks):
        self._tracks = list(tracks or [])

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 1) % 360
        self._render()
        self.after(200, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        w = self._width
        h = self._height

        # Grid
        for i in range(10):
            x = int(i * w / 9)
            y = int(i * h / 9)
            c.create_line(x, 0, x, h, fill="#0D1520", width=1)
            c.create_line(0, y, w, y, fill="#0D1520", width=1)

        # Axis labels
        c.create_text(w / 2, h - 4, text="ENERGY ->", fill=MUTED,
                       font=("Segoe UI", 8), anchor="s")
        c.create_text(8, h / 2, text="BRIGHTNESS ->", fill=MUTED,
                       font=("Segoe UI", 8), anchor="w", angle=90)

        if not self._tracks:
            c.create_text(w / 2, h / 2,
                           text="Kutuphanede parca yok",
                           fill=MUTED, font=("Segoe UI", 12))
            return

        # Draw tracks as dots
        for track in self._tracks:
            energy = float(track.get("energy", 0.5) or 0.5)
            brightness = float(track.get("brightness", 0.5) or 0.5)
            ear = float(track.get("ai_ear_score", 0.5) or 0.5)
            genre = track.get("parent_genre", track.get("genre", "UNKNOWN"))

            x = int(energy * (w - 40)) + 20
            y = int((1 - brightness) * (h - 40)) + 20

            color = GENRE_COLORS.get(genre, GENRE_COLORS["UNKNOWN"])
            radius = max(2, int(ear * 5))

            c.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=color,
                outline="",
                stipple="gray25" if ear < 0.5 else "",
            )

        # Legend (top right)
        legend_x = w - 140
        legend_y = 15
        c.create_rectangle(legend_x - 5, legend_y - 5, w - 5, legend_y + len(GENRE_COLORS) * 14 + 5,
                           fill=GLASS_BG, outline=GLASS_BORDER)

        for i, (genre, color) in enumerate(GENRE_COLORS.items()):
            if genre == "UNKNOWN":
                continue
            ly = legend_y + i * 14
            c.create_oval(legend_x, ly, legend_x + 8, ly + 8, fill=color, outline="")
            c.create_text(legend_x + 12, ly + 4, text=genre, fill=TEXT,
                           font=("Segoe UI", 7), anchor="w")

        # Stats
        genre_counts = {}
        for t in self._tracks:
            g = t.get("parent_genre", t.get("genre", "UNKNOWN"))
            genre_counts[g] = genre_counts.get(g, 0) + 1

        self._info.configure(
            text=f"{len(self._tracks)} parca | {len(genre_counts)} tur | "
                 f"Enerji dagilimi: {self._energy_distribution()}"
        )

    def _energy_distribution(self):
        if not self._tracks:
            return "bos"

        zones = {"dusuk": 0, "orta": 0, "yuksek": 0}
        for t in self._tracks:
            e = float(t.get("energy", 0.5) or 0.5)
            if e > 0.7:
                zones["yuksek"] += 1
            elif e > 0.4:
                zones["orta"] += 1
            else:
                zones["dusuk"] += 1

        total = len(self._tracks)
        return (
            f"dusuk={zones['dusuk']*100//total}% "
            f"orta={zones['orta']*100//total}% "
            f"yuksek={zones['yuksek']*100//total}%"
        )

    def _on_hover(self, event):
        """Show track info on hover."""
        w = self._width
        h = self._height

        # Find nearest track
        best_dist = float("inf")
        best_track = None

        for track in self._tracks:
            energy = float(track.get("energy", 0.5) or 0.5)
            brightness = float(track.get("brightness", 0.5) or 0.5)

            x = int(energy * (w - 40)) + 20
            y = int((1 - brightness) * (h - 40)) + 20

            dist = math.sqrt((event.x - x) ** 2 + (event.y - y) ** 2)
            if dist < best_dist and dist < 15:
                best_dist = dist
                best_track = track

        if best_track:
            name = best_track.get("name", "?")[:40]
            bpm = best_track.get("bpm", "?")
            genre = best_track.get("genre", "?")
            self._info.configure(
                text=f"{name} | {bpm} BPM | {genre}"
            )
        else:
            self._info.configure(text=self._energy_distribution())
