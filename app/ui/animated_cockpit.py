import math
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    ACCENT_DARK,
    BACKGROUND,
    BORDER,
    CARD,
    GLASS_BG,
    GLASS_BORDER,
    GLOW,
    MUTED,
    NEON_BLUE,
    NEON_MAGENTA,
    NEON_PURPLE,
    NEON_PURPLE_DARK,
    PANEL,
    PURPLE_GLOW,
    TEXT,
    WARNING,
)
from app.ui.glass import draw_glow_rect, draw_glow_line


class AnimatedArchiveCockpit(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(
            master,
            fg_color=PANEL,
            corner_radius=8,
            border_width=1,
            border_color=NEON_PURPLE_DARK
        )

        self.phase = 0
        self.running = True
        self.stats = {
            "tracks": 0,
            "issues": 0,
            "locked": True,
            "mode": "IDEMPOTENT",
            "missing": 0,
            "relinked": 0,
        }

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            self.header,
            text="AI ARCHIVE COCKPIT",
            font=("Segoe UI", 18, "bold"),
            text_color=NEON_BLUE
        ).pack(side="left")

        self.mode_label = ctk.CTkLabel(
            self.header,
            text="LOCKED IDEMPOTENT MODE",
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT
        )
        self.mode_label.pack(side="right")

        self.canvas = tk.Canvas(
            self,
            height=280,
            bg=PANEL,
            highlightthickness=0
        )
        self.canvas.pack(fill="x", padx=10, pady=10)

        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(fill="x", padx=12, pady=(0, 12))

        self.track_label = self.footer_label("TRACKS 0")
        self.issue_label = self.footer_label("DOCTOR 0")
        self.lock_label = self.footer_label("ARCHIVE LOCK ON")
        self.health_label = self.footer_label("RELINK 0 / MISSING 0")

        self.after(80, self.animate)

    def footer_label(self, text):

        label = ctk.CTkLabel(
            self.footer,
            text=text,
            fg_color=CARD,
            corner_radius=6,
            height=30,
            text_color=TEXT,
            font=("Segoe UI", 11, "bold")
        )
        label.pack(side="left", fill="x", expand=True, padx=4)
        return label

    def update_stats(
        self,
        tracks=0,
        issues=0,
        locked=True,
        mode="IDEMPOTENT",
        missing=0,
        relinked=0
    ):

        self.stats = {
            "tracks": tracks,
            "issues": issues,
            "locked": locked,
            "mode": mode,
            "missing": missing,
            "relinked": relinked,
        }

        self.track_label.configure(text=f"TRACKS {tracks}")
        self.issue_label.configure(
            text=f"DOCTOR {issues}",
            text_color=WARNING if issues else TEXT
        )
        self.lock_label.configure(
            text="ARCHIVE LOCK ON" if locked else "ARCHIVE OPEN",
            text_color=ACCENT if locked else WARNING
        )
        self.mode_label.configure(text=f"{mode} MODE")
        self.health_label.configure(
            text=f"RELINK {relinked} / MISSING {missing}",
            text_color=WARNING if missing else ACCENT
        )

    def animate(self):

        if not self.winfo_exists():
            return

        self.phase = (self.phase + 1) % 360
        self.draw()
        self.after(80, self.animate)

    def draw(self):

        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 1)
        height = 280

        self.draw_background(width, height)
        self.draw_pipeline(width, height)
        self.draw_control_center(width, height)
        self.draw_health_radar(width, height)
        self.draw_lock(width, height)

    def draw_pipeline(self, width, height):

        left = 24
        right = width - 24
        bar_y = 48
        self.canvas.create_rectangle(
            left,
            bar_y - 18,
            right,
            bar_y + 18,
            fill="#0B1228",
            outline=NEON_PURPLE_DARK,
            width=2
        )

        stages = [
            (left + 60, "SCAN", "source"),
            (width * 0.32, "ANALYZE", "metadata"),
            (width * 0.58, "DIAGNOSE", "health"),
            (right - 60, "STORE", "archive"),
        ]

        for x, title, subtitle in stages:
            self.canvas.create_oval(
                x - 24,
                bar_y - 18,
                x + 24,
                bar_y + 18,
                fill="#0D1732",
                outline=NEON_BLUE,
                width=2
            )
            self.canvas.create_text(
                x,
                bar_y - 4,
                text=title,
                fill=ACCENT,
                font=("Segoe UI", 9, "bold")
            )
            self.canvas.create_text(
                x,
                bar_y + 8,
                text=subtitle,
                fill=MUTED,
                font=("Segoe UI", 7)
            )

        for index in range(len(stages) - 1):
            x1 = stages[index][0] + 24
            x2 = stages[index + 1][0] - 24
            self.canvas.create_line(
                x1,
                bar_y,
                x2,
                bar_y,
                fill=NEON_PURPLE,
                width=2,
                dash=(6, 4)
            )

    def draw_control_center(self, width, height):

        left = 28
        top = 90
        right = width - 28
        bottom = 232
        panel_width = (right - left) / 3 - 12

        tracks = max(1, int(self.stats.get("tracks", 0) or 0))
        issues = int(self.stats.get("issues", 0) or 0)
        missing = int(self.stats.get("missing", 0) or 0)
        relinked = int(self.stats.get("relinked", 0) or 0)

        integrity = max(0, 100 - int(((issues + missing) / tracks) * 100))
        fingerprint = min(100, int((relinked / tracks) * 100))
        review = issues + missing
        review_load = min(1.0, review / max(1, tracks // 4))

        self.canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#0B1124",
            outline=NEON_PURPLE_DARK,
            width=1
        )

        panels = [
            ("Archive Integrity", f"{integrity}%", integrity / 100),
            ("Fingerprint Rate", f"{fingerprint}%", fingerprint / 100),
            ("Review Queue", str(review), review_load),
        ]

        for index, (label, value, fill_ratio) in enumerate(panels):
            x = left + 12 + index * (panel_width + 12)
            self.canvas.create_rectangle(
                x,
                top + 12,
                x + panel_width,
                top + 95,
                fill="#101630",
                outline=NEON_BLUE,
                width=1
            )
            self.canvas.create_text(
                x + panel_width / 2,
                top + 24,
                text=label,
                fill=NEON_BLUE,
                font=("Segoe UI", 9, "bold")
            )

            self.canvas.create_text(
                x + panel_width / 2,
                top + 52,
                text=value,
                fill=ACCENT,
                font=("Segoe UI", 20, "bold")
            )

            self.canvas.create_rectangle(
                x + 16,
                top + 72,
                x + panel_width - 16,
                top + 78,
                fill="#0A1328",
                outline="",
            )
            self.canvas.create_rectangle(
                x + 16,
                top + 72,
                x + 16 + (panel_width - 32) * fill_ratio,
                top + 78,
                fill=ACCENT,
                outline=""
            )

            if index == 2 and review > 0:
                self.canvas.create_text(
                    x + panel_width / 2,
                    top + 88,
                    text="Action required",
                    fill=WARNING,
                    font=("Segoe UI", 7, "bold")
                )

        self.canvas.create_text(
            left + 14,
            bottom + 18,
            text=f"Tracks: {tracks}  Issues: {issues}  Missing: {missing}  Relinked: {relinked}",
            fill=MUTED,
            anchor="w",
            font=("Segoe UI", 8)
        )

    def draw_health_radar(self, width, height):

        cx = int(width * 0.82)
        cy = height - 52
        radius = 34
        missing = int(self.stats.get("missing", 0) or 0)
        relinked = int(self.stats.get("relinked", 0) or 0)
        issues = int(self.stats.get("issues", 0) or 0)

        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=NEON_BLUE,
            width=1
        )
        self.canvas.create_oval(
            cx - radius * 0.65,
            cy - radius * 0.65,
            cx + radius * 0.65,
            cy + radius * 0.65,
            outline="#1D2A4F",
            width=1
        )

        sweep = math.radians(self.phase * 1.8)
        self.canvas.create_line(
            cx,
            cy,
            cx + math.cos(sweep) * radius,
            cy + math.sin(sweep) * radius,
            fill=ACCENT,
            width=2
        )

        points = [
            (missing, WARNING, -18, -10),
            (relinked, ACCENT, 18, -10),
            (issues, NEON_MAGENTA, 0, 18),
        ]

        for value, color, dx, dy in points:
            if value <= 0:
                continue

            size = min(8, 4 + value)
            self.canvas.create_oval(
                cx + dx - size,
                cy + dy - size,
                cx + dx + size,
                cy + dy + size,
                fill=color,
                outline=""
            )

        self.canvas.create_text(
            cx,
            cy + radius + 10,
            text="ARCHIVE STATUS",
            fill=MUTED,
            font=("Segoe UI", 8, "bold")
        )

        self.canvas.create_text(
            cx,
            cy - radius - 14,
            text="NETWORK SCAN",
            fill=NEON_MAGENTA,
            font=("Segoe UI", 8, "bold")
        )

    def draw_background(self, width, height):

        for i in range(0, width, 28):
            color = "#151737" if (i // 28) % 2 == 0 else "#0B0E22"
            self.canvas.create_line(i, 0, i, height, fill=color)

        for y in range(18, height, 28):
            self.canvas.create_line(0, y, width, y, fill="#171A3A")

        scan_x = int((self.phase / 360) * width)
        self.canvas.create_line(scan_x, 0, scan_x, height, fill=NEON_PURPLE, width=1)
        self.canvas.create_line(max(0, scan_x - 18), 0, max(0, scan_x - 18), height, fill="#2D1E60", width=1)

        self.canvas.create_rectangle(
            1,
            1,
            width - 2,
            height - 2,
            outline=NEON_PURPLE_DARK,
            width=2
        )

        pulse = int((math.sin(math.radians(self.phase * 3)) + 1) * 28)
        self.canvas.create_rectangle(
            18 + pulse // 3,
            18,
            width - 18 - pulse // 3,
            height - 18,
            outline="#241B59",
            width=1
        )

    def draw_connection(self, x1, y1, x2, y2, index):

        self.canvas.create_line(
            x1 + 45,
            y1,
            x2 - 45,
            y2,
            fill=BORDER,
            width=6
        )
        self.canvas.create_line(
            x1 + 45,
            y1,
            x2 - 45,
            y2,
            fill=ACCENT_DARK,
            width=2
        )
        self.canvas.create_line(
            x1 + 45,
            y1 - 10,
            x2 - 45,
            y2 - 10,
            fill=NEON_PURPLE_DARK,
            width=1
        )

    def draw_particle(self, width, y, offset):

        usable = width * 0.75
        start = width * 0.13
        progress = ((self.phase + offset) % 360) / 360
        x = start + usable * progress
        glow = 4 + math.sin(math.radians(self.phase * 4 + offset)) * 2

        self.canvas.create_oval(
            x - glow * 2.2,
            y - glow * 2.2,
            x + glow * 2.2,
            y + glow * 2.2,
            outline=NEON_PURPLE,
            width=1
        )
        self.canvas.create_oval(
            x - glow,
            y - glow,
            x + glow,
            y + glow,
            fill=ACCENT,
            outline=""
        )

    def draw_node(self, x, y, title, subtitle):

        radius = 42
        pulse = 2 + math.sin(math.radians(self.phase * 3 + x)) * 2
        outline = ACCENT if title in {"AI EAR", "ARCHIVE"} else NEON_PURPLE

        self.canvas.create_oval(
            x - radius - pulse,
            y - radius - pulse,
            x + radius + pulse,
            y + radius + pulse,
            outline=NEON_PURPLE_DARK,
            width=1
        )
        self.canvas.create_oval(
            x - radius - 9,
            y - radius - 9,
            x + radius + 9,
            y + radius + 9,
            outline="#143E35" if title in {"AI EAR", "ARCHIVE"} else "#34226D",
            width=1
        )
        self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=BACKGROUND,
            outline=outline,
            width=2
        )
        self.canvas.create_text(
            x,
            y - 8,
            text=title,
            fill=NEON_BLUE if title == "DOCTOR" else TEXT,
            font=("Segoe UI", 11, "bold")
        )
        self.canvas.create_text(
            x,
            y + 13,
            text=subtitle,
            fill=MUTED,
            font=("Segoe UI", 8)
        )

    def draw_lock(self, width, height):

        color = ACCENT if self.stats.get("locked") else WARNING
        x = width - 38
        y = height - 32

        self.canvas.create_rectangle(
            x - 15,
            y - 2,
            x + 15,
            y + 20,
            fill=BACKGROUND,
            outline=color,
            width=2
        )
        self.canvas.create_arc(
            x - 13,
            y - 23,
            x + 13,
            y + 9,
            start=0,
            extent=180,
            style="arc",
            outline=color,
            width=2
        )
        self.canvas.create_text(
            x - 48,
            y + 9,
            text="NO RE-SCAN",
            fill=NEON_MAGENTA if self.stats.get("locked") else color,
            anchor="e",
            font=("Segoe UI", 9, "bold")
        )

    def draw_health_radar(self, width, height):

        cx = int(width * 0.52)
        cy = height - 54
        radius = 34
        missing = int(self.stats.get("missing", 0) or 0)
        relinked = int(self.stats.get("relinked", 0) or 0)
        issues = int(self.stats.get("issues", 0) or 0)

        self.canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            outline=NEON_PURPLE_DARK,
            width=1
        )
        self.canvas.create_oval(
            cx - radius / 2,
            cy - radius / 2,
            cx + radius / 2,
            cy + radius / 2,
            outline="#173F37",
            width=1
        )

        sweep = math.radians(self.phase * 2)
        self.canvas.create_line(
            cx,
            cy,
            cx + math.cos(sweep) * radius,
            cy + math.sin(sweep) * radius,
            fill=ACCENT,
            width=2
        )

        points = [
            (missing, WARNING, -18, -10),
            (relinked, ACCENT, 12, -2),
            (issues, NEON_MAGENTA, -2, 16),
        ]

        for value, color, dx, dy in points:
            if value <= 0:
                continue

            size = min(8, 3 + value)
            self.canvas.create_oval(
                cx + dx - size,
                cy + dy - size,
                cx + dx + size,
                cy + dy + size,
                fill=color,
                outline=""
            )

        self.canvas.create_text(
            cx,
            cy + radius + 12,
            text="ARCHIVE HEALTH RADAR",
            fill=MUTED,
            font=("Segoe UI", 8, "bold")
        )
