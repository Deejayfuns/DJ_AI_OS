import customtkinter as ctk

from app.ui.theme import ACCENT, MUTED, PANEL, TEXT
from app.ui.views.base import ViewBase
from app.core.i18n import t, get_language, set_language, available_languages


class SettingsView(ViewBase):

    def build(self, parent):

        win = self.win

        win.make_section_title(
            parent,
            t("sidebar.settings"),
            "Lisans durumu ve arsiv sinirlari."
        )

        plan = win.license.get_plan()

        stats = ctk.CTkFrame(parent, fg_color="transparent")
        stats.pack(fill="x")

        win.make_metric(stats, t("common.version"), plan.get("plan", "DEMO"))
        win.make_metric(stats, "LICENSED", "YES" if plan.get("licensed") else "NO")
        win.make_metric(stats, "MAX TRACKS", plan.get("max_tracks", 0))
        win.make_metric(stats, "ARCHIVED", win.total_archived)

        # ================= UPDATES (yalnızca updates_active lisanslar) =================
        updates = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8)
        updates.pack(fill="x", pady=12)

        ctk.CTkLabel(
            updates,
            text="UPDATES",
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 4))

        try:
            tech_version = getattr(win, "app_tech_version", "?")
        except Exception:
            tech_version = "?"
        updates_active = bool(plan.get("entitlements", {}).get("updates_active"))

        ctk.CTkLabel(
            updates,
            text=(
                f"Uygulama sürümü: {tech_version} | "
                f"Güncellemeler: {'AKTİF' if updates_active else 'AKTİF DEĞİL'}"
            ),
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(0, 6))

        if not updates_active:
            ctk.CTkLabel(
                updates,
                text=(
                    "Güncellemeler yalnızca lisansı aktif olan kullanıcılara "
                    "sunulur. Paketini yenilemek için Account bölümünü kullan."
                ),
                text_color=MUTED,
                wraplength=900,
                justify="left"
            ).pack(anchor="w", padx=12, pady=(0, 12))
        else:
            ctk.CTkLabel(
                updates,
                text="Güncelleme beklenmiyor / henüz kontrol edilmedi.",
                text_color=MUTED
            ).pack(anchor="w", padx=12, pady=(0, 4))

            status_label = ctk.CTkLabel(
                updates,
                text="Son kontrol: —",
                text_color=TEXT,
                wraplength=900,
                justify="left"
            )
            status_label.pack(anchor="w", padx=12, pady=(0, 4))

            button_row = ctk.CTkFrame(updates, fg_color="transparent")
            button_row.pack(fill="x", padx=12, pady=(0, 12))

            ctk.CTkButton(
                button_row,
                text="GÜNCELLEME KONTROL",
                width=180,
                command=win.check_for_updates_ui
            ).pack(side="left", padx=(0, 8))

            apply_button = ctk.CTkButton(
                button_row,
                text="UYGULA",
                width=120,
                state="disabled",
                command=win.apply_update_ui
            )
            apply_button.pack(side="left", padx=(0, 8))

            # main_window handler'ları bu etiketleri günceller.
            win.update_status_label = status_label
            win.update_apply_button = apply_button

        # Language selector
        lang_frame = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=8)
        lang_frame.pack(fill="x", pady=12)

        ctk.CTkLabel(
            lang_frame,
            text=t("common.language"),
            font=("Segoe UI", 14, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        current_lang = get_language()
        lang_var = ctk.StringVar(value=current_lang)

        def on_lang_change(choice):
            if set_language(choice):
                win.log(t("messages.language_changed", lang=choice))
                # Sync the voice assistant's TTS language so ASTRA speaks
                # in the newly selected language (tr -> AhmetNeural, etc.)
                try:
                    if hasattr(win, "voice_assistant") and win.voice_assistant:
                        win.voice_assistant.set_language(choice)
                except Exception:
                    pass
                # Rebuild sidebar to reflect language change
                if hasattr(win, "sidebar"):
                    win.sidebar._build()

        lang_combo = ctk.CTkComboBox(
            lang_frame,
            values=[code for code, _ in available_languages()],
            variable=lang_var,
            command=on_lang_change,
            width=150,
        )
        lang_combo.pack(anchor="w", padx=12, pady=(0, 12))

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
            "F11 Stage Mode (immersive fullscreen DJ)",
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

        # Selectable neural voice model (persisted, used by boot greeting + assistant)
        try:
            from app.core import voice_config
            current_voice = voice_config.get_voice_id()
            voice_models = voice_config.get_voice_models()
            voice_labels = [m["label"] for m in voice_models]
            voice_id_by_label = {m["label"]: m["id"] for m in voice_models}

            sel_frame = ctk.CTkFrame(voice_box, fg_color="transparent")
            sel_frame.pack(fill="x", padx=12, pady=(0, 10))

            ctk.CTkLabel(
                sel_frame,
                text="SES MODELI (ASTRA):",
                text_color=MUTED
            ).pack(side="left", padx=(0, 8))

            current_label = next(
                (m["label"] for m in voice_models if m["id"] == current_voice),
                voice_models[0]["label"],
            )
            voice_var = ctk.StringVar(value=current_label)

            def on_voice_change(choice):
                vid = voice_id_by_label.get(choice)
                if vid:
                    voice_config.set_voice_id(vid)

            voice_combo = ctk.CTkComboBox(
                sel_frame,
                values=voice_labels,
                variable=voice_var,
                command=on_voice_change,
                width=220,
            )
            voice_combo.pack(side="left", padx=6, pady=4)
        except Exception:
            pass

        for action in win.voice_assistant.next_actions():
            ctk.CTkLabel(
                voice_box,
                text=f"- {action}",
                text_color=MUTED
            ).pack(anchor="w", padx=18, pady=1)
