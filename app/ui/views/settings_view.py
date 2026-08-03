import customtkinter as ctk

from app.ui.theme import ACCENT, MUTED, PANEL, TEXT
from app.ui.views.base import ViewBase


class SettingsView(ViewBase):

    def build(self, parent):

        win = self.win

        win.make_section_title(
            parent,
            "Settings",
            "Lisans durumu ve arsiv sinirlari."
        )

        plan = win.license.get_plan()

        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.pack(fill="x")

        win.make_metric(stats, "PLAN", plan.get("plan", "DEMO"))
        win.make_metric(stats, "LICENSED", "YES" if plan.get("licensed") else "NO")
        win.make_metric(stats, "MAX TRACKS", plan.get("max_tracks", 0))
        win.make_metric(stats, "ARCHIVED", win.total_archived)

        shortcuts = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8)
        shortcuts.pack(fill="x", pady=12)

        ctk.CTkLabel(
            shortcuts,
            text="KEYBOARD SHORTCUTS",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        lines = [
            "Ctrl+L Load Library",
            "Ctrl+G Generate Set",
            "Space Play/Stop",
            "Ctrl+S Show Director",
            "Ctrl+D Deck Studio",
            "Ctrl+E Export Center",
            "Ctrl+R Genre Review",
            "Ctrl+K Command Palette",
            "Ctrl+Shift+D Next Duplicate Review",
            "Ctrl+F Search Filter",
            "Ctrl+1 Load selected to Deck A",
            "Ctrl+2 Load selected to Deck B",
            "Ctrl+M AI Auto Mix Plan",
            "F5 Refresh current view",
            "Duplicate dialog: 1 old delete, 2 duplicate folder, 3 keep both, Enter AI recommendation",
        ]

        for line in lines:
            ctk.CTkLabel(
                shortcuts,
                text=line,
                text_color=TEXT
            ).pack(anchor="w", padx=12, pady=2)

        voice = win.voice_assistant.capability_summary()
        voice_box = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8)
        voice_box.pack(fill="x", pady=12)

        ctk.CTkLabel(
            voice_box,
            text="VOICE AI",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            voice_box,
            text=(
                f"{voice['message']} | "
                f"TTS: {voice.get('tts_engine')} "
                f"({'READY' if voice.get('tts_available') else 'MISSING'}) | "
                f"STT: {voice.get('stt_engine')} "
                f"({'READY' if voice.get('stt_available') else 'MISSING'}) | "
                f"Turkish voice: "
                f"{voice.get('turkish_voice') or 'NOT FOUND'} | "
                f"Turkish TTS ready: "
                f"{'YES' if voice.get('turkish_tts_ready') else 'NO'}"
            ),
            text_color=TEXT,
            wraplength=1100,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        test_frame = ctk.CTkFrame(voice_box, fg_color="transparent")
        test_frame.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            test_frame,
            text="MIC TEST",
            width=120,
            command=win.run_voice_mic_once
        ).pack(side="left", padx=6, pady=4)

        ctk.CTkButton(
            test_frame,
            text="TTS TEST",
            width=120,
            command=win.speak_last_voice_reply
        ).pack(side="left", padx=6, pady=4)

        ctk.CTkButton(
            test_frame,
            text="VOICE CHECK",
            width=120,
            command=win.run_voice_diagnostics
        ).pack(side="left", padx=6, pady=4)

        for action in win.voice_assistant.next_actions():
            ctk.CTkLabel(
                voice_box,
                text=f"- {action}",
                text_color=MUTED
            ).pack(anchor="w", padx=18, pady=1)
