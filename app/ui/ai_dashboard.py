"""
DJ AI OS — AI Engine Status Dashboard

Clean Pro DJ status panel showing track info, energy, BPM, key.
No glow effects — just clean data display.
"""

import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, GREEN, BLUE_BRIGHT, AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META,
    R_SM, R_MD,
)


class AIDashboard(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(
            fg_color=SURFACE,
            corner_radius=R_MD,
            border_width=1,
            border_color=BORDER,
        )

        # Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=12, pady=(10, 4))

        self.title = ctk.CTkLabel(
            title_frame,
            text="ENGINE STATUS",
            font=F_H3,
            text_color=TEXT_SECONDARY,
        )
        self.title.pack(side="left")

        # Status badge
        self.status_badge = ctk.CTkLabel(
            title_frame,
            text="IDLE",
            font=("Consolas", 9),
            text_color=TEXT_DIM,
            fg_color=BG,
            corner_radius=3,
            padx=6, pady=2,
        )
        self.status_badge.pack(side="right")

        # Metrics section
        metrics_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=R_SM)
        metrics_frame.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(
            metrics_frame,
            text="TRACK INFO",
            font=F_META,
            text_color=TEXT_DIM,
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # BPM / KEY / ENERGY row
        info_row = ctk.CTkFrame(metrics_frame, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(0, 10))

        # BPM
        bpm_frame = ctk.CTkFrame(info_row, fg_color="transparent")
        bpm_frame.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(bpm_frame, text="BPM", font=F_META, text_color=TEXT_DIM).pack(anchor="w")
        self.bpm = ctk.CTkLabel(bpm_frame, text="--", font=F_H3, text_color=TEXT_PRIMARY)
        self.bpm.pack(anchor="w")

        # KEY
        key_frame = ctk.CTkFrame(info_row, fg_color="transparent")
        key_frame.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(key_frame, text="KEY", font=F_META, text_color=TEXT_DIM).pack(anchor="w")
        self.key = ctk.CTkLabel(key_frame, text="--", font=F_H3, text_color=BLUE_BRIGHT)
        self.key.pack(anchor="w")

        # ENERGY
        energy_frame = ctk.CTkFrame(info_row, fg_color="transparent")
        energy_frame.pack(side="left", padx=(0, 16))
        ctk.CTkLabel(energy_frame, text="ENERGY", font=F_META, text_color=TEXT_DIM).pack(anchor="w")
        self.energy = ctk.CTkLabel(energy_frame, text="--", font=F_H3, text_color=AMBER)
        self.energy.pack(anchor="w")

        # Energy bar
        self.energy_bar = ctk.CTkProgressBar(metrics_frame, height=4, progress_color=RED)
        self.energy_bar.set(0)
        self.energy_bar.pack(fill="x", padx=10, pady=(0, 10))

        # Heart section
        heart_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=R_SM)
        heart_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.heart = ctk.CTkLabel(
            heart_frame, text="HEART: -- | -- | --",
            font=F_BODY, text_color=GREEN,
        )
        self.heart.pack(anchor="w", padx=10, pady=8)

    def update_track(self, track):
        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0)
        key = track.get("key", "N/A")

        self.bpm.configure(text=f"{bpm}")
        self.key.configure(text=f"{key}")
        self.energy.configure(text=f"{energy:.0%}")

        self.energy_bar.set(min(1.0, float(energy or 0)))

        self.status_badge.configure(
            text=track.get("analysis_status", "READY"),
            text_color=GREEN if track.get("analysis_status") == "READY" else TEXT_DIM,
        )

        heart_score = track.get("heart_score", 0)
        color = track.get("emotional_color", "--")
        moment = track.get("crowd_moment", "--")

        self.heart.configure(
            text=f"HEART: {heart_score} | {color} | {moment}"
        )
