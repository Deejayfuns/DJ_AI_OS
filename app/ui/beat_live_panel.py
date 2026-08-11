"""
DJ AI OS — Beat Live Panel (Real-time)

Live beat generation with real-time controls + live analysis.
Connects BeatStudio streaming engine to RealtimeAIEar.

Controls:
- Start/Stop live stream
- Master volume / filter / BPM / swing sliders
- Live analysis readout (BPM, key, energy, vocal)
"""

import threading
import time
import tkinter as tk

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False


class BeatLivePanel(ctk.CTkFrame):
    """
    Real-time beat production panel.
    Plays infinite beat stream through sounddevice with live parameter
    control and on-screen AI analysis.
    """

    def __init__(self, master, beat_studio=None, ai_ear=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)

        from app.ai.beat_studio import BeatStudio
        from app.ai.ai_ear_realtime import RealtimeAIEar

        self.beat_studio = beat_studio or BeatStudio()
        self.ai_ear = ai_ear or RealtimeAIEar(sample_rate=44100, chunk_size=1024,
                                              buffer_seconds=2.0, analysis_interval=4)

        self.sample_rate = 44100
        self.chunk_size = 1024

        # Stream state
        self._stream = None
        self._stream_gen = None
        self._running = False
        self._live_command = "128 BPM house beat"

        # UI state
        self._poll_job = None

        self._build()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(header, text="LIVE MODE", font=F_H3, text_color=RED).pack(side="left")
        self.live_badge = ctk.CTkLabel(header, text="STOPPED", font=F_MONO, text_color=TEXT_DIM,
                                       fg_color=BG, corner_radius=3, padx=8, pady=2)
        self.live_badge.pack(side="right")

        # ---- Command row ----
        cmd_row = ctk.CTkFrame(self, fg_color="transparent")
        cmd_row.pack(fill="x", padx=12, pady=(4, 8))

        self.cmd_entry = ctk.CTkEntry(cmd_row, placeholder_text="128 BPM tech house beat",
                                      font=F_BODY, fg_color=BG, border_color=BORDER)
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.start_btn = ctk.CTkButton(cmd_row, text="PLAY", fg_color=GREEN, hover_color="#3DAE6C",
                                       text_color="#FFF", font=F_BODY_BOLD, width=90,
                                       command=self.toggle_play)
        self.start_btn.pack(side="left")

        # ---- Controls ----
        ctrl = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        ctrl.pack(fill="x", padx=12, pady=4)

        # Row 1: master volume, filter
        row1 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(row1, text="VOL", font=F_META, text_color=TEXT_DIM, width=30).pack(side="left")
        self.vol_slider = ctk.CTkSlider(row1, from_=0, to=1.5, number_of_steps=60,
                                        command=self._on_volume)
        self.vol_slider.set(1.0)
        self.vol_slider.pack(side="left", fill="x", expand=True, padx=(4, 12))

        ctk.CTkLabel(row1, text="FILTER", font=F_META, text_color=TEXT_DIM, width=45).pack(side="left")
        self.filter_slider = ctk.CTkSlider(row1, from_=100, to=20000, number_of_steps=100,
                                           command=self._on_filter)
        self.filter_slider.set(20000)
        self.filter_slider.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Row 2: BPM, swing
        row2 = ctk.CTkFrame(ctrl, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkLabel(row2, text="BPM", font=F_META, text_color=TEXT_DIM, width=30).pack(side="left")
        self.bpm_slider = ctk.CTkSlider(row2, from_=60, to=180, number_of_steps=120,
                                        command=self._on_bpm)
        self.bpm_slider.set(128)
        self.bpm_slider.pack(side="left", fill="x", expand=True, padx=(4, 12))

        ctk.CTkLabel(row2, text="SWING", font=F_META, text_color=TEXT_DIM, width=45).pack(side="left")
        self.swing_slider = ctk.CTkSlider(row2, from_=0, to=0.5, number_of_steps=50,
                                          command=self._on_swing)
        self.swing_slider.set(0.1)
        self.swing_slider.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ---- Live analysis readout ----
        analysis = ctk.CTkFrame(self, fg_color="transparent")
        analysis.pack(fill="x", padx=12, pady=(8, 4))

        self.bpm_label = self._metric(analysis, "BPM", "--")
        self.key_label = self._metric(analysis, "KEY", "--")
        self.energy_label = self._metric(analysis, "ENERGY", "--")
        self.vocal_label = self._metric(analysis, "VOCAL", "--")

        # Status line
        self.status_label = ctk.CTkLabel(self, text="Sesi duymak icin PLAY'e basin. (sounddevice)",
                                         font=F_META, text_color=TEXT_DIM)
        self.status_label.pack(anchor="w", padx=12, pady=(4, 10))

    def _metric(self, parent, title, value):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=4)
        box.pack(side="left", fill="x", expand=True, padx=3)
        ctk.CTkLabel(box, text=title, font=F_META, text_color=TEXT_DIM).pack(pady=(6, 0))
        lbl = ctk.CTkLabel(box, text=value, font=F_MONO, text_color=GREEN)
        lbl.pack(pady=(0, 6))
        return lbl

    # ============================================================
    # PLAYBACK CONTROL
    # ============================================================
    def toggle_play(self):
        if self._running:
            self.stop()
        else:
            self.play()

    def play(self):
        if not HAS_AUDIO:
            self.status_label.configure(text="sounddevice yok — ses cikisi kullanilamaz.")
            return

        cmd = self.cmd_entry.get().strip() or self._live_command
        self._live_command = cmd

        self._stream_gen = self.beat_studio.generate_stream(cmd, self.chunk_size)

        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            self.status_label.configure(text=f"Audio error: {exc}")
            self._stream = None
            return

        # Start AI ear
        self.ai_ear.start()

        self._running = True
        self.live_badge.configure(text="PLAYING", text_color=GREEN)
        self.start_btn.configure(text="STOP", fg_color=RED, hover_color=RED_HOVER)
        self.status_label.configure(text=f"CANLI: {cmd}")
        self._poll()

    def stop(self):
        self._running = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self.beat_studio.stop_stream()
        self.ai_ear.stop()

        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

        self.live_badge.configure(text="STOPPED", text_color=TEXT_DIM)
        self.start_btn.configure(text="PLAY", fg_color=GREEN, hover_color="#3DAE6C")
        self.status_label.configure(text="Durduruldu.")

    def _audio_callback(self, outdata, frames, time_info, status):
        try:
            chunk = next(self._stream_gen).astype("float32")
        except StopIteration:
            outdata.fill(0)
            return
        except Exception:
            outdata.fill(0)
            return

        n = min(len(chunk), frames)
        outdata[:n, 0] = chunk[:n]
        if n < frames:
            outdata[n:, 0] = 0

        # Feed to AI ear for live analysis
        self.ai_ear.process_chunk(chunk[:n])

    # ============================================================
    # PARAMETER CALLBACKS
    # ============================================================
    def _on_volume(self, value):
        self.beat_studio.set_master_volume(float(value))

    def _on_filter(self, value):
        self.beat_studio.set_global_filter(float(value))

    def _on_bpm(self, value):
        self.beat_studio.set_bpm(int(value))

    def _on_swing(self, value):
        self.beat_studio.set_swing(float(value))

    # ============================================================
    # ANALYSIS POLLING
    # ============================================================
    def _poll(self):
        if not self._running:
            return

        a = self.ai_ear.get_current()
        if a.rms_energy > 0:
            self.bpm_label.configure(text=f"{a.bpm:.0f}" if a.bpm else "--")
            self.key_label.configure(text=a.key)
            self.energy_label.configure(text=f"{a.rms_energy:.2f}")
            self.vocal_label.configure(text="EVET" if a.vocal_present else "HAYIR")

        self._poll_job = self.after(500, self._poll)

    def destroy(self):
        """Cleanup on close."""
        self.stop()
        super().destroy()
