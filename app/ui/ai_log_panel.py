"""
DJ AI OS — AI Log Panel

Clean monospace terminal-style log panel.
Dark background, green timestamps, white text.
"""

import time
import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, BORDER, GREEN, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_META,
)


class AILogPanel(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master, fg_color=BG, corner_radius=6, border_width=1, border_color=BORDER)

        self.max_lines = 200
        self._lines = []

        # Title
        ctk.CTkLabel(
            self, text="LOG", font=("Consolas", 9), text_color=TEXT_DIM,
        ).pack(anchor="w", padx=8, pady=(6, 2))

        self.text = ctk.CTkTextbox(
            self,
            fg_color=BG,
            text_color=TEXT_PRIMARY,
            font=("Consolas", 10),
            wrap="word",
        )
        self.text.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def log(self, message):
        if not self.winfo_exists() or not self.text.winfo_exists():
            return

        ts = time.strftime("%H:%M:%S")

        try:
            self.text.insert("end", f"[{ts}] {message}\n")
            self.text.see("end")
            self._lines.append(f"[{ts}] {message}")
            if len(self._lines) > self.max_lines:
                self._lines = self._lines[-self.max_lines:]
        except Exception:
            pass
