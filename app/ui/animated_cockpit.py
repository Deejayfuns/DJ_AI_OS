"""
DJ AI OS — Archive Cockpit (Pro DJ style)

Clean pipeline flow with dots + lines.
Stats cards below. No neon glow — just clean data visualization.
"""

import math
import tkinter as tk
import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
)


class AnimatedArchiveCockpit(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)

        self.stats = {
            "tracks": 0, "issues": 0, "locked": True,
            "mode": "IDEMPOTENT", "missing": 0, "relinked": 0,
        }

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(header, text="ARCHIVE PIPELINE", font=("Segoe UI", 13, "bold"),
                      text_color=TEXT_SECONDARY).pack(side="left")

        self.mode_label = ctk.CTkLabel(header, text="LOCKED", font=("Consolas", 9),
                                        text_color=GREEN, fg_color=BG, corner_radius=3, padx=6, pady=2)
        self.mode_label.pack(side="right")

        # Canvas
        self.canvas = tk.Canvas(self, height=180, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="x", padx=10, pady=8)

        # Footer stats
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 10))

        self.track_label = self._stat_label(footer, "TRACKS 0")
        self.issue_label = self._stat_label(footer, "DOCTOR 0")
        self.health_label = self._stat_label(footer, "OK 0 / MISSING 0")

        self._draw()

    def _stat_label(self, parent, text):
        label = ctk.CTkLabel(parent, text=text, fg_color=BG, corner_radius=4,
                             height=28, text_color=TEXT_SECONDARY,
                             font=("Consolas", 10))
        label.pack(side="left", fill="x", expand=True, padx=4)
        return label

    def update_stats(self, tracks=0, issues=0, locked=True, mode="IDEMPOTENT", missing=0, relinked=0):
        self.stats = {"tracks": tracks, "issues": issues, "locked": locked,
                       "mode": mode, "missing": missing, "relinked": relinked}

        self.track_label.configure(text=f"TRACKS {tracks}")
        self.issue_label.configure(
            text=f"DOCTOR {issues}",
            text_color=AMBER if issues else TEXT_SECONDARY,
        )
        self.health_label.configure(
            text=f"OK {relinked} / MISSING {missing}",
            text_color=GREEN if not missing else AMBER,
        )
        self.mode_label.configure(
            text="LOCKED" if locked else "OPEN",
            text_color=GREEN if locked else AMBER,
        )
        self._draw()

    def _draw(self, **kwargs):
        if not hasattr(self, 'canvas'):
            return
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 1)
        h = 180

        # Pipeline: SCAN → ANALYZE → DIAGNOSE → STORE
        stages = [
            ("SCAN", GREEN),
            ("ANALYZE", BLUE_BRIGHT),
            ("DIAGNOSE", AMBER),
            ("STORE", RED),
        ]

        start_x = 60
        end_x = w - 60
        cy = 50
        step = (end_x - start_x) / (len(stages) - 1)

        # Draw connecting lines first (behind dots)
        for i in range(len(stages) - 1):
            x1 = start_x + i * step
            x2 = start_x + (i + 1) * step
            self.canvas.create_line(x1, cy, x2, cy, fill=BORDER, width=2)

        # Draw stage dots
        for i, (label, color) in enumerate(stages):
            x = start_x + i * step

            # Outer circle
            self.canvas.create_oval(x - 20, cy - 20, x + 20, cy + 20,
                                     fill=BG, outline=color, width=2)
            # Inner dot
            self.canvas.create_oval(x - 5, cy - 5, x + 5, cy + 5, fill=color, outline="")
            # Label below
            self.canvas.create_text(x, cy + 32, text=label, fill=TEXT_SECONDARY,
                                     font=("Consolas", 9, "bold"))

        # Bottom stats area
        tracks = max(1, self.stats.get("tracks", 1))
        issues = self.stats.get("issues", 0)
        missing = self.stats.get("missing", 0)
        relinked = self.stats.get("relinked", 0)

        bar_y = 110
        bar_w = (w - 120) / 3 - 12

        panels = [
            ("Integrity", f"{max(0, 100 - int(((issues + missing) / tracks) * 100))}%"),
            ("Fingerprint", f"{min(100, int((relinked / tracks) * 100))}%"),
            ("Review Queue", str(issues + missing)),
        ]

        for i, (label, value) in enumerate(panels):
            x = 60 + i * (bar_w + 12)
            self.canvas.create_rectangle(x, bar_y, x + bar_w, bar_y + 50,
                                          fill=BG, outline=BORDER, width=1)
            self.canvas.create_text(x + bar_w / 2, bar_y + 12, text=label,
                                     fill=TEXT_DIM, font=("Consolas", 9))
            self.canvas.create_text(x + bar_w / 2, bar_y + 32, text=value,
                                     fill=GREEN, font=("Consolas", 14, "bold"))

    def animate(self):
        pass  # Static — no animation needed in Pro DJ mode
