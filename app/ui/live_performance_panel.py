"""
DJ AI OS — Live Performance Panel

Real instrument plugin beat production with:
- Style-from-track: drop a song -> AI analyzes -> generates fresh pattern
- Genre quick-load (house / tech / techno / trap / mars)
- 16-step per-channel pattern grid (click cells to toggle)
- Live BPM / swing / master level controls
- Per-channel live instrument params (automation)
- Scene A/B capture & recall
- Real-time audio out through sounddevice
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.instruments import list_instruments
from app.ai.live_performance import LivePerformanceEngine

try:
    import windnd
    HAS_WINDND = True
except Exception:
    HAS_WINDND = False

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False


class LivePerformancePanel(ctk.CTkFrame):
    """Live beat production with real instrument plugins."""

    GENRES = ["house", "tech_house", "techno", "melodic_techno", "trap", "mars"]

    def __init__(self, master, sample_rate=44100, chunk_size=1024):
        super().__init__(master, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        self.sr = sample_rate
        self.chunk_size = chunk_size

        self.engine = LivePerformanceEngine(bpm=128, sample_rate=sample_rate)
        self.engine.load_genre("house")

        self._stream = None
        self._stream_gen = None
        self._running = False
        self._poll_job = None

        # UI state
        self._cell_buttons = {}  # channel -> list of buttons
        self._channels = []

        self._build()
        self._refresh_channels()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(header, text="LIVE PERFORMANCE", font=F_H3, text_color=RED).pack(side="left")
        self.badge = ctk.CTkLabel(header, text="STOPPED", font=F_MONO, text_color=TEXT_DIM,
                                  fg_color=BG, corner_radius=3, padx=8, pady=2)
        self.badge.pack(side="right")
        ctk.CTkButton(header, text="SYNTH", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=72, height=24,
                      command=self._toggle_synth_editor).pack(side="right", padx=6)

        # ---- STYLE FROM TRACK ----
        style_box = ctk.CTkFrame(self, fg_color=BG, corner_radius=6, border_width=1, border_color=RED)
        style_box.pack(fill="x", padx=12, pady=(4, 8))

        top = ctk.CTkFrame(style_box, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(top, text="🎵 STYLE FROM TRACK", font=F_BODY_BOLD, text_color=RED).pack(side="left")
        self.style_status = ctk.CTkLabel(top, text="", font=F_META, text_color=TEXT_DIM)
        self.style_status.pack(side="right")

        drop_row = ctk.CTkFrame(style_box, fg_color="transparent")
        drop_row.pack(fill="x", padx=10, pady=(2, 8))
        self.drop_label = ctk.CTkLabel(
            drop_row,
            text="Bir sarki surukle-birak veya sec — AI dinler, tarzini cikarir, yeni beat yazar",
            font=F_META, text_color=TEXT_DIM, height=36,
            fg_color=SURFACE, corner_radius=4,
        )
        self.drop_label.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(drop_row, text="SARKI SEC", fg_color=RED, hover_color=RED_HOVER,
                      text_color="#FFF", font=F_BODY_BOLD, width=90, height=34,
                      command=self._select_track).pack(side="left")

        # hook drag-drop on the style box
        if HAS_WINDND:
            try:
                windnd.hook_dropfiles(style_box, func=self._on_dropped)
            except Exception:
                pass

        # Style result line
        self.style_result = ctk.CTkLabel(style_box, text="", font=F_MONO, text_color=GREEN,
                                         anchor="w", wraplength=720, justify="left")
        self.style_result.pack(fill="x", padx=10, pady=(0, 8))

        # ---- Genre buttons ----
        genre_row = ctk.CTkFrame(self, fg_color="transparent")
        genre_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(genre_row, text="GENRE:", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        for g in self.GENRES:
            ctk.CTkButton(genre_row, text=g.upper().replace("_", " "), fg_color=SURFACE_RAISED,
                          hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META, height=26,
                          width=84, command=lambda x=g: self._load_genre(x)).pack(side="left", padx=3)

        # ---- Play controls ----
        ctrl = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        ctrl.pack(fill="x", padx=12, pady=4)

        self.play_btn = ctk.CTkButton(ctrl, text="PLAY", fg_color=GREEN, hover_color="#3DAE6C",
                                      text_color="#FFF", font=F_BODY_BOLD, width=80,
                                      command=self.toggle_play)
        self.play_btn.pack(side="left", padx=(8, 12), pady=8)

        ctk.CTkLabel(ctrl, text="BPM", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.bpm_slider = ctk.CTkSlider(ctrl, from_=60, to=180, number_of_steps=120, command=self._on_bpm)
        self.bpm_slider.set(128)
        self.bpm_slider.pack(side="left", fill="x", expand=True, padx=(4, 12), pady=8)

        ctk.CTkLabel(ctrl, text="SWING", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.swing_slider = ctk.CTkSlider(ctrl, from_=0, to=0.5, number_of_steps=50, command=self._on_swing)
        self.swing_slider.set(0.1)
        self.swing_slider.pack(side="left", fill="x", expand=True, padx=(4, 12), pady=8)

        ctk.CTkLabel(ctrl, text="LEVEL", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.level_slider = ctk.CTkSlider(ctrl, from_=0, to=1.5, number_of_steps=60, command=self._on_level)
        self.level_slider.set(1.0)
        self.level_slider.pack(side="left", fill="x", expand=True, padx=(4, 8), pady=8)

        # ---- Scene buttons ----
        scene_row = ctk.CTkFrame(self, fg_color="transparent")
        scene_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkButton(scene_row, text="CAPTURE A", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=90, height=26,
                      command=lambda: self._capture_scene("A")).pack(side="left", padx=3)
        ctk.CTkButton(scene_row, text="RECALL A", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=90, height=26,
                      command=lambda: self._recall_scene("A")).pack(side="left", padx=3)
        ctk.CTkButton(scene_row, text="CAPTURE B", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=90, height=26,
                      command=lambda: self._capture_scene("B")).pack(side="left", padx=3)
        ctk.CTkButton(scene_row, text="RECALL B", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=90, height=26,
                      command=lambda: self._recall_scene("B")).pack(side="left", padx=3)
        ctk.CTkLabel(scene_row, text="(A/B pattern değiştir)", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=8)
        ctk.CTkButton(scene_row, text="EXPORT MIX", fg_color=RED, hover_color=RED_HOVER,
                      text_color="#FFF", font=F_META, width=90, height=26,
                      command=lambda: self._export("mix")).pack(side="right", padx=3)
        ctk.CTkButton(scene_row, text="EXPORT STEMS", fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META, width=100, height=26,
                      command=lambda: self._export("stems")).pack(side="right", padx=3)

        # ---- Instrument select ----
        inst_row = ctk.CTkFrame(self, fg_color="transparent")
        inst_row.pack(fill="x", padx=12, pady=(4, 8))
        ctk.CTkLabel(inst_row, text="+ INSTRUMENT:", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        self.inst_var = tk.StringVar(value="kick")
        self.inst_combo = ctk.CTkComboBox(inst_row, values=list_instruments(), variable=self.inst_var,
                                          width=110, height=28, font=F_META)
        self.inst_combo.pack(side="left", padx=(0, 6))
        ctk.CTkButton(inst_row, text="EKLE", fg_color=RED, hover_color=RED_HOVER,
                      text_color="#FFF", font=F_META, width=56, height=28,
                      command=self._add_instrument).pack(side="left")

        # ---- Pattern grid ----
        grid_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        grid_frame.pack(fill="x", padx=12, pady=4)
        self.grid_inner = ctk.CTkFrame(grid_frame, fg_color="transparent")
        self.grid_inner.pack(fill="x", padx=6, pady=6)

        # Step header
        hdr = ctk.CTkFrame(self.grid_inner, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=17, sticky="w")
        ctk.CTkLabel(hdr, text="CHANNEL", font=F_META, text_color=TEXT_DIM, width=90).pack(side="left")
        for s in range(16):
            ctk.CTkLabel(hdr, text=str(s + 1), font=("Consolas", 8), text_color=TEXT_DIM,
                         width=26).pack(side="left")

        self.status_label = ctk.CTkLabel(self, text="", font=F_META, text_color=TEXT_DIM)
        self.status_label.pack(anchor="w", padx=12, pady=(4, 10))

    # ============================================================
    # CHANNELS
    # ============================================================
    def _load_genre(self, genre):
        self.engine.load_genre(genre)
        self.engine.set_bpm(int(self.bpm_slider.get()))
        self._refresh_channels()
        self.set_status(f"{genre} yuklendi")

    def _add_instrument(self):
        name = self.inst_var.get()
        if not name or name in self.engine.channel_names():
            self.set_status(f"{name} zaten var")
            return
        self.engine.add_channel(name)
        self._refresh_channels()
        self.set_status(f"{name} eklendi")

    def _refresh_channels(self):
        for w in self.grid_inner.winfo_children():
            w.destroy()
        self._cell_buttons = {}
        self._channels = self.engine.channel_names()

        hdr = ctk.CTkFrame(self.grid_inner, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=17, sticky="w")
        ctk.CTkLabel(hdr, text="CHANNEL", font=F_META, text_color=TEXT_DIM, width=90).pack(side="left")
        for s in range(16):
            ctk.CTkLabel(hdr, text=str(s + 1), font=("Consolas", 8), text_color=TEXT_DIM,
                         width=26).pack(side="left")

        for r, ch_name in enumerate(self._channels, start=1):
            ch = self.engine.channels[ch_name]
            # Channel label + mute
            lbl = ctk.CTkLabel(self.grid_inner, text=ch_name, font=("Consolas", 9),
                               text_color=BLUE_BRIGHT if ch.inst.category == "melodic" else TEXT_SECONDARY,
                               width=90, anchor="w")
            lbl.grid(row=r, column=0, padx=(0, 4), pady=2, sticky="w")

            btns = []
            for s in range(16):
                on = ch.steps[s] == 1
                btn = ctk.CTkButton(
                    self.grid_inner, text="", width=24, height=22, corner_radius=3,
                    fg_color=GREEN if on else SURFACE_RAISED,
                    hover_color=BORDER, text_color=TEXT_DIM, border_width=1,
                    border_color=GREEN if on else BORDER,
                    command=lambda name=ch_name, idx=s: self._toggle_step(name, idx),
                )
                btn.grid(row=r, column=s + 1, padx=1, pady=2)
                btns.append(btn)
            self._cell_buttons[ch_name] = btns

            # mute toggle
            mbtn = ctk.CTkButton(self.grid_inner, text="M", width=22, height=22, corner_radius=3,
                                 fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=TEXT_DIM,
                                 font=("Consolas", 8), border_width=1, border_color=BORDER,
                                 command=lambda name=ch_name: self._toggle_mute(name))
            mbtn.grid(row=r, column=17, padx=(4, 0), pady=2)

    def _toggle_step(self, name, idx):
        on = self.engine.toggle_step(name, idx)
        btn = self._cell_buttons[name][idx]
        color = GREEN if on else SURFACE_RAISED
        btn.configure(fg_color=color, border_color=color)

    def _toggle_mute(self, name):
        ch = self.engine.channels[name]
        ch.muted = not ch.muted
        self.set_status(f"{name} {'MUTED' if ch.muted else 'ON'}")

    # ============================================================
    # SCENES
    # ============================================================
    def _capture_scene(self, letter):
        self.engine.capture_scene(letter)
        self.set_status(f"Scene {letter} kaydedildi")

    def _recall_scene(self, letter):
        ok = self.engine.recall_scene(letter)
        if ok:
            self._refresh_channels()
            self.set_status(f"Scene {letter} yuklendi")
        else:
            self.set_status(f"Scene {letter} yok — once CAPTURE")

    # ============================================================
    # PLAYBACK
    # ============================================================
    def toggle_play(self):
        if self._running:
            self.stop()
        else:
            self.play()

    def play(self):
        if not HAS_AUDIO:
            self.set_status("sounddevice yok — ses cikisi kullanilamaz")
            return
        # Warm the instrument caches off the UI thread so the first bar
        # doesn't stall playback (cold render can be slow).
        self._warm_cache()

        self._stream_gen = self.engine.iter_stream(self.chunk_size)
        try:
            self._stream = sd.OutputStream(
                samplerate=self.sr, blocksize=self.chunk_size, channels=1,
                dtype="float32", callback=self._audio_callback)
            self._stream.start()
        except Exception as exc:
            self.set_status(f"Audio error: {exc}")
            self._stream = None
            return

        self._running = True
        self.badge.configure(text="PLAYING", text_color=GREEN)
        self.play_btn.configure(text="STOP", fg_color=RED, hover_color=RED_HOVER)

    def _warm_cache(self):
        import threading
        def _warm():
            try:
                # render each channel once to fill plugin caches
                self.engine.render_bar()
            except Exception:
                pass
        threading.Thread(target=_warm, daemon=True).start()

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None
        self.badge.configure(text="STOPPED", text_color=TEXT_DIM)
        self.play_btn.configure(text="PLAY", fg_color=GREEN, hover_color="#3DAE6C")

    def _audio_callback(self, outdata, frames, time_info, status):
        try:
            chunk = next(self._stream_gen)
        except Exception:
            outdata.fill(0)
            return
        n = min(len(chunk), frames)
        outdata[:n, 0] = chunk[:n]
        if n < frames:
            outdata[n:, 0] = 0

    # ============================================================
    # CONTROLS
    # ============================================================
    def _on_bpm(self, value):
        self.engine.set_bpm(int(value))

    def _on_swing(self, value):
        self.engine.set_swing(float(value))

    def _on_level(self, value):
        for ch in self.engine.channels.values():
            ch.level = float(value)

    def set_status(self, text):
        self.status_label.configure(text=text)

    def _export(self, mode):
        import os
        os.makedirs("DJ_EXPORTS", exist_ok=True)
        bars = 4
        if mode == "mix":
            path = self.engine.export_wav("DJ_EXPORTS/live_perf_mix.wav", bars=bars)
            self.set_status(f"MIX exported: {path} ({bars} bar)")
        else:
            paths = self.engine.export_stems("DJ_EXPORTS/live_stems", bars=bars)
            self.set_status(f"STEMS exported: {', '.join(list(paths.keys())[:4])}...")

    # ============================================================
    # STYLE FROM TRACK
    # ============================================================

    def _select_track(self):
        files = filedialog.askopenfilenames(
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a *.aiff *.aif"), ("All", "*.*")])
        if files:
            self._analyze_and_style(files[0])

    def _on_dropped(self, files):
        """windnd drop callback — receives list of paths (bytes on py3)."""
        for f in files:
            p = f.decode("utf-8") if isinstance(f, bytes) else str(f)
            if p.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".aiff", ".aif", ".ogg")):
                self._analyze_and_style(p)
                return
        self.set_status("Desteklenen ses dosyasi yok (mp3/wav/flac/m4a)")

    def _analyze_and_style(self, path):
        """Analyze a track in the background, then build a fresh style."""
        if not os.path.exists(path):
            self.set_status(f"Dosya yok: {os.path.basename(path)}")
            return
        # stop current playback before swapping engines
        self.stop()
        self.style_status.configure(text="Dinleniyor...", text_color=AMBER)
        self.style_result.configure(text=f"🎧 {os.path.basename(path)} analiz ediliyor...")

        def _work():
            try:
                from app.ai.style_generator import StyleGenerator, describe_style
                sg = StyleGenerator(sample_rate=self.sr)
                analysis = sg.analyze_file(path)
                style = sg.generate(analysis)
                engine = sg.build_engine(style=style)
                engine.set_bpm(style["bpm"])
                desc = describe_style(style)

                def _apply():
                    self.engine = engine
                    # sync sliders
                    self.bpm_slider.set(style["bpm"])
                    self.swing_slider.set(style["swing"])
                    self.style_status.configure(text="HAZIR", text_color=GREEN)
                    self.style_result.configure(
                        text=f"🎵 {os.path.basename(path)}\n"
                             f"    {desc}\n"
                             f"    Pattern yeniden yazildi — grid'den duzenleyebilirsin.")
                    self._refresh_channels()
                    # auto-play the new style
                    self.play()
                self.after(0, _apply)
            except Exception as exc:
                def _err():
                    self.style_status.configure(text="HATA", text_color=RED)
                    self.style_result.configure(text=f"Analiz hatasi: {exc}")
                self.after(0, _err)

        threading.Thread(target=_work, daemon=True).start()

    # ============================================================
    # ASTRA STYLE SCENE (setup sahnesi)
    # ============================================================

    def mount_scene(self, scene):
        """Astra mounts a StyleScene onto this panel for playback control."""
        self.style_scene = scene
        scene.mount_engine(self.engine)

        # scene bar
        if hasattr(self, "scene_bar"):
            self.scene_bar.pack_forget()
        scene_bar = ctk.CTkFrame(self, fg_color=BG, corner_radius=6, border_width=1, border_color=BLUE_BRIGHT)
        scene_bar.pack(fill="x", padx=12, pady=(0, 8))
        self.scene_bar = scene_bar

        row = ctk.CTkFrame(scene_bar, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(row, text="🤖 ASTRA SAHNE", font=F_BODY_BOLD, text_color=BLUE_BRIGHT).pack(side="left")

        self.scene_track_label = ctk.CTkLabel(row, text="", font=F_META, text_color=TEXT_SECONDARY)
        self.scene_track_label.pack(side="left", padx=12)

        ctk.CTkButton(row, text="◀", width=34, height=26, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._scene_prev).pack(side="right", padx=2)
        ctk.CTkButton(row, text="▶", width=34, height=26, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._scene_next).pack(side="right", padx=2)

        self.scene_progress = ctk.CTkLabel(scene_bar, text="", font=F_META, text_color=TEXT_DIM)
        self.scene_progress.pack(anchor="w", padx=8, pady=(0, 6))

        self._poll_scene()

    def _poll_scene(self):
        scene = getattr(self, "style_scene", None)
        if scene is None:
            return
        if scene.is_ready():
            self.scene_progress.configure(text=f"{scene.analyzed_count()}/{len(scene.tracks())} parca analiz edildi — HAZIR")
            if not getattr(self, "_scene_autoplayed", False):
                self._scene_autoplayed = True
                self._scene_play_current()
        else:
            self.scene_progress.configure(
                text=f"Analiz ediliyor... {scene.analyzed_count()}/{len(scene.tracks())}"
                     f" ({scene.failed_count()} hata)")
        # update current track label
        cur = scene.current_index()
        if cur >= 0:
            self.scene_track_label.configure(text=scene.current_summary().split(" — ")[0])
        self.after(500, self._poll_scene)

    def _scene_play_current(self):
        scene = getattr(self, "style_scene", None)
        if scene is None:
            return
        idx = scene.current_index()
        if idx < 0:
            idx = 0
            scene.play_index(0)
        else:
            scene.play_index(idx)
        self._refresh_channels()
        self.bpm_slider.set(scene.last_engine.bpm if hasattr(scene, "last_engine") and scene.last_engine else self.engine.bpm)
        self.play()

    def _scene_next(self):
        scene = getattr(self, "style_scene", None)
        if not scene:
            return
        summary = scene.next()
        if summary:
            self._refresh_channels()
            self.play()

    def _scene_prev(self):
        scene = getattr(self, "style_scene", None)
        if not scene:
            return
        summary = scene.prev()
        if summary:
            self._refresh_channels()
            self.play()

    def _toggle_synth_editor(self):
        if getattr(self, "synth_editor", None) is None:
            try:
                from app.ui.synth_editor import SynthEditorPanel
                self.synth_editor = SynthEditorPanel(
                    self, engine=self.engine, on_preview=self.stop, panel=self)
                self.synth_editor.pack(fill="x", padx=12, pady=(0, 8))
            except Exception as exc:
                self.set_status(f"Synth editor hatasi: {exc}")
            return
        if self.synth_editor.winfo_manager():
            self.synth_editor.pack_forget()
        else:
            self.synth_editor.pack(fill="x", padx=12, pady=(0, 8))

    def destroy(self):
        self.stop()
        super().destroy()
