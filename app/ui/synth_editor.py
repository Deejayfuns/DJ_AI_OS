"""
DJ AI OS — Synth Editor (Serum/Nexus-style)

A professional 2-oscillator synthesizer editor. Design basses, kicks,
leads and pads from scratch:

    OSC1 + OSC2 -> FILTER -> ADSR -> DRIVE

- Live preview through sounddevice (non-blocking, debounced)
- Factory presets + save/load to DJ_EXPORTS/patches/
- Push the designed sound into a LivePerformanceEngine channel
  (ADD CHANNEL) or retune an existing channel (SEND TO CHANNEL)
"""

import os
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, BORDER_LIGHT, RED, RED_HOVER,
    GREEN, BLUE_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.instruments import get_instrument
from app.ai.instruments.synth_patch import (
    WAVES, FILTERS, PATCH_PRESETS, save_patch, load_patch, list_patches,
    PATCH_DIR,
)

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

# base octave MIDI notes (C0..C5), default preview C3
OCTAVE_BASE = [12, 24, 36, 48, 60, 72]
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class SynthEditorPanel(ctk.CTkFrame):
    """Serum-style 2-osc patch synth editor."""

    def __init__(self, master, engine=None, sample_rate=44100, on_preview=None,
                 panel=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BLUE_BRIGHT)
        self.engine = engine
        self.sr = sample_rate
        self.on_preview = on_preview or (lambda: None)
        self.panel = panel  # LivePerformancePanel (for grid refresh)
        self.plugin = get_instrument("synth_patch", sample_rate=sample_rate)

        self._cur_octave = 2  # C3
        self._cur_note = 60   # C4-ish preview
        self._preview_job = None
        self._auto_preview = True

        self._build()
        self.plugin.set_patch(PATCH_PRESETS["acid_bass"])
        self._refresh_controls()
        self._refresh_patch_list()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        # ---- header ----
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="SYNTH EDITOR", font=F_H3, text_color=BLUE_BRIGHT).pack(side="left")
        self.status_lbl = ctk.CTkLabel(hdr, text="", font=F_META, text_color=TEXT_DIM)
        self.status_lbl.pack(side="right")

        # patch name + save/load/preset
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row, text="PATCH:", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=(0, 4))
        self.name_entry = ctk.CTkEntry(row, width=150, height=26, font=F_META)
        self.name_entry.insert(0, "my_bass")
        self.name_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(row, text="SAVE", width=52, height=26, fg_color=RED, hover_color=RED_HOVER,
                      text_color="#FFF", font=F_META, command=self._save).pack(side="left", padx=2)
        self.load_combo = ctk.CTkComboBox(row, values=[], width=120, height=26, font=F_META)
        self.load_combo.pack(side="left", padx=(6, 2))
        ctk.CTkButton(row, text="LOAD", width=52, height=26, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META,
                      command=self._load).pack(side="left", padx=2)
        ctk.CTkLabel(row, text="PRESET:", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=(12, 4))
        self.preset_combo = ctk.CTkComboBox(row, values=list(PATCH_PRESETS.keys()),
                                            width=120, height=26, font=F_META,
                                            command=self._on_preset)
        self.preset_combo.set("acid_bass")
        self.preset_combo.pack(side="left", padx=(0, 6))

        # ---- oscillator sections ----
        self._build_osc_section("OSC 1", 0)
        self._build_osc_section("OSC 2", 1)

        # ---- filter ----
        flt = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        flt.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(flt, text="FILTER", font=F_META, text_color=TEXT_DIM).grid(
            row=0, column=0, padx=6, pady=(6, 0), sticky="w")
        self.filter_type = ctk.CTkComboBox(flt, values=[f.upper() for f in FILTERS],
                                           width=56, height=24, font=F_META,
                                           command=self._on_filter_type)
        self.filter_type.set("LP")
        self.filter_type.grid(row=0, column=1, padx=4, pady=(6, 0))
        self.cutoff_slider, self.cutoff_lbl = self._slider_row(
            flt, 2, "CUTOFF", 0, 1000, command=self._on_cutoff)
        self.res_slider, self.res_lbl = self._slider_row(
            flt, 3, "RES", 0, 100, command=self._on_res)

        # ---- env ----
        env = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        env.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(env, text="ENV", font=F_META, text_color=TEXT_DIM).grid(
            row=0, column=0, padx=6, pady=(6, 0), sticky="w")
        self.attack_slider, self.attack_lbl = self._slider_row(
            env, 1, "A", 1, 100, command=lambda v: self._on_param("env_a", v / 100 * 2.0))
        self.decay_slider, self.decay_lbl = self._slider_row(
            env, 2, "D", 1, 100, command=lambda v: self._on_param("env_d", v / 100 * 3.0))
        self.sustain_slider, self.sustain_lbl = self._slider_row(
            env, 3, "S", 0, 100, command=lambda v: self._on_param("env_s", v / 100))
        self.release_slider, self.release_lbl = self._slider_row(
            env, 4, "R", 1, 100, command=lambda v: self._on_param("env_r", v / 100 * 3.0))
        self.pitch_slider, self.pitch_lbl = self._slider_row(
            env, 5, "PITCH", 0, 100,
            command=lambda v: self._on_param("pitch_amt", (v / 100 * 96) - 48))

        # ---- drive / level ----
        out = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        out.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(out, text="OUT", font=F_META, text_color=TEXT_DIM).grid(
            row=0, column=0, padx=6, pady=(6, 0), sticky="w")
        self.drive_slider, self.drive_lbl = self._slider_row(
            out, 1, "DRIVE", 0, 100, command=lambda v: self._on_param("drive", 1 + v / 100 * 7))
        self.level_slider, self.level_lbl = self._slider_row(
            out, 2, "LEVEL", 0, 100, command=lambda v: self._on_param("level", v / 100))

        # ---- preview keyboard ----
        kb = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        kb.pack(fill="x", padx=10, pady=(2, 2))
        kbh = ctk.CTkFrame(kb, fg_color="transparent")
        kbh.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(kbh, text="PREVIEW", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.auto_cb = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(kbh, text="auto", variable=self.auto_cb, command=self._toggle_auto,
                        font=F_META, text_color=TEXT_SECONDARY,
                        fg_color=RED, hover_color=RED_HOVER).pack(side="left", padx=8)
        ctk.CTkButton(kbh, text="◀", width=30, height=22, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META,
                      command=lambda: self._shift_octave(-1)).pack(side="right", padx=2)
        self.oct_lbl = ctk.CTkLabel(kbh, text="C3", font=F_MONO, text_color=TEXT_SECONDARY, width=32)
        self.oct_lbl.pack(side="right")
        ctk.CTkButton(kbh, text="▶", width=30, height=22, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META,
                      command=lambda: self._shift_octave(1)).pack(side="right", padx=2)

        # note keys
        kbrow = ctk.CTkFrame(kb, fg_color="transparent")
        kbrow.pack(fill="x", padx=6, pady=(4, 6))
        base = OCTAVE_BASE[self._cur_octave]
        for i, nm in enumerate(NOTE_NAMES):
            note = base + i
            white = "#" in nm
            ctk.CTkButton(
                kbrow, text=nm, width=44, height=26, corner_radius=3,
                fg_color=BG if white else SURFACE_RAISED,
                hover_color=BLUE_BRIGHT, text_color=TEXT_PRIMARY if white else TEXT_SECONDARY,
                font=F_MONO, command=lambda m=note: self._preview_note(m),
            ).pack(side="left", padx=1)

        # ---- send / channel ----
        send = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        send.pack(fill="x", padx=10, pady=(2, 8))
        srow = ctk.CTkFrame(send, fg_color="transparent")
        srow.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(srow, text="BEAT KANALI:", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.channel_combo = ctk.CTkComboBox(srow, values=[], width=150, height=26, font=F_META)
        self.channel_combo.pack(side="left", padx=6)
        ctk.CTkButton(srow, text="ADD CHANNEL", width=110, height=26, fg_color=RED,
                      hover_color=RED_HOVER, text_color="#FFF", font=F_META,
                      command=self._add_channel).pack(side="left", padx=3)
        ctk.CTkButton(srow, text="SEND TO CHANNEL", width=130, height=26, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META,
                      command=self._send_to_channel).pack(side="left", padx=3)
        ctk.CTkButton(srow, text="STOP", width=56, height=26, fg_color=SURFACE_RAISED,
                      hover_color=BORDER, text_color=TEXT_SECONDARY, font=F_META,
                      command=self._preview_stop).pack(side="left", padx=3)
        self._refresh_channel_list()

    def _build_osc_section(self, label, idx):
        fr = ctk.CTkFrame(self, fg_color=BG, corner_radius=6)
        fr.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(fr, text=label, font=F_META, text_color=BLUE_BRIGHT).grid(
            row=0, column=0, padx=6, pady=(6, 0), sticky="w")
        pref = "osc1" if idx == 0 else "osc2"
        self._osc_waves = getattr(self, "_osc_waves", [])
        wave = ctk.CTkComboBox(fr, values=WAVES, width=70, height=24, font=F_META,
                               command=lambda v, k=pref: self._on_wave(k, v))
        wave.set("saw")
        wave.grid(row=0, column=1, padx=4, pady=(6, 0))
        setattr(self, f"{pref}_wave", wave)
        setattr(self, f"{pref}_coarse_slider", self._slider_row(
            fr, 2, "COARSE", -24, 24, command=lambda v, k=pref: self._on_param(f"{k}_coarse", v))[0])
        setattr(self, f"{pref}_detune_slider", self._slider_row(
            fr, 3, "DETUNE", -50, 50, command=lambda v, k=pref: self._on_param(f"{k}_detune", v))[0])
        setattr(self, f"{pref}_level_slider", self._slider_row(
            fr, 4, "LEVEL", 0, 100, command=lambda v, k=pref: self._on_param(f"{k}_level", v / 100))[0])

    def _slider_row(self, parent, col, label, lo, hi, command):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, padx=4, pady=(4, 6), sticky="w")
        ctk.CTkLabel(f, text=label, font=("Consolas", 8), text_color=TEXT_DIM, width=48).pack(side="left")
        s = ctk.CTkSlider(f, from_=lo, to=hi, number_of_steps=hi - lo, width=110, height=14,
                          command=command)
        s.pack(side="left", padx=3)
        val = ctk.CTkLabel(f, text="", font=("Consolas", 8), text_color=TEXT_SECONDARY, width=48)
        val.pack(side="left")
        s._val_lbl = val
        s._label = label
        return s, val

    # ============================================================
    # PARAM WIRING
    # ============================================================
    def _on_wave(self, pref, wave):
        self._on_param(f"{pref}_wave", WAVES.index(wave))

    def _on_filter_type(self, ft):
        self._on_param("filter_type", FILTERS.index(ft.lower()))

    def _on_cutoff(self, pos):
        # log-space: 30 Hz .. 16 kHz
        cutoff = 30.0 * (16000.0 / 30.0) ** (float(pos) / 1000.0)
        self._on_param("filter_cutoff", cutoff)
        if hasattr(self, "cutoff_lbl"):
            self.cutoff_lbl.configure(text=f"{int(cutoff)} Hz")

    def _on_res(self, pos):
        self._on_param("filter_res", float(pos) / 100.0)
        if hasattr(self, "res_lbl"):
            self.res_lbl.configure(text=f"{float(pos) / 100.0:.2f}")

    def _on_param(self, key, value):
        try:
            self.plugin.set_param(key, float(value))
        except Exception:
            return
        # update value label if it's a slider bound row
        self._schedule_preview()

    def _toggle_auto(self):
        self._auto_preview = self.auto_cb.get()

    def _schedule_preview(self):
        if self._preview_job:
            try:
                self.after_cancel(self._preview_job)
            except Exception:
                pass
        if self._auto_preview and HAS_AUDIO:
            self._preview_job = self.after(120, lambda: self._preview_note(self._cur_note))

    # ============================================================
    # PREVIEW
    # ============================================================
    def _shift_octave(self, delta):
        self._cur_octave = max(0, min(5, self._cur_octave + delta))
        self.oct_lbl.configure(text=f"C{self._cur_octave}")
        base = OCTAVE_BASE[self._cur_octave]
        self._preview_note(base)

    def _preview_note(self, midi):
        self._cur_note = midi
        if not HAS_AUDIO:
            self._set_status("sounddevice yok — preview kapali")
            return
        try:
            self.on_preview()  # stop engine stream first (device contention)
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
    # PATCH PERSIST
    # ============================================================
    def _on_preset(self, name):
        if name in PATCH_PRESETS:
            self.plugin.set_patch(PATCH_PRESETS[name])
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, name)
            self._refresh_controls()
            self._preview_note(self._cur_note)

    def _save(self):
        name = self.name_entry.get().strip() or "patch"
        try:
            path = save_patch(self.plugin.get_patch(), name)
            self._refresh_patch_list()
            self._set_status(f"kaydedildi: {os.path.basename(path)}")
        except Exception as exc:
            self._set_status(f"kaydet hatasi: {exc}")

    def _load(self):
        sel = self.load_combo.get()
        if sel:
            try:
                patch = load_patch(sel)
                self.plugin.set_patch(patch)
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, sel)
                self._refresh_controls()
                self._preview_note(self._cur_note)
                self._set_status(f"yuklendi: {sel}")
            except Exception as exc:
                self._set_status(f"yukleme hatasi: {exc}")

    def _refresh_patch_list(self):
        names = list_patches()
        self.load_combo.configure(values=names if names else [""])
        if names:
            self.load_combo.set(names[0])

    # ============================================================
    # BEAT CHANNEL INTEGRATION
    # ============================================================
    def _refresh_channel_list(self):
        if not self.engine:
            return
        names = [n for n in self.engine.channel_names() if "synth" in n]
        if names:
            self.channel_combo.configure(values=names)
            self.channel_combo.set(names[0])
        else:
            self.channel_combo.configure(values=["(ekle)"])

    def _add_channel(self):
        if not self.engine:
            self._set_status("engine yok")
            return
        name = "synth_patch"
        base = name
        i = 2
        while name in self.engine.channel_names():
            name = f"{base}_{i}"
            i += 1
        ch = self.engine.add_channel(name, note_root=36, note_octave=1)
        ch.inst.set_patch(self.plugin.get_patch())
        # a rolling bass 16th pattern to start
        ch.set_pattern([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                       if self.plugin.get_patch()["category"] == "bass"
                       else [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0])
        self._refresh_channel_list()
        if self.panel:
            self.panel._refresh_channels()
        self._set_status(f"kanal eklendi: {name}")

    def _send_to_channel(self):
        if not self.engine:
            return
        sel = self.channel_combo.get()
        if sel in self.engine.channels:
            self.engine.channels[sel].inst.set_patch(self.plugin.get_patch())
            self._set_status(f"{sel} sesi guncellendi")
        else:
            self._set_status(f"kanal yok: {sel}")

    # ============================================================
    # CONTROL SYNC
    # ============================================================
    def _refresh_controls(self):
        p = self.plugin.get_params()
        try:
            self._osc_wave_set("osc1", WAVES[int(p["osc1_wave"])])
            self._osc_wave_set("osc2", WAVES[int(p["osc2_wave"])])
            self._set_slider("osc1_coarse_slider", p["osc1_coarse"], -24, 24)
            self._set_slider("osc1_detune_slider", p["osc1_detune"], -50, 50)
            self._set_slider("osc1_level_slider", p["osc1_level"], 0, 100)
            self._set_slider("osc2_coarse_slider", p["osc2_coarse"], -24, 24)
            self._set_slider("osc2_detune_slider", p["osc2_detune"], -50, 50)
            self._set_slider("osc2_level_slider", p["osc2_level"], 0, 100)
            self.filter_type.set(FILTERS[int(p["filter_type"])].upper())
            # log cutoff -> slider pos
            pos = 1000.0 * (np_log(p["filter_cutoff"] / 30.0) / np_log(16000.0 / 30.0))
            self.cutoff_slider.set(pos)
            self.cutoff_lbl.configure(text=f"{int(p['filter_cutoff'])} Hz")
            self.res_slider.set(p["filter_res"] * 100)
            self.res_lbl.configure(text=f"{p['filter_res']:.2f}")
            self.attack_slider.set(p["env_a"] / 2.0 * 100)
            self.decay_slider.set(p["env_d"] / 3.0 * 100)
            self.sustain_slider.set(p["env_s"] * 100)
            self.release_slider.set(p["env_r"] / 3.0 * 100)
            self.pitch_slider.set((p["pitch_amt"] + 48) / 96 * 100)
            self.drive_slider.set((p["drive"] - 1) / 7 * 100)
            self.level_slider.set(p["level"] * 100)
        except Exception:
            pass

    def _osc_wave_set(self, pref, wave):
        w = getattr(self, f"{pref}_wave")
        try:
            w.set(wave)
        except Exception:
            pass

    def _set_slider(self, attr, value, lo, hi):
        s = getattr(self, attr)
        try:
            s.set(float(value))
        except Exception:
            pass
        if hasattr(s, "_val_lbl"):
            s._val_lbl.configure(text=f"{value:.1f}")

    def get_patch(self):
        return self.plugin.get_patch()

    def set_patch(self, patch):
        self.plugin.set_patch(patch)
        self._refresh_controls()

    def _set_status(self, text):
        self.status_lbl.configure(text=text)


def np_log(x):
    import math
    return math.log(max(1e-9, x))


# cleanup at shutdown — stop any running preview
def _cleanup():
    if HAS_AUDIO:
        try:
            sd.stop()
        except Exception:
            pass
