import customtkinter as ctk
import tkinter as tk

from app.ui.theme import ACCENT, BACKGROUND, GLASS_BG, MUTED, NEON_BLUE, NEON_MAGENTA, NEON_PURPLE_DARK, PANEL, TEXT, WARNING

try:
    import windnd
except Exception:
    windnd = None


class WaveformView(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(
            fg_color=PANEL,
            corner_radius=8,
            border_width=1,
            border_color=NEON_PURPLE_DARK
        )

        self.canvas = tk.Canvas(
            self,
            bg=GLASS_BG,
            height=250,
            highlightthickness=0
        )

        self.canvas.pack(fill="both", expand=True)

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
        h = max(self.canvas.winfo_height(), 250)
        detail_h = int(h * 0.72)
        overview_top = detail_h + 18
        overview_h = h - overview_top - 14
        center = detail_h / 2

        self.draw_deck_grid(w, detail_h, bpm, duration)

        phrase_points = phrase_points or []
        self.draw_phrase_regions(phrase_points, w, detail_h)

        self.canvas.create_line(
            0,
            center,
            w,
            center,
            fill=NEON_PURPLE_DARK
        )

        if not waveform:
            self.canvas.create_text(
                w / 2,
                center,
                text="NO WAVEFORM - WAV ANALIZ VEYA DOSYA SURUKLE",
                fill=MUTED,
                font=("Segoe UI", 10, "bold")
            )
            return

        bars = self.resample_waveform(waveform, w)

        for x, raw in enumerate(bars):
            val = abs(raw)
            y = min((detail_h / 2) - 10, val * ((detail_h / 2) - 12))
            color = self.wave_color(val, raw)
            width = 2 if val > 0.62 else 1

            self.canvas.create_line(
                x,
                center - y,
                x,
                center + y,
                fill=color,
                width=width
            )

            if val > 0.82:
                self.canvas.create_line(
                    x,
                    center - y - 2,
                    x,
                    center + y + 2,
                    fill="#EAF2FF"
                )

        self.canvas.create_text(
            10,
            12,
            text=self.waveform_title(bpm, duration),
            fill=NEON_BLUE,
            anchor="w",
            font=("Segoe UI", 9, "bold")
        )

        self.draw_phrase_points(phrase_points, w, detail_h)
        self.draw_overview(bars, w, overview_top, overview_h, phrase_points)

    def waveform_title(self, bpm, duration):

        bpm_text = f"{float(bpm):.1f} BPM" if self.number(bpm, 0) else "BPM --"
        duration_text = self.format_time(duration)

        return f"DETAILED WAVEFORM | {bpm_text} | {duration_text}"

    def draw_deck_grid(self, width, height, bpm, duration):

        for x in range(0, width, 24):
            color = "#101329" if (x // 24) % 2 else "#15183A"
            self.canvas.create_line(x, 0, x, height, fill=color)

        bar_positions = self.bar_positions(width, bpm, duration)

        if bar_positions:
            for index, x in enumerate(bar_positions):
                is_phrase = index % 8 == 0
                color = NEON_PURPLE_DARK if index % 4 == 0 else "#26304D"
                width_px = 2 if is_phrase else 1

                self.canvas.create_line(x, 0, x, height, fill=color, width=width_px)

                if is_phrase:
                    self.canvas.create_text(
                        x + 3,
                        28,
                        text=str(index + 1),
                        fill=MUTED,
                        anchor="w",
                        font=("Segoe UI", 7, "bold")
                    )

        self.canvas.create_rectangle(
            1,
            1,
            width - 2,
            height - 2,
            outline=NEON_PURPLE_DARK,
            width=1
        )

    def bar_positions(self, width, bpm, duration):

        bpm = self.number(bpm, 0)
        duration = self.number(duration, 0)

        if bpm <= 0 or duration <= 0:
            return []

        bar_seconds = (60 / bpm) * 4

        if bar_seconds <= 0:
            return []

        total_bars = int(duration / bar_seconds) + 1

        return [
            max(0, min(width - 1, int((bar * bar_seconds / duration) * width)))
            for bar in range(total_bars)
        ]

    def resample_waveform(self, waveform, width):

        if not waveform or width <= 1:
            return []

        count = len(waveform)
        bars = []

        for x in range(width):
            start = int((x / width) * count)
            end = int(((x + 1) / width) * count)
            end = max(start + 1, min(end, count))
            chunk = waveform[start:end]

            if not chunk:
                bars.append(0)
                continue

            strongest = max(chunk, key=lambda value: abs(float(value or 0)))
            bars.append(float(strongest or 0))

        return bars

    def wave_color(self, value, raw):

        if value > 0.84:
            return "#EAF2FF"

        if value > 0.62:
            return NEON_BLUE

        if raw < 0:
            return "#2D6BFF"

        return "#00B7FF"

    def draw_overview(self, bars, width, top, height, phrase_points):

        self.canvas.create_rectangle(
            0,
            top,
            width,
            top + height,
            fill="#05070D",
            outline=NEON_PURPLE_DARK
        )

        center = top + height / 2
        step = max(1, int(len(bars) / max(width, 1)))

        for x in range(0, min(width, len(bars)), step):
            val = abs(float(bars[x] or 0))
            y = max(1, val * (height / 2 - 3))
            self.canvas.create_line(
                x,
                center - y,
                x,
                center + y,
                fill="#0098D8"
            )

        self.draw_phrase_points(phrase_points, width, top + height)

        self.canvas.create_text(
            10,
            top + 12,
            text="OVERVIEW",
            fill=MUTED,
            anchor="w",
            font=("Segoe UI", 8, "bold")
        )

    def draw_phrase_regions(self, phrase_points, width, height):

        ordered = sorted(
            phrase_points,
            key=lambda point: float(point.get("position", 0) or 0)
        )

        colors = {
            "START": "#063527",
            "BUILD": "#34270B",
            "PEAK": "#351126",
            "OUTRO": "#0B2440",
        }

        for index, point in enumerate(ordered):
            label = point.get("label", "")
            start = float(point.get("position", 0) or 0)
            end = (
                float(ordered[index + 1].get("position", 1) or 1)
                if index + 1 < len(ordered)
                else 1
            )
            x1 = max(0, min(width, start * width))
            x2 = max(x1, min(width, end * width))
            color = colors.get(label)

            if color and x2 > x1:
                self.canvas.create_rectangle(
                    x1,
                    0,
                    x2,
                    height,
                    fill=color,
                    outline=""
                )

    def draw_phrase_points(self, phrase_points, width, height):

        colors = {
            "START": "#00FFA3",
            "BUILD": "#FFB020",
            "PEAK": NEON_MAGENTA,
            "OUTRO": NEON_BLUE,
        }

        for point in phrase_points:
            label = point.get("label", "")
            position = float(point.get("position", 0) or 0)
            x = max(0, min(width - 1, position * width))
            color = colors.get(label, "#EAF2FF")

            self.canvas.create_line(
                x,
                0,
                x,
                height,
                fill=color,
                dash=(3, 3)
            )
            self.canvas.create_polygon(
                x - 4,
                2,
                x + 4,
                2,
                x,
                10,
                fill=color,
                outline=""
            )
            self.canvas.create_text(
                x + 4,
                height - 14,
                text=label,
                fill=color,
                anchor="w",
                font=("Segoe UI", 8, "bold")
            )

    def format_time(self, duration):

        duration = int(self.number(duration, 0))

        if duration <= 0:
            return "--:--"

        return f"{duration // 60}:{duration % 60:02d}"

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
