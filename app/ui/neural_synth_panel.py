"""
DJ AI OS — Neural Synth Panel
=============================
Interactive control surface for the neural instrument
(`app.ai.instruments.neural_synth.NeuralSynthPlugin`).

What you can do here that a normal synth can't:
  • MORPH — crossfade two learned timbres in LATENT space (morph_a ⇄ morph_b)
  • VARIATION — z_noise re-imagines the same class into new bodies each hit
  • PITCH — neural timbre is preserved while transposed to any note
  • TRAIN — run scripts/train_neural_timbre.py on your library (background)
  • BEAT — push the neural instrument into a LivePerformanceEngine channel

Wired into MainWindow as view key `neural_synth`.
"""

import os
import subprocess
import threading

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BLUE_BRIGHT,
    F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.instruments import get_instrument

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

SOUND_CLASSES = ["KICK", "BASS", "PLUCK", "ARP"]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
OCTAVE_BASE = [12, 24, 36, 48, 60, 72]


class NeuralSynthPanel(ctk.CTkFrame):
    """Neural timbre instrument — latent morph, variation, preview, beat."""

    def __init__(self, master, engine=None, sample_rate=44100, panel=None,
                 win=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BLUE_BRIGHT)
        self.engine = engine
        self.sr = sample_rate
        self.panel = panel          # LivePerformancePanel (grid refresh)
        self.win = win              # MainWindow (status bar + library access)
        self.plugin = get_instrument("neural_synth", sample_rate=sample_rate)

        self._cur_octave = 2
        self._cur_note = 48
        self._preview_job = None
        self._auto_preview = True
        self._vae_ready = False

        self._build()
        # warm the VAE in a thread so the UI never blocks on first open
        self._warm_vae()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="NEURAL SYNTH", font=F_H3,
                     text_color=BLUE_BRIGHT).pack(side="left")
        self.status_lbl = ctk.CTkLabel(hdr, text="", font=F_META,
                                       text_color=TEXT_DIM)
        self.status_lbl.pack(side="right")

        # ---- sound class (timbre source) ----
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row, text="TINBRE (latent class):", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        self.class_combo = ctk.CTkComboBox(row, values=SOUND_CLASSES,
                                           width=110, height=26, font=F_META,
                                           command=self._on_class)
        self.class_combo.set("BASS")
        self.class_combo.pack(side="left")
        ctk.CTkLabel(row, text="  VAE:", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(8, 4))
        self.vae_lbl = ctk.CTkLabel(row, text="yükleniyor…", font=F_BODY_BOLD,
                                    text_color=RED)
        self.vae_lbl.pack(side="left")

        # ---- latent morph ----
        morph = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        morph.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(morph, text="LATENT MORPH", font=F_META,
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=6,
                                               pady=(6, 0), sticky="w")
        self.morph_a = ctk.CTkComboBox(morph, values=SOUND_CLASSES, width=78,
                                       height=24, font=F_META,
                                       command=lambda v: self._on_morph())
        self.morph_a.set("KICK")
        self.morph_a.grid(row=0, column=1, padx=2, pady=(6, 0))
        self.morph_slider, self.morph_lbl = self._slider_row(
            morph, 2, "MORPH", 0, 100, command=lambda v: self._on_morph())
        self.morph_b = ctk.CTkComboBox(morph, values=SOUND_CLASSES, width=78,
                                       height=24, font=F_META,
                                       command=lambda v: self._on_morph())
        self.morph_b.set("ARP")
        self.morph_b.grid(row=0, column=3, padx=2, pady=(6, 0))

        # ---- neural variation + pitch ----
        var = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        var.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(var, text="NEURAL VARIATION", font=F_META,
                     text_color=TEXT_DIM).grid(row=0, column=0, padx=6,
                                               pady=(6, 0), sticky="w")
        self.noise_slider, self.noise_lbl = self._slider_row(
            var, 1, "Z-NOISE", 0, 100,
            command=lambda v: self._on_param("z_noise", v / 100.0 * 1.5))
        self.pitch_slider, self.pitch_lbl = self._slider_row(
            var, 2, "PITCH", 0, 100,
            command=lambda v: self._on_param("pitch_shift", (v / 100 * 48) - 24))

        # ---- preview keyboard ----
        kb = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        kb.pack(fill="x", padx=10, pady=(2, 2))
        kbh = ctk.CTkFrame(kb, fg_color="transparent")
        kbh.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(kbh, text="PREVIEW", font=F_META,
                     text_color=TEXT_DIM).pack(side="left")
        self.auto_cb = ctk.CTkCheckBox(kbh, text="auto",
                                       variable=ctk.BooleanVar(value=True),
                                       command=self._toggle_auto, font=F_META,
                                       text_color=TEXT_SECONDARY,
                                       fg_color=RED, hover_color=RED_HOVER)
        self.auto_cb.pack(side="left", padx=8)
        ctk.CTkButton(kbh, text="◀", width=30, height=22,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=lambda: self._shift_octave(-1)).pack(side="right",
                                                                   padx=2)
        self.oct_lbl = ctk.CTkLabel(kbh, text="C2", font=F_MONO,
                                    text_color=TEXT_SECONDARY, width=32)
        self.oct_lbl.pack(side="right")
        ctk.CTkButton(kbh, text="▶", width=30, height=22,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=lambda: self._shift_octave(1)).pack(side="right",
                                                                  padx=2)

        kbrow = ctk.CTkFrame(kb, fg_color="transparent")
        kbrow.pack(fill="x", padx=6, pady=(4, 6))
        base = OCTAVE_BASE[self._cur_octave]
        for i, nm in enumerate(NOTE_NAMES):
            note = base + i
            white = "#" not in nm
            ctk.CTkButton(
                kbrow, text=nm, width=44, height=26, corner_radius=3,
                fg_color=BG if white else SURFACE_RAISED,
                hover_color=BLUE_BRIGHT,
                text_color=TEXT_PRIMARY if white else TEXT_SECONDARY,
                font=F_MONO, command=lambda m=note: self._preview_note(m),
            ).pack(side="left", padx=1)

        # ---- train + beat ----
        act = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        act.pack(fill="x", padx=10, pady=(2, 8))
        arow = ctk.CTkFrame(act, fg_color="transparent")
        arow.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(arow, text="🎓 LIBRARY İLE EĞİT",
                      width=130, height=26, fg_color=RED, hover_color=RED_HOVER,
                      text_color="#FFF", font=F_META,
                      command=self._train_library).pack(side="left", padx=(0, 6))
        ctk.CTkButton(arow, text="DEMO WAV ÜRET", width=120, height=26,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._run_demo).pack(side="left", padx=3)
        ctk.CTkButton(arow, text="STOP", width=56, height=26,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._preview_stop).pack(side="left", padx=3)
        ctk.CTkLabel(arow, text="  BEAT KANALI:", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(10, 4))
        self.channel_combo = ctk.CTkComboBox(arow, values=[], width=130,
                                             height=26, font=F_META)
        self.channel_combo.pack(side="left")
        ctk.CTkButton(arow, text="ADD CHANNEL", width=104, height=26,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      font=F_META, command=self._add_channel).pack(side="left",
                                                                   padx=3)
        self._refresh_channel_list()

    def _slider_row(self, parent, col, label, lo, hi, command):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, padx=4, pady=(4, 6), sticky="w")
        ctk.CTkLabel(f, text=label, font=("Consolas", 8), text_color=TEXT_DIM,
                     width=52).pack(side="left")
        s = ctk.CTkSlider(f, from_=lo, to=hi, number_of_steps=hi - lo,
                          width=110, height=14, command=command)
        s.pack(side="left", padx=3)
        val = ctk.CTkLabel(f, text="", font=("Consolas", 8),
                           text_color=TEXT_SECONDARY, width=48)
        val.pack(side="left")
        s._val_lbl = val
        return s, val

    # ============================================================
    # BACKEND
    # ============================================================
    def _warm_vae(self):
        """Load/train the VAE off the UI thread so the panel opens fast."""
        def _w():
            ok = self.plugin.ensure_vae()
            self.after(0, lambda: self._vae_ready_changed(ok))
        threading.Thread(target=_w, daemon=True).start()

    def _vae_ready_changed(self, ok):
        self._vae_ready = ok
        self.vae_lbl.configure(text="HAZIR" if ok else "N/A",
                               text_color=RED if ok else TEXT_DIM)
        if ok:
            self._schedule_preview()

    # ============================================================
    # PARAM WIRING
    # ============================================================
    def _on_class(self, name):
        self._on_param("timbre_src", SOUND_CLASSES.index(name))
        self._on_param("morph_amount", 0.0)

    def _on_morph(self):
        amt = float(self.morph_slider.get()) / 100.0
        self.morph_lbl.configure(text=f"{amt:.2f}")
        self.plugin.set_param("morph_amount", amt)
        self.plugin.set_param("morph_a", SOUND_CLASSES.index(self.morph_a.get()))
        self.plugin.set_param("morph_b", SOUND_CLASSES.index(self.morph_b.get()))
        self._schedule_preview()

    def _on_param(self, key, value):
        try:
            self.plugin.set_param(key, float(value))
        except Exception:
            return
        self._schedule_preview()

    def _toggle_auto(self):
        self._auto_preview = self.auto_cb.get()

    def _schedule_preview(self):
        if self._preview_job:
            try:
                self.after_cancel(self._preview_job)
            except Exception:
                pass
        if self._auto_preview and HAS_AUDIO and self._vae_ready:
            self._preview_job = self.after(140,
                                           lambda: self._preview_note(self._cur_note))

    # ============================================================
    # PREVIEW
    # ============================================================
    def _shift_octave(self, delta):
        self._cur_octave = max(0, min(5, self._cur_octave + delta))
        self.oct_lbl.configure(text=f"C{self._cur_octave}")
        self._preview_note(OCTAVE_BASE[self._cur_octave])

    def _preview_note(self, midi):
        self._cur_note = midi
        if not HAS_AUDIO:
            self._set_status("sounddevice yok — preview kapali")
            return
        try:
            if getattr(self, "on_preview", None):
                self.on_preview()
            sig = self.plugin.hit(note=midi, velocity=1.0)
            sd.stop()
            sd.play(sig, self.sr)
        except Exception as exc:
            self._set_status(f"preview hata: {exc}")

    def _preview_stop(self):
        if HAS_AUDIO:
            try:
                sd.stop()
            except Exception:
                pass

    # ============================================================
    # BEAT CHANNEL INTEGRATION
    # ============================================================
    def _refresh_channel_list(self):
        if not self.engine:
            return
        names = [n for n in self.engine.channel_names() if "neural" in n]
        if names:
            self.channel_combo.configure(values=names)
            self.channel_combo.set(names[0])
        else:
            self.channel_combo.configure(values=["(ekle)"])

    def _add_channel(self):
        if not self.engine:
            self._set_status("engine yok")
            return
        name = "neural_synth"
        base = name
        i = 2
        while name in self.engine.channel_names():
            name = f"{base}_{i}"
            i += 1
        ch = self.engine.add_channel(name, note_root=36, note_octave=1)
        # the neural instrument is already on this panel; copy its params
        ch.inst.set_param("timbre_src", self.plugin.get_params()["timbre_src"])
        ch.inst.set_param("z_noise", self.plugin.get_params()["z_noise"])
        ch.set_pattern([1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0])
        self._refresh_channel_list()
        if self.panel:
            try:
                self.panel._refresh_channels()
            except Exception:
                pass
        self._set_status(f"kanal eklendi: {name}")

    # ============================================================
    # TRAIN + DEMO (background subprocesses)
    # ============================================================
    def _train_library(self):
        self._set_status("EĞİTİM BAŞLADI (arka plan)…")
        if self.win:
            try:
                self.win.set_status("NEURAL EĞİTİM: kütüphaneden öğreniliyor…")
            except Exception:
                pass

        def _run():
            folder = None
            if self.win and getattr(self.win, "music_folder", None):
                folder = self.win.music_folder
            cmd = [sys_exe(), "scripts/train_neural_timbre.py"]
            if folder and os.path.isdir(folder):
                cmd += ["--folder", folder]
            try:
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=1200)
                tail = (r.stdout or r.stderr or "")[-160:]
                self.after(0, lambda: self._set_status(
                    f"EĞİTİM: {'tamam' if r.returncode == 0 else 'hata'} | {tail}"))
            except Exception as e:
                self.after(0, lambda: self._set_status(f"EĞİTİM HATASI: {e}"))
        threading.Thread(target=_run, daemon=True).start()

    def _run_demo(self):
        self._set_status("DEMO WAV ÜRETİLİYOR…")
        threading.Thread(target=_run_demo_proc, daemon=True).start()

    # ============================================================
    def _set_status(self, text):
        self.status_lbl.configure(text=text)

    def on_close(self):
        self._preview_stop()


def sys_exe():
    return os.path.join(os.path.dirname(sys_executable_help()), "python.exe") \
        if hasattr(os, "sys") else None


def sys_executable_help():
    import sys
    return sys.executable


def _run_demo_proc():
    import sys
    try:
        r = subprocess.run([sys.executable, "scripts/demo_neural_synth.py"],
                           capture_output=True, text=True, timeout=600)
    except Exception:
        pass
