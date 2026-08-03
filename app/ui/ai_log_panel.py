import customtkinter as ctk
import time


class AILogPanel(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color="#0B0B0B")

        self.title = ctk.CTkLabel(
            self,
            text="MUZIK DOKTORU MESAJLARI",
            font=("Arial", 14, "bold"),
            text_color="#00FFA3"
        )
        self.title.pack(anchor="w", padx=10, pady=5)

        self.text = ctk.CTkTextbox(
            self,
            fg_color="#111111",
            text_color="#DDDDDD",
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
