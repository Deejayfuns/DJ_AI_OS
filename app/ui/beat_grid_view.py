"""Beat Grid Overlay — enhanced waveform with beat markers.

Draws beat grid lines, phrase markers, and hot cues on top of
the existing waveform visualization. Gives the DJ a precise
visual guide during live performance.
"""

import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    F_BODY,
    F_META,
    GLASS_BG,
    MUTED,
    NEON_BLUE,
    NEON_MAGENTA,
    TEXT,
    WARNING,
)


class BeatGridView(ctk.CTkFrame):
    """Enhanced waveform with beat grid, phrase markers, and hot cues."""

    def __init__(self, master, width=800, height=200, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._width = width
        self._height = height
        self._phase = 0
        self._waveform = []
        self._phrase_points = []
        self._hot_cues = []
        self._bpm = 0
        self._duration = 0
        self._playhead = 0.0  # 0-1 position

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=GLASS_BG,
            highlightthickness=0,
        )
        self._canvas.pack()

        # Info bar
        self._info_bar = ctk.CTkFrame(self, fg_color="transparent")
        self._info_bar.pack(fill="x", pady=(4, 0))

        self._bpm_label = ctk.CTkLabel(self._info_bar, text="BPM: --",
                                        font=F_BODY, text_color=ACCENT)
        self._bpm_label.pack(side="left", padx=8)

        self._key_label = ctk.CTkLabel(self._info_bar, text="KEY: --",
                                        font=F_BODY, text_color=NEON_BLUE)
        self._key_label.pack(side="left", padx=8)

        self._time_label = ctk.CTkLabel(self._info_bar, text="00:00 / 00:00",
                                         font=F_META, text_color=MUTED)
        self._time_label.pack(side="right", padx=8)

        self.after(60, self._tick)

    def set_track(self, track):
        """Load track data for visualization."""
        self._waveform = track.get("waveform", [])
        self._phrase_points = track.get("phrase_points", [])
        self._hot_cues = track.get("hot_cues", [])
        self._bpm = float(track.get("bpm", 0) or 0)
        self._duration = float(track.get("duration", 0) or 0)

        self._bpm_label.configure(text=f"BPM: {self._bpm:.0f}" if self._bpm else "BPM: --")
        self._key_label.configure(
            text=f"KEY: {track.get('camelot', track.get('key', '--'))}"
        )

    def set_playhead(self, position):
        """Set playhead position (0-1)."""
        self._playhead = max(0, min(1, float(position)))

    def _tick(self):
        if not self.winfo_exists():
            return
        self._phase = (self._phase + 1) % 360
        self._render()
        self.after(50, self._tick)

    def _render(self):
        c = self._canvas
        c.delete("all")
        w = self._width
        h = self._height
        center_y = h / 2

        # Background grid
        for x in range(0, w, 4):
            color = "#0D1520" if x % 20 == 0 else "#0A0F18"
            c.create_line(x, 0, x, h, fill=color, width=1)

        # Beat grid lines
        if self._bpm > 0 and self._duration > 0:
            beat_duration = 60.0 / self._bpm
            total_beats = self._duration / beat_duration

            for beat in range(int(total_beats) + 1):
                beat_pos = (beat * beat_duration) / self._duration
                x = int(beat_pos * w)

                if x < 0 or x > w:
                    continue

                is_bar = beat % 4 == 0
                is_phrase = beat % 16 == 0

                if is_phrase:
                    color = "#9B5CFF"
                    width = 2
                elif is_bar:
                    color = "#253058"
                    width = 1
                else:
                    color = "#0D1520"
                    width = 1

                c.create_line(x, 0, x, h, fill=color, width=width)

                # Beat number at bars
                if is_bar and beat % 8 == 0:
                    c.create_text(x + 3, 8, text=str(beat // 4 + 1),
                                   fill=MUTED, font=("Segoe UI", 7), anchor="w")

        # Center line
        c.create_line(0, center_y, w, center_y, fill="#253058", width=1)

        # Waveform
        if self._waveform:
            bars = self._resample(self._waveform, w)

            for x, val in enumerate(bars):
                amplitude = abs(val) * (center_y - 10)
                color = self._wave_color(val)

                c.create_line(x, center_y - amplitude, x, center_y + amplitude,
                               fill=color, width=1 if abs(val) < 0.6 else 2)

        # Phrase regions
        phrase_colors = {
            "START": "#2ECC71",
            "BUILD": "#F5A623",
            "PEAK": "#E63946",
            "OUTRO": "#457B9D",
        }

        ordered = sorted(self._phrase_points,
                         key=lambda p: float(p.get("position", 0) or 0))

        for i, point in enumerate(ordered):
            pos = float(point.get("position", 0) or 0)
            x = int(pos * w)
            end_pos = float(ordered[i + 1].get("position", 1) or 1) if i + 1 < len(ordered) else 1
            end_x = int(end_pos * w)

            color = phrase_colors.get(point.get("label", ""), "")
            if color:
                c.create_rectangle(x, 0, end_x, h, fill=color, outline="")

            # Phrase marker
            label = point.get("label", "")
            marker_colors = {
                "START": ACCENT,
                "BUILD": WARNING,
                "PEAK": NEON_MAGENTA,
                "OUTRO": NEON_BLUE,
            }
            mc = marker_colors.get(label, TEXT)

            c.create_line(x, 0, x, h, fill=mc, width=2, dash=(4, 4))
            c.create_text(x + 4, h - 14, text=label, fill=mc,
                           font=("Segoe UI", 8, "bold"), anchor="w")

        # Hot cues
        for cue in self._hot_cues:
            pos = float(cue.get("position", 0) or 0)
            x = int(pos * w)
            label = cue.get("label", "CUE")
            color = cue.get("color", "CYAN")
            cue_colors = {
                "GREEN": "#00FFA3", "YELLOW": "#FFB020",
                "MAGENTA": "#FF3DF2", "BLUE": "#22D3FF", "CYAN": "#00C896",
            }
            cc = cue_colors.get(color, ACCENT)

            c.create_line(x, 0, x, h, fill=cc, width=2)
            # Triangle marker
            c.create_polygon(x - 5, 2, x + 5, 2, x, 12, fill=cc, outline="")
            c.create_text(x, h - 4, text=label, fill=cc,
                           font=("Segoe UI", 7, "bold"), anchor="s")

        # Playhead
        ph_x = int(self._playhead * w)
        pulse = 2 + math.sin(math.radians(self._phase * 3)) * 1
        c.create_line(ph_x, 0, ph_x, h, fill="#FFFFFF", width=2)
        c.create_oval(ph_x - pulse, 0, ph_x + pulse, 4, fill="#FFFFFF", outline="")

        # Time display
        current_sec = self._playhead * self._duration
        total_min = int(self._duration // 60)
        total_sec = int(self._duration % 60)
        cur_min = int(current_sec // 60)
        cur_sec = int(current_sec % 60)
        self._time_label.configure(
            text=f"{cur_min:02d}:{cur_sec:02d} / {total_min:02d}:{total_sec:02d}"
        )

    def _resample(self, waveform, target_width):
        """Resample waveform to target width."""
        if not waveform or target_width <= 0:
            return []

        count = len(waveform)
        result = []
        for x in range(target_width):
            idx = int((x / target_width) * count)
            idx = min(idx, count - 1)
            result.append(float(waveform[idx] or 0))
        return result

    def _wave_color(self, value):
        """Color based on waveform amplitude."""
        val = abs(value)
        if val > 0.84:
            return "#EAF2FF"
        if val > 0.62:
            return NEON_BLUE
        if value < 0:
            return "#2D6BFF"
        return "#00B7FF"
