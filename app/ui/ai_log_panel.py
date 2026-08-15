"""
DJ AI OS — AI Log Panel

Clean monospace terminal-style log panel.
Dark background, green timestamps, white text.
"""

import time
import tkinter as tk
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

        # Native tk.Text (CTkTextbox creates a CTkScrollbar whose _draw()
        # calls update_idletasks reentrantly — an infinite event storm can
        # hang boot). Styled to match the terminal look.
        row = tk.Frame(self, bg=BG)
        row.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self.text = tk.Text(
            row,
            bg=BG,
            fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY,
            selectbackground="#334",
            selectforeground=TEXT_PRIMARY,
            font=("Consolas", 10),
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=4,
        )
        sb = tk.Scrollbar(
            row, orient="vertical", command=self.text.yview,
            bg=SURFACE, troughcolor=BG, activebackground=BORDER,
            highlightthickness=0, relief="flat", width=10,
        )
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

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
