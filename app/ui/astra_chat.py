"""
DJ AI OS — Astra Chat Panel

Real-time conversation with Astra AI assistant.
Every action is shown as a chat message.
User can see what Astra is doing and respond.

Features:
- Chat bubbles (user vs Astra)
- Action cards (what Astra did)
- Typing indicator
- Voice input button
- Quick action buttons
"""

import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META,
)
from app.core.i18n import t


class AstraChatPanel:
    """
    Astra AI Chat Interface.
    Shows all AI interactions as chat messages.
    """

    def __init__(self, win):
        self.win = win
        self._messages = []
        self._typing = False

    def build(self, parent):
        win = self.win

        # Title bar
        title = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=0, height=40)
        title.pack(fill="x")
        title.pack_propagate(False)

        ctk.CTkLabel(title, text=t("astra_chat.title"), font=F_H3, text_color=RED).pack(side="left", padx=12)

        # Status dot
        self.status_dot = ctk.CTkLabel(
            title, text="●", font=F_META, text_color=GREEN
        )
        self.status_dot.pack(side="left", padx=4)

        self.status_text = ctk.CTkLabel(
            title, text=t("astra_chat.status_online"), font=F_META, text_color=TEXT_DIM
        )
        self.status_text.pack(side="left", padx=4)

        # Voice button
        self.voice_btn = ctk.CTkButton(
            title, text="🎤", width=36, height=30,
            fg_color=BG, hover_color=RED, text_color=TEXT_DIM,
            font=("Segoe UI Emoji", 14), border_width=1, border_color=BORDER,
            command=self._toggle_voice,
        )
        self.voice_btn.pack(side="right", padx=8)
        self._voice_active = False

        # Chat area
        chat_frame = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        chat_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.chat_canvas = ctk.CTkScrollableFrame(
            chat_frame, fg_color="transparent",
            scrollbar_button_color=SURFACE_RAISED,
            scrollbar_button_hover_color=BORDER,
        )
        self.chat_canvas.pack(fill="both", expand=True)

        # Welcome message
        self._add_message("astra", t("astra_chat.welcome"))

        # Input area
        input_frame = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=0, height=50)
        input_frame.pack(fill="x")
        input_frame.pack_propagate(False)

        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text=t("astra_chat.input_placeholder"),
            font=F_BODY, fg_color=BG, border_color=BORDER,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=8)
        self.input_entry.bind("<Return>", lambda e: self._send_message())

        self.send_btn = ctk.CTkButton(
            input_frame, text=t("astra_chat.send"), width=80, height=34,
            fg_color=RED, hover_color="#FF5A68", text_color="#FFF",
            font=F_BODY_BOLD, command=self._send_message,
        )
        self.send_btn.pack(side="right", padx=(4, 8), pady=8)

        # Quick actions
        quick_frame = ctk.CTkFrame(parent, fg_color="transparent")
        quick_frame.pack(fill="x", padx=4, pady=(0, 4))

        quick_labels = [
            t("astra_chat.quick.mission"),
            t("astra_chat.quick.make_beat"),
            t("astra_chat.quick.build_set"),
            t("astra_chat.quick.analyze"),
            t("astra_chat.quick.key_match"),
        ]
        quick_cmds = [
            t("astra_chat.quick_cmds.mission"),
            t("astra_chat.quick_cmds.make_beat"),
            t("astra_chat.quick_cmds.build_set"),
            t("astra_chat.quick_cmds.analyze"),
            t("astra_chat.quick_cmds.key_match"),
        ]

        for label, cmd in zip(quick_labels, quick_cmds):
            ctk.CTkButton(
                quick_frame, text=label, fg_color=BG, hover_color=SURFACE_RAISED,
                text_color=TEXT_SECONDARY, font=F_META, width=90, height=26,
                border_width=1, border_color=BORDER,
                command=lambda c=cmd: (self.input_entry.delete(0, "end"),
                                        self.input_entry.insert(0, c),
                                        self._send_message()),
            ).pack(side="left", padx=2)

    def _send_message(self):
        """Send user message and get Astra response."""
        text = self.input_entry.get().strip()
        if not text:
            return

        self.input_entry.delete(0, "end")

        # Show user message
        self._add_message("user", text)

        # Show typing indicator
        self._show_typing(True)

        # Process command (in background)
        import threading
        threading.Thread(target=self._process_command, args=(text,), daemon=True).start()

    def _process_command(self, text):
        """Process command and show response."""
        try:
            # Build context
            win = self.win
            context = {
                "library": getattr(win, "library", []) or getattr(win, "saved_tracks", []),
                "tracks": getattr(win, "current_set", []) or getattr(win, "library", []),
                "track": getattr(win, "selected_track", None),
                "path": getattr(win, "selected_track", {}).get("path") if getattr(win, "selected_track", None) else None,
            }

            # ---- ASTRA KİMLİĞİ: GÖREV ----
            text_lower = text.lower()
            if any(w in text_lower for w in ["görev", "gorev", "misyon", "mission", "kimsin",
                                             "ne yapiyorsun", "ne yapıyorsun", "amac", "amaç"]):
                result = {
                    "reply": (
                        "Ben DJ AI OS — bir DJ'in tam zamanlı AI ko-pilotuyum. 🎧\n\n"
                        "Görevim: kütüphaneni temiz tutmak, setini akıllı kurmak, "
                        "sahneyi senkronize etmek ve prodüksiyona köprü kurmak.\n\n"
                        "Yapabileceklerim:\n"
                        "• Kütüphane: tara, analiz et, yinelenenleri bul, kayıp dosyaları yeniden bağla\n"
                        "• Set: BPM/key uyumlu set kur, enerji eğrisi, kalabalık rolleri\n"
                        "• Sahne: Rekordbox/FL Studio hazır çıktı, stem'ler, manifest'ler\n"
                        "• Canlı: beat üret (LIVE MODE), ses analizi, mix önerileri\n\n"
                        "Ben araçlarım, sahnede olan sensin. Kararları sen verirsin, "
                        "verileri ve hızı ben sağlarım. 🌍"
                    ),
                    "action": "astra_mission",
                }
            # ---- MARS (eğlencelik uzay genre'si) ----
            elif any(w in text_lower for w in ["mars", "space", "uzay", "galaksi", "astronot"]):
                from app.ai.mars_mission import handle_mars_query
                result = handle_mars_query(text)
                reply = result.get("reply", "Mars plani hazirlaniyor...")
                action = result.get("action", "mars_mission")

            # ---- STYLE SCENE: Astra sahneyi yönetir ----
            elif any(w in text_lower for w in ["sahne", "scene", "sahneyi", "stil", "style"]):
                result = self._handle_style_scene(text, context)
            else:
                # Process through AstraBrain
                from app.ai.voice_assistant import VoiceAssistant
                va = VoiceAssistant()
                result = va.interpret_command(text, context=context)

                reply = result.get("reply", "Komut islenemedi.")
                action = result.get("action", "")

            # Show action card if there's a result
            if action and action != "unknown":
                self._add_action_card(action, result.get("result", {}))

            # Show Astra reply
            self._add_message("astra", reply)

            # Speak reply
            self.win.after(100, lambda: self.win.voice_assistant.speak_reply(reply[:200]))

        except Exception as e:
            self._add_message("astra", f"Hata olustu: {e}")

        finally:
            self._show_typing(False)

    def _handle_style_scene(self, text, context):
        """
        Astra-managed setup scene. Interprets things like:
          "sahne kur" / "set kur"          -> build scene from library
          "sahneyi oynat" / "oynat"        -> play through the scene
          "sonraki" / "siradaki"           -> next style
          "<yol>/<dosya> icin style yap"   -> single track scene
        """
        win = self.win
        lower = text.lower()
        path = context.get("path") if context else None

        try:
            from app.ai.style_scene import StyleScene
            from app.ai.style_generator import describe_style

            # Make sure the performance panel exists (open live performance view)
            if not hasattr(win, "live_perf_panel"):
                win.set_view("live_performance")
            panel = getattr(win, "live_perf_panel", None)
            if panel is None:
                return {"reply": "Canli performans paneli hazir degil.", "action": "scene", "result": {}}

            # single track case: path provided in text or context
            import os, re
            # look for a filesystem path in the text
            m = re.search(r'[A-Za-z]:[\\/][^\s,;]+', text)
            single = m.group(0) if m else (path if path else None)

            scene = StyleScene(sample_rate=44100)

            if single and os.path.exists(single):
                if os.path.isdir(single):
                    n = scene.add_folder(single)
                    reply = f"{n} parca bulundu, dinliyorum ve stil yaziyorum..."
                else:
                    scene.add_track(single)
                    reply = f"{os.path.basename(single)} dinleniyor, stil yaziliyor..."
            else:
                # use library
                tracks = context.get("library") or []
                added = 0
                for t in tracks[:10]:
                    tp = t.get("path") if isinstance(t, dict) else None
                    if tp and os.path.exists(tp):
                        try:
                            scene.add_track(tp)
                            added += 1
                        except Exception:
                            continue
                if added == 0:
                    return {
                        "reply": ("Sahne kurmak icin once kutuphaneye sarki ekle ya da "
                                  "bana bir dosya yolu ver.\n"
                                  "Ornek: 'C:/Muzik/parca.mp3 icin style yap'"),
                        "action": "scene", "result": {},
                    }
                reply = f"Kutuphaneden {added} parca secildi, dinliyorum..."

            panel.mount_scene(scene)
            scene.build(
                on_progress=lambda i, t, name: None,
                on_done=lambda s: self.after(0, lambda: self._scene_done(s)),
            )

            return {
                "reply": f"🎧 {reply}\nBeat Studio -> LIVE PERFORMANCE paneline baktigimda ilerlemeyi gorursun. Analiz bitince otomatik calar.",
                "action": "scene",
                "result": {"tracks": scene.analyzed_count(), "total": len(scene.tracks())},
            }

        except Exception as exc:
            return {"reply": f"Sahne hatasi: {exc}", "action": "scene", "result": {}}

    def _scene_done(self, scene):
        """Called on the UI thread when a scene finishes analyzing."""
        try:
            panel = getattr(self.win, "live_perf_panel", None)
            if panel:
                panel._poll_scene()
            self._add_message("astra", f"🤖 Sahne hazir: {scene.analyzed_count()} parca stil aldi. "
                                       "Play ediyorum — ▶ ile siradaki parca.")
        except Exception:
            pass

    def _add_message(self, sender, text):
        """Add a chat message."""
        is_user = (sender == "user")

        msg_frame = ctk.CTkFrame(
            self.chat_canvas,
            fg_color=SURFACE_RAISED if is_user else SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=RED if is_user else BORDER,
        )
        msg_frame.pack(fill="x", padx=8 if is_user else 40, pady=4,
                       anchor="e" if is_user else "w")

        # Sender label
        sender_text = t("astra_chat.you") if is_user else "Astra"
        sender_color = RED if is_user else BLUE_BRIGHT

        ctk.CTkLabel(
            msg_frame, text=sender_text, font=F_META, text_color=sender_color,
        ).pack(anchor="w" if not is_user else "e", padx=10, pady=(6, 0))

        # Message text
        ctk.CTkLabel(
            msg_frame, text=text, font=F_BODY, text_color=TEXT_PRIMARY,
            wraplength=500, justify="left" if not is_user else "right",
        ).pack(anchor="w" if not is_user else "e", padx=10, pady=(2, 8))

        # Scroll to bottom
        self.chat_canvas.update_idletasks()
        self.chat_canvas._parent_canvas.yview_moveto(1.0)

    def _add_action_card(self, action, result):
        """Add an action card showing what Astra did."""
        card = ctk.CTkFrame(
            self.chat_canvas,
            fg_color=BG, corner_radius=6,
            border_width=1, border_color=GREEN,
        )
        card.pack(fill="x", padx=40, pady=4, anchor="w")

        # Action header
        ctk.CTkLabel(
            card, text=f"✓ {action.replace('_', ' ').title()}",
            font=F_META, text_color=GREEN,
        ).pack(anchor="w", padx=8, pady=(6, 2))

        # Action details (compact)
        if isinstance(result, dict):
            details = []
            for k, v in result.items():
                if k in ("bpm", "key", "energy", "mood", "score", "tracks"):
                    details.append(f"{k}: {v}")
            if details:
                ctk.CTkLabel(
                    card, text=" | ".join(details[:5]),
                    font=F_META, text_color=TEXT_DIM, wraplength=400,
                ).pack(anchor="w", padx=8, pady=(0, 6))

    def _show_typing(self, show):
        """Show/hide typing indicator."""
        self._typing = show
        if show:
            self.status_text.configure(text="Asta yaziyor...")
            self.status_dot.configure(text_color=AMBER)
        else:
            self.status_text.configure(text="Hosgeldiniz")
            self.status_dot.configure(text_color=GREEN)

    def _toggle_voice(self):
        """Toggle voice input."""
        self._voice_active = not self._voice_active
        if self._voice_active:
            self.voice_btn.configure(fg_color=RED, text_color="#FFF")
            self.status_text.configure(text="Mikrofon dinleniyor...")
            self.status_dot.configure(text_color=RED)
            # Start listening in background
            import threading
            threading.Thread(target=self._listen_voice, daemon=True).start()
        else:
            self.voice_btn.configure(fg_color=BG, text_color=TEXT_DIM)
            self.status_text.configure(text="Hosgeldiniz")
            self.status_dot.configure(text_color=GREEN)

    def _listen_voice(self):
        """Listen for voice input."""
        try:
            heard = self.win.voice_assistant.listen_once(timeout=5, phrase_time_limit=7)
            if heard and heard.get("ok"):
                text = heard.get("text", "")
                if text:
                    self.win.after(100, lambda: self._handle_voice_result(text))
        except Exception:
            pass
        finally:
            self.win.after(100, lambda: self._toggle_voice())

    def _handle_voice_result(self, text):
        """Handle voice input result."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, text)
        self._send_message()

    def add_system_message(self, text):
        """Add a system notification (e.g., from background processes)."""
        self._add_message("astra", f"[Sistem] {text}")
