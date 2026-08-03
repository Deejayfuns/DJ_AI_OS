import customtkinter as ctk

from app.ui.theme import ACCENT, CARD, MUTED, NEON_BLUE, NEON_MAGENTA, NEON_PURPLE_DARK, PANEL, TEXT


class AIDashboard(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(
            fg_color=PANEL,
            corner_radius=8,
            border_width=1,
            border_color=NEON_PURPLE_DARK
        )

        self.title = ctk.CTkLabel(
            self,
            text="AI ENGINE STATUS",
            font=("Arial", 16, "bold"),
            text_color=NEON_BLUE
        )
        self.title.pack(anchor="w", padx=10, pady=5)

        self.summary_card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        self.summary_card.pack(fill="x", padx=10, pady=5)

        self.model_label = ctk.CTkLabel(
            self.summary_card,
            text="AI ENGINE METRICS",
            text_color=NEON_BLUE,
            font=("Segoe UI", 12, "bold")
        )
        self.model_label.pack(anchor="w", padx=10, pady=(10, 2))

        self.status = ctk.CTkLabel(
            self.summary_card,
            text="AI STATUS: IDLE",
            text_color=TEXT,
            font=("Segoe UI", 11)
        )
        self.status.pack(anchor="w", padx=10, pady=(0, 10))

        self.energy = ctk.CTkProgressBar(self)
        self.energy.pack(fill="x", padx=10, pady=5)

        self.bpm = ctk.CTkLabel(self, text="BPM: --", text_color=TEXT)
        self.bpm.pack(anchor="w", padx=10)

        self.key = ctk.CTkLabel(self, text="KEY: --", text_color=TEXT)
        self.key.pack(anchor="w", padx=10)

        self.heart = ctk.CTkLabel(self, text="HEART: --", text_color=NEON_MAGENTA)
        self.heart.pack(anchor="w", padx=10, pady=(4, 0))

    def update_track(self, track):

        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0)
        key = track.get("key", "N/A")

        self.bpm.configure(text=f"BPM: {bpm}")
        self.key.configure(text=f"KEY: {key}")

        self.energy.set(min(1.0, float(energy or 0)))

        self.status.configure(
            text=f"AI STATUS: {track.get('analysis_status', 'READY')}"
        )

        heart_score = track.get("heart_score", 0)
        color = track.get("emotional_color", "--")
        moment = track.get("crowd_moment", "--")

        self.heart.configure(
            text=f"HEART: {heart_score} | {color} | {moment}"
        )
