"""
DJ AI OS — Neural Bridge Panel
==============================
Pick two tracks from your library. The bridge pulls a few timbral-DNA
windows out of each, then renders a beat-synced line whose sound slides
from Track A to Track B — a transition where the *audio itself* morphs,
not just a volume fade.

    A ------------✕~~~~~~~~~~~~~~~✕------------ B
         pure A        never-before     pure B
                        middle
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BLUE_BRIGHT,
    F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.neural_bridge import NeuralBridge

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

AUDIO_EXT = (".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aiff", ".aif")


class NeuralBridgePanel(ctk.CTkFrame):
    """Two-track timbre bridge — analyze, render, play, export."""

    def __init__(self, master, win=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BLUE_BRIGHT)
        self.win = win
        self.bridge = NeuralBridge()
        self._track_map = {}        # label -> path
        self._busy = False
        self._auto_render = False

        self._build()
        self._load_library()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="NEURAL BRIDGE", font=F_H3,
                     text_color=BLUE_BRIGHT).pack(side="left")
        ctk.CTkLabel(hdr, text="iki şarkı → tek ses kimliği",
                     font=F_META, text_color=TEXT_DIM).pack(side="left", padx=8)
        self.status_lbl = ctk.CTkLabel(hdr, text="", font=F_META,
                                       text_color=TEXT_DIM)
        self.status_lbl.pack(side="right")

        # ---- track selection ----
        sel = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        sel.pack(fill="x", padx=10, pady=2)

        def _row(parent, r, label, key):
            ctk.CTkLabel(parent, text=label, font=F_BODY_BOLD,
                         text_color=RED, width=34).grid(row=r, column=0,
                                                        padx=8, pady=4,
                                                        sticky="w")
            combo = ctk.CTkComboBox(parent, values=[], width=280, height=26,
                                    font=F_META, command=self._on_track_change)
            combo.grid(row=r, column=1, padx=2, pady=4, sticky="ew")
            ctk.CTkButton(parent, text="⋯", width=32, height=26,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=lambda k=key: self._browse(k)).grid(
                              row=r, column=2, padx=4, pady=4)
            setattr(self, f"track_{key}", combo)
            setattr(self, f"path_{key}", None)

        _row(sel, 0, "A", "a")
        _row(sel, 1, "B", "b")
        sel.columnconfigure(1, weight=1)

        # ---- transport / bridge controls ----
        ctl = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        ctl.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(ctl, text="KÖPRÜ", font=F_META,
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=6,
                                               pady=(6, 0), sticky="w")

        self.bpm_slider, self.bpm_lbl = self._slider_row(
            ctl, 1, "BPM", 90, 180, "128",
            lambda v: self.bpm_lbl.configure(text=f"{int(float(v))}"))
        self.bars_slider, self.bars_lbl = self._slider_row(
            ctl, 2, "BARS", 2, 8, "4",
            lambda v: self.bars_lbl.configure(text=f"{int(float(v))}"))
        self.semis_slider, self.semis_lbl = self._slider_row(
            ctl, 3, "ANAHTAR", -12, 12, "0",
            lambda v: self.semis_lbl.configure(
                text=f"{'+' if float(v) >= 0 else ''}{int(float(v))}st"))
        self.spread_slider, self.spread_lbl = self._slider_row(
            ctl, 4, "GEÇİŞ", 10, 90, "50",
            lambda v: self.spread_lbl.configure(text=f"{int(float(v))}%"))
        self.spread_slider.set(50)

        # ---- actions ----
        act = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        act.pack(fill="x", padx=10, pady=(2, 8))
        arow = ctk.CTkFrame(act, fg_color="transparent")
        arow.pack(fill="x", padx=6, pady=6)
        self.btn_analyze = ctk.CTkButton(
            arow, text="🧬 ANALİZ ET", width=112, height=28,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            text_color=TEXT_SECONDARY, font=F_BODY_BOLD,
            command=self._analyze).pack(side="left", padx=(0, 6))
        self.btn_render = ctk.CTkButton(
            arow, text="▶ KÖPRÜYÜ ÇAL", width=132, height=28,
            fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
            font=F_BODY_BOLD, command=self._render_play).pack(side="left",
                                                              padx=3)
        self.btn_stop = ctk.CTkButton(
            arow, text="STOP", width=52, height=28,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            text_color=TEXT_SECONDARY, font=F_META,
            command=self._stop).pack(side="left", padx=3)
        ctk.CTkButton(
            arow, text="💾 EXPORT WAV", width=112, height=28,
            fg_color=SURFACE_RAISED, hover_color=BORDER,
            text_color=TEXT_SECONDARY, font=F_META,
            command=self._export).pack(side="left", padx=3)
        self.info_lbl = ctk.CTkLabel(arow, text="", font=("Consolas", 8),
                                     text_color=BLUE_BRIGHT, justify="left")
        self.info_lbl.pack(side="right", padx=6)

    def _slider_row(self, parent, col, label, lo, hi, init, command):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, padx=4, pady=(4, 6), sticky="w")
        ctk.CTkLabel(f, text=label, font=("Consolas", 8), text_color=TEXT_DIM,
                     width=52).pack(side="left")
        s = ctk.CTkSlider(f, from_=lo, to=hi, width=100, height=14,
                          command=command)
        s.set(float(init))
        s.pack(side="left", padx=3)
        val = ctk.CTkLabel(f, text=str(init), font=("Consolas", 8),
                           text_color=TEXT_SECONDARY, width=40)
        val.pack(side="left")
        s._val_lbl = val
        return s, val

    # ============================================================
    # LIBRARY / FILES
    # ============================================================
    def _load_library(self):
        tracks = []
        if self.win and getattr(self.win, "library", None):
            tracks = self.win.library
        elif self.win and getattr(self.win, "saved_tracks", None):
            tracks = self.win.saved_tracks
        labels = []
        for t in tracks:
            p = t.get("path")
            if p and p.lower().endswith(AUDIO_EXT) and os.path.isfile(p):
                label = t.get("name") or os.path.basename(p)
                self._track_map[label] = p
                labels.append(label)
        # dedupe by path, keep first label
        seen = set()
        uniq = []
        for lab in labels:
            if self._track_map[lab] not in seen:
                seen.add(self._track_map[lab])
                uniq.append(lab)
        if uniq:
            self.track_a.configure(values=uniq)
            self.track_b.configure(values=uniq)
            self.track_a.set(uniq[0])
            self.track_b.set(uniq[1] if len(uniq) > 1 else uniq[0])
            self.path_a = self._track_map[uniq[0]]
            self.path_b = self._track_map[uniq[1] if len(uniq) > 1 else uniq[0]]
            self._set_status(f"{len(uniq)} şarkı kütüphaneden yüklendi")
        else:
            self._set_status("kütüphane boş — ⋯ ile dosya seç")

    def _on_track_change(self, _value):
        self.path_a = self._track_map.get(self.track_a.get())
        self.path_b = self._track_map.get(self.track_b.get())

    def _browse(self, key):
        path = filedialog.askopenfilename(
            parent=self, title=f"Track {key.upper()} seç",
            filetypes=[("Ses", "*.wav *.flac *.mp3 *.ogg *.m4a *.aiff"),
                       ("Tüm dosyalar", "*.*")])
        if not path:
            return
        setattr(self, f"path_{key}", path)
        getattr(self, f"track_{key}").set(os.path.basename(path))
        self._set_status(f"{key.upper()}: {os.path.basename(path)}")

    # ============================================================
    # ACTIONS
    # ============================================================
    def _analyze(self):
        if self._busy:
            return
        if not (self.path_a and self.path_b):
            self._set_status("önce A ve B şarkılarını seç")
            return
        self._busy = True
        self._set_status("tını DNA'sı çıkarılıyor…")
        self._stop()

        def _run():
            try:
                info = self.bridge.analyze(self.path_a, self.path_b)
                msg = (f"A: {self.bridge.name_a} ({info['reps_a']} pencere) | "
                       f"B: {self.bridge.name_b} ({info['reps_b']} pencere)")
                self.after(0, lambda: self._set_status(msg))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"ANALİZ HATASI: {exc}"))
            finally:
                self._busy = False
                if self._auto_render:
                    self._auto_render = False
                    self.after(50, self._render_play)
        threading.Thread(target=_run, daemon=True).start()

    def _render_play(self):
        if self._busy:
            return
        if not (self.path_a and self.path_b):
            self._set_status("önce her iki şarkıyı da seç")
            return
        if not (self.bridge.reps_a and self.bridge.reps_b):
            # not analyzed yet — analyze first, then auto-render
            self._auto_render = True
            self._analyze()
            return
        self._busy = True
        self._set_status("köprü render ediliyor…")
        self._stop()

        bpm = int(self.bpm_slider.get())
        bars = int(self.bars_slider.get())
        semis = int(self.semis_slider.get())
        spread = float(self.spread_slider.get()) / 100.0

        def _run():
            try:
                audio = self.bridge.render(bpm=bpm, bars=bars,
                                           root_semis=semis, spread=spread)
                if HAS_AUDIO:
                    sd.stop()
                    sd.play(audio, self.bridge.sr)
                dur = self.bridge.render_seconds
                self.after(0, lambda: self._set_status(
                    f"▶ {self.bridge.name_a} → {self.bridge.name_b} | "
                    f"{bpm} BPM · {bars} bar · {dur:.1f}s"))
            except Exception as exc:
                self.after(0, lambda: self._set_status(f"RENDER HATASI: {exc}"))
            finally:
                self._busy = False
        threading.Thread(target=_run, daemon=True).start()

    def _stop(self):
        if HAS_AUDIO:
            try:
                sd.stop()
            except Exception:
                pass

    def _export(self):
        if self.bridge.audio is None:
            self._set_status("önce köprüyü çal (render olması lazım)")
            return
        out_dir = os.path.join("DJ_EXPORTS", "neural_bridge")
        os.makedirs(out_dir, exist_ok=True)
        stem = (f"{os.path.splitext(self.bridge.name_a)[0]}_to_"
                f"{os.path.splitext(self.bridge.name_b)[0]}")
        out = os.path.join(out_dir, f"bridge_{stem}.wav")
        import soundfile as sf
        sf.write(out, self.bridge.audio, self.bridge.sr)
        self._set_status(f"💾 kaydedildi: {out}")

    # ============================================================
    def _set_status(self, text):
        self.status_lbl.configure(text=text)

    def on_close(self):
        self._stop()
