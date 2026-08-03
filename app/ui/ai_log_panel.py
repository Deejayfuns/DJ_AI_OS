import customtkinter as ctk
import time

from app.ui.theme import ACCENT, BACKGROUND, GLASS_BG, PANEL, TEXT, F_H3


class AILogPanel(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color=GLASS_BG)

        self.title = ctk.CTkLabel(
            self,
            text="MUZIK DOKTORU MESAJLARI",
            font=F_H3,
            text_color=ACCENT
        )
        self.title.pack(anchor="w", padx=10, pady=5)

        self.text = ctk.CTkTextbox(
            self,
            fg_color=PANEL,
            text_color=TEXT,
            wrap="word"
        )
        self.text.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, message: str):

        if not self.winfo_exists() or not self.text.winfo_exists():
            return

        ts = time.strftime("%H:%M:%S")

        try:
            self.text.insert("end", f"[{ts}] {message}\n")
            self.text.see("end")
        except Exception:
            pass
