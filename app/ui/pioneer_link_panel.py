"""
DJ AI OS — Pioneer Link Panel
=============================
Professional hardware + Rekordbox integration.

  • Connect a real Pioneer (CDJ/XDJ-RR/DJM/DDJ) or a virtual MIDI port.
  • Master MIDI clock locks the whole booth to your BPM.
  • Transport buttons drive the hardware decks.
  • The FX RACK is a live software effect studio: pick a preset, preview it
    on a built-in loop, and MIDI-LEARN any hardware knob/button to a slot.
  • Rekordbox XML import lights hot-cue pads and syncs BPM to the gear.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog

import numpy as np
import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BLUE_BRIGHT,
    F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.pioneer_link import (
    PioneerLink, list_ports, FX_PRESETS, preset_chain,
)
from app.ai.pioneer_fx import FXRack, FX_CATALOG
from app.ai.hardware_coach import HardwareCoach
from app.ai.instruments import get_instrument

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

SR = 44100
DECKS = ["A", "B", "C", "D"]

# primary "intensity" param per effect type (0-100 slider mapping)
FX_INTENSITY = {
    "echo":     ("feedback", 0.0, 0.9),
    "reverb":   ("decay", 0.0, 0.85),
    "filter":   ("lfo_depth", 0.0, 0.95),
    "flanger":  ("depth_ms", 0.5, 12.0),
    "phaser":   ("depth", 0.0, 1.0),
    "gate":     ("hold", 0.1, 1.0),
    "bitcrush": ("bits", 2, 16),
    "dist":     ("drive", 1.0, 6.0),
    "duck":     ("amount", 0.0, 0.95),
}


class PioneerLinkPanel(ctk.CTkFrame):
    """The professional bridge: hardware + MIDI clock + FX rack + Rekordbox."""

    def __init__(self, master, win=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BLUE_BRIGHT)
        self.win = win
        self.link = PioneerLink()
        self.rack = FXRack(slots=4, bpm=128)
        self._loop_cache = None
        self._loop_bpm = None
        self._mix_cache = None      # dry DAW mix (cached for re-FX)
        self._mix_bpm = None
        self._preview_job = None
        self._coach_job = None
        self._slot_widgets = []     # per-slot (type_combo, inten_slider, wet_slider)
        self.coach = HardwareCoach()

        self._build()
        self._refresh_ports()
        self.link._on_binding = self._on_binding
        self.link._on_event = self._on_hardware_event
        self._coach_tick()

    # ============================================================
    # UI BUILD
    # ============================================================
    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="PIONEER LINK", font=F_H3,
                     text_color=BLUE_BRIGHT).pack(side="left")
        self.status_lbl = ctk.CTkLabel(hdr, text="bağlanmadı", font=F_META,
                                       text_color=TEXT_DIM)
        self.status_lbl.pack(side="right")

        self._build_device(self)
        self._build_transport(self)
        self._build_presets(self)
        self._build_rack(self)
        self._build_preview(self)
        self._build_coach(self)
        self._build_rekordbox(self)

    # ---- device + clock -----------------------------------------
    def _build_device(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(r, text="MIDI", font=F_META,
                     text_color=TEXT_DIM).pack(side="left")
        self.in_combo = ctk.CTkComboBox(r, values=[], width=180, height=26,
                                        font=F_META)
        self.in_combo.pack(side="left", padx=3)
        self.out_combo = ctk.CTkComboBox(r, values=[], width=180, height=26,
                                         font=F_META)
        self.out_combo.pack(side="left", padx=3)
        ctk.CTkButton(r, text="🔌 BAĞLAN", width=88, height=26,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      font=F_BODY_BOLD,
                      command=self._toggle_connect).pack(side="left", padx=3)
        ctk.CTkLabel(r, text=" CLOCK", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(12, 4))
        self.clock_btn = ctk.CTkButton(r, text="● OFF", width=54, height=24,
                                       fg_color=SURFACE_RAISED,
                                       hover_color=BORDER,
                                       text_color=TEXT_SECONDARY, font=F_META,
                                       command=self._toggle_clock)
        self.clock_btn.pack(side="left")
        self.clock_bpm = ctk.CTkSlider(r, from_=90, to=180, width=100,
                                       height=14,
                                       command=lambda v: self._clock_bpm_chg(v))
        self.clock_bpm.set(128)
        self.clock_bpm.pack(side="left", padx=4)
        self.clock_lbl = ctk.CTkLabel(r, text="128", font=F_MONO,
                                      text_color=TEXT_SECONDARY, width=34)
        self.clock_lbl.pack(side="left")

    # ---- transport ----------------------------------------------
    def _build_transport(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(r, text="TRANSPORT", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 8))
        for deck in DECKS:
            f = ctk.CTkFrame(r, fg_color="transparent")
            f.pack(side="left", padx=4)
            ctk.CTkLabel(f, text=f"◉ {deck}", font=F_BODY_BOLD,
                         text_color=RED).pack(side="left", padx=(0, 3))
            for lbl, fn in (("PLAY", self._play), ("CUE", self._cue),
                            ("SYNC", self._sync)):
                ctk.CTkButton(f, text=lbl, width=44, height=22,
                              fg_color=SURFACE_RAISED, hover_color=BORDER,
                              text_color=TEXT_SECONDARY, font=F_META,
                              command=lambda fn=fn, d=deck: fn(d)).pack(
                                  side="left", padx=1)

    # ---- FX presets ---------------------------------------------
    def _build_presets(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(r, text="FX PRESET", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 6))
        for name in FX_PRESETS:
            ctk.CTkButton(r, text=name, width=88, height=24,
                          fg_color=RED if name == "CLEAN" else SURFACE_RAISED,
                          hover_color=BORDER,
                          text_color="#FFF" if name == "CLEAN" else TEXT_SECONDARY,
                          font=F_META,
                          command=lambda n=name: self._apply_preset(n)).pack(
                              side="left", padx=2)

    # ---- FX rack ------------------------------------------------
    def _build_rack(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        hdr = ctk.CTkFrame(box, fg_color="transparent")
        hdr.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(hdr, text="FX RACK", font=F_META,
                     text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(hdr, text="TÜMÜNÜ TEMİZLE", width=100, height=22,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._clear_all).pack(side="right")

        for s in range(4):
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=2)
            ctk.CTkLabel(row, text=f"S{s + 1}", font=F_MONO, width=24,
                         text_color=TEXT_DIM).pack(side="left")
            combo = ctk.CTkComboBox(row, values=["—"] + list(FX_CATALOG),
                                    width=120, height=24, font=F_META,
                                    command=lambda v, s=s: self._slot_type(s, v))
            combo.set("—")
            combo.pack(side="left", padx=2)
            inten, inten_lbl = self._mini_slider(row, "INTEN", 0, 100, 60)
            wet, wet_lbl = self._mini_slider(row, "WET", 0, 100, 50)
            ctk.CTkButton(row, text="ÖĞREN", width=52, height=22,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=lambda s=s: self._learn(s, "intensity")).pack(
                              side="left", padx=1)
            ctk.CTkButton(row, text="WET", width=44, height=22,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=lambda s=s: self._learn(s, "wet")).pack(
                              side="left", padx=1)
            inten.configure(command=lambda v, s=s: self._slot_inten(s, v))
            wet.configure(command=lambda v, s=s: self._slot_wet(s, v))
            self._slot_widgets.append((combo, inten, inten_lbl, wet, wet_lbl))

    def _mini_slider(self, parent, label, lo, hi, init):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=3)
        ctk.CTkLabel(f, text=label, font=("Consolas", 8), text_color=TEXT_DIM,
                     width=38).pack(side="left")
        s = ctk.CTkSlider(f, from_=lo, to=hi, width=86, height=12)
        s.set(float(init))
        s.pack(side="left", padx=2)
        lbl = ctk.CTkLabel(f, text=str(init), font=("Consolas", 8),
                           text_color=TEXT_SECONDARY, width=28)
        lbl.pack(side="left")
        return s, lbl

    # ---- preview ------------------------------------------------
    def _build_preview(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(r, text="PREVIEW", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 8))
        self.src_combo = ctk.CTkComboBox(r, values=["LOOP (dahili)",
                                                    "SET MİX (DAW)"],
                                         width=130, height=24, font=F_META,
                                         command=lambda v: self._set_status(
                                             f"kaynak: {v}"))
        self.src_combo.set("LOOP (dahili)")
        self.src_combo.pack(side="left", padx=3)
        ctk.CTkButton(r, text="▶ FX'İ DUY", width=104, height=26,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      font=F_BODY_BOLD,
                      command=self._preview_fx).pack(side="left", padx=3)
        ctk.CTkButton(r, text="STOP", width=52, height=26,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._stop).pack(side="left", padx=3)
        self.preview_lbl = ctk.CTkLabel(r, text="2 bar 4/4 loop @128",
                                        font=F_META, text_color=TEXT_DIM)
        self.preview_lbl.pack(side="left", padx=8)

    # ---- AI hardware coach -------------------------------------
    def _build_coach(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=2)
        hdr = ctk.CTkFrame(box, fg_color="transparent")
        hdr.pack(fill="x", padx=6, pady=(6, 0))
        ctk.CTkLabel(hdr, text="AI DONANIM KOÇU", font=F_META,
                     text_color=TEXT_DIM).pack(side="left")
        ctk.CTkLabel(hdr, text="ellerinden öğrenir", font=F_META,
                     text_color=TEXT_DIM).pack(side="right")
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=4)
        self.coach_sum_lbl = ctk.CTkLabel(r, text="henüz veri yok — donanımda "
                                           "oyna ya da kaynağı bağla",
                                          font=("Consolas", 9),
                                          text_color=TEXT_SECONDARY,
                                          anchor="w")
        self.coach_sum_lbl.pack(fill="x")
        self.coach_sug_lbl = ctk.CTkLabel(box, text="",
                                          font=F_BODY_BOLD,
                                          text_color=BLUE_BRIGHT,
                                          wraplength=760, justify="left",
                                          anchor="w")
        self.coach_sug_lbl.pack(fill="x", padx=8, pady=(0, 2))
        self.coach_set_lbl = ctk.CTkLabel(box, text="", font=F_META,
                                          text_color=RED, anchor="w")
        self.coach_set_lbl.pack(fill="x", padx=8, pady=(0, 6))

    def _coach_tick(self):
        try:
            if self.coach.ready:
                line, deck = self.coach.summary()
                self.coach_sum_lbl.configure(text=line)
                set_tracks = None
                if self.win and getattr(self.win, "current_set", None):
                    set_tracks = self.win.current_set
                sugs = self.coach.suggest(set_tracks=set_tracks)
                if sugs:
                    text, conf, kind = sugs[0]
                    self.coach_sug_lbl.configure(
                        text=f"💡 {text}   [{conf:.0%}]")
                    self.coach_set_lbl.configure(
                        text=" | ".join(s[0] for s in sugs[1:3]))
        except Exception:
            pass
        try:
            self._coach_job = self.after(1000, self._coach_tick)
        except Exception:
            pass

    # ---- Rekordbox ----------------------------------------------
    def _build_rekordbox(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG, corner_radius=6)
        box.pack(fill="x", padx=10, pady=(2, 8))
        r = ctk.CTkFrame(box, fg_color="transparent")
        r.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(r, text="REKORDBOX", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(0, 8))
        ctk.CTkButton(r, text="📂 XML İÇE AKTAR", width=120, height=24,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._import_rekordbox).pack(side="left", padx=3)
        self.rb_lbl = ctk.CTkLabel(r, text="", font=F_META,
                                   text_color=BLUE_BRIGHT)
        self.rb_lbl.pack(side="left", padx=8)
        self.rb_tracks = []
        self.rb_box = ctk.CTkScrollableFrame(box, fg_color="transparent",
                                             height=96)
        # packed lazily on first successful import

    # ============================================================
    # DEVICE / CLOCK
    # ============================================================
    def _refresh_ports(self):
        ports = list_ports()
        ins, outs = ports["inputs"], ports["outputs"]
        self.in_combo.configure(values=ins or ["(yok)"])
        self.out_combo.configure(values=outs or ["(yok)"])
        if ins:
            self.in_combo.set(ins[0])
        if outs:
            self.out_combo.set(outs[0])
        self._set_status(f"{len(ins)} giriş · {len(outs)} çıkış portu")

    def _toggle_connect(self):
        if self.link.connected:
            self.link.disconnect()
            self._set_status("bağlantı koptu")
            return
        inp = self.in_combo.get() if self.in_combo.get() != "(yok)" else None
        out = self.out_combo.get() if self.out_combo.get() != "(yok)" else None
        if not (inp or out):
            self._set_status("port yok — sanal port takılı değil")
            return
        ok = self.link.connect(in_port=inp, out_port=out)
        self._set_status("BAĞLANDI ✓" if ok else "bağlantı hatası")

    def _toggle_clock(self):
        if self.link.clock_running:
            self.link.stop_clock()
            self.clock_btn.configure(text="● OFF", fg_color=SURFACE_RAISED,
                                     text_color=TEXT_SECONDARY)
            self._set_status("clock durdu")
        else:
            bpm = int(self.clock_bpm.get())
            self.link.start_clock(bpm)
            self.clock_btn.configure(text="● ON", fg_color=RED,
                                     text_color="#FFF")
            self._set_status(f"MIDI clock: {bpm} BPM gönderiliyor")

    def _clock_bpm_chg(self, value):
        bpm = int(value)
        self.clock_lbl.configure(text=str(bpm))
        if self.link._clock:
            self.link._clock.set_bpm(bpm)

    # ============================================================
    # TRANSPORT
    # ============================================================
    def _play(self, deck):
        self.link.play(deck)
        self._set_status(f"deck {deck}: PLAY gönderildi")

    def _cue(self, deck):
        self.link.cue(deck)

    def _sync(self, deck):
        self.link.sync(deck)

    # ============================================================
    # FX RACK
    # ============================================================
    def _apply_preset(self, name):
        self._clear_all()
        chain = preset_chain(name)
        for i, (fx_type, params) in enumerate(chain):
            if i >= 4:
                break
            self.rack.set(i, fx_type, params)
            self._sync_slot_ui(i, fx_type, params)
        self._set_status(f"preset: {name}")

    def _clear_all(self):
        for i in range(4):
            self.rack.clear(i)
            combo, inten, ilbl, wet, wlbl = self._slot_widgets[i]
            combo.set("—")
            inten.set(60)
            ilbl.configure(text="60")
            wet.set(50)
            wlbl.configure(text="50")
            self.link.clear_binding(i, "intensity")
            self.link.clear_binding(i, "wet")

    def _sync_slot_ui(self, i, fx_type, params):
        combo, inten, ilbl, wet, wlbl = self._slot_widgets[i]
        combo.set(fx_type)
        wet.set(int(params.get("wet", 0.5) * 100))
        wlbl.configure(text=str(int(params.get("wet", 0.5) * 100)))
        pk = FX_INTENSITY.get(fx_type, ("wet", 0, 1))[0]
        lo, hi = FX_INTENSITY.get(fx_type, ("wet", 0, 1))[1], \
            FX_INTENSITY.get(fx_type, ("wet", 0, 1))[2]
        val = params.get(pk, lo + (hi - lo) * 0.6)
        inten.set(int((val - lo) / (hi - lo) * 100) if hi > lo else 60)
        ilbl.configure(text=str(int(inten.get())))

    def _slot_type(self, s, value):
        if value == "—":
            self.rack.clear(s)
        else:
            self.rack.set(s, value)
        self._set_status(f"slot {s + 1}: {value}")

    def _slot_inten(self, s, v):
        fx_type = self.rack.slots[s]["type"]
        if not fx_type:
            return
        pk, lo, hi = FX_INTENSITY.get(fx_type, ("wet", 0, 1))
        norm = float(v) / 100.0
        val = lo + norm * (hi - lo)
        self.rack.set_param(s, pk, round(val, 4))
        self._slot_widgets[s][2].configure(text=str(int(v)))
        self._schedule_preview()

    def _slot_wet(self, s, v):
        self.rack.set_param(s, "wet", float(v) / 100.0)
        self._slot_widgets[s][4].configure(text=str(int(v)))
        self._schedule_preview()

    def _learn(self, s, which):
        param = which if which != "intensity" else \
            FX_INTENSITY.get(self.rack.slots[s]["type"], ("wet", 0, 1))[0]
        self.link.arm_learn(s, param)
        self._set_status(f"ÖĞREN: slot {s + 1} / {param} — donanımda düğmeye bas")

    def _on_binding(self, target, value01):
        # called from link thread on hardware control movement
        slot, param = target
        try:
            self.after(0, lambda: self._apply_hardware(slot, param, value01))
        except Exception:
            pass

    def _apply_hardware(self, slot, param, value01):
        fx_type = self.rack.slots[slot]["type"]
        if not fx_type:
            return
        self.rack.set_param(slot, param, float(value01))
        if param == "wet":
            self._slot_widgets[slot][3].set(int(value01 * 100))
            self._slot_widgets[slot][4].configure(text=str(int(value01 * 100)))
        else:
            pk, lo, hi = FX_INTENSITY.get(fx_type, ("wet", 0, 1))
            norm = (float(value01) - lo) / (hi - lo) if hi > lo else value01
            norm = max(0.0, min(1.0, norm))
            self._slot_widgets[slot][1].set(int(norm * 100))
            self._slot_widgets[slot][2].configure(text=str(int(norm * 100)))
        self._schedule_preview()

    def _on_hardware_event(self, ev):
        try:
            self.coach.feed(ev)
            if ev.get("type") == "play":
                self._set_status(f"donanım: deck {ev.get('deck')} PLAY")
        except Exception:
            pass

    # ============================================================
    # PREVIEW AUDIO
    # ============================================================
    def _make_loop(self, bpm=128):
        """2-bar 4/4 loop built from real instrument hits — always works."""
        if self._loop_cache is not None and self._loop_bpm == bpm:
            return self._loop_cache
        step_s = 60.0 / bpm / 4.0
        n = int(step_s * SR * 32)           # 2 bars
        out = np.zeros(n, dtype=np.float32)

        def place(sig, step_idx, gain=1.0):
            i = int(step_idx * step_s * SR)
            seg = sig if len(sig) <= n - i else sig[: n - i]
            out[i: i + len(seg)] += seg * gain

        kick = get_instrument("kick").hit(velocity=1.0)
        hat = get_instrument("hat").hit(velocity=0.6)
        clap = get_instrument("clap").hit(velocity=0.8)
        bass = get_instrument("bass_saw").hit(note=33, velocity=0.9)
        for s in range(0, 32, 2):           # beats
            place(kick, s)
        for s in range(1, 32, 2):           # off-beats
            place(hat, s, 0.55)
        for s in range(4, 32, 8):           # backbeats
            place(clap, s, 0.7)
        for s in (0, 16):                   # bass on 1 & 3
            place(bass, s)
        peak = float(np.max(np.abs(out))) + 1e-9
        out = (out / peak * 0.9).astype(np.float32)
        self._loop_cache = out
        self._loop_bpm = bpm
        return out

    def _make_mix(self, bpm):
        """Bounce the DAW arrangement dry once, cache it for re-FX."""
        if self._mix_cache is not None and self._mix_bpm == bpm:
            return self._mix_cache
        engine = None
        if self.win and getattr(self.win, "daw_panel", None):
            engine = getattr(self.win.daw_panel, "engine", None)
        if engine is None or not engine.project.arrangement_length():
            return None
        self._mix_cache = engine.bounce_mix()
        self._mix_bpm = bpm
        return self._mix_cache

    def _preview_fx(self):
        bpm = int(self.clock_bpm.get())
        active = self.rack.active_slots()
        src = self.src_combo.get()
        if src.startswith("SET MİX"):
            dry = self._make_mix(bpm)
            if dry is None:
                self._set_status("SET MİX: önce Beat Studio'da bir "
                                 "aranjman oluştur")
                return
            if active:
                L = self.rack.apply(dry[0], bpm=bpm)
                R = self.rack.apply(dry[1], bpm=bpm)
                audio = np.stack([L, R])
            else:
                audio = dry
            label = f"set mix ({dry.shape[1] / SR:.1f}s)"
        else:
            audio = self._make_loop(bpm)
            if active:
                audio = self.rack.apply(audio, bpm=bpm)
            label = f"loop @{bpm} BPM"
        if HAS_AUDIO:
            sd.stop()
            sd.play(audio, SR)
        names = [s["type"] for s in active]
        self.preview_lbl.configure(text=label)
        self._set_status(f"▶ {names or 'temiz'} @{bpm} BPM ({label})")

    def _schedule_preview(self):
        if self._preview_job:
            try:
                self.after_cancel(self._preview_job)
            except Exception:
                pass
        self._preview_job = self.after(140, self._preview_fx)

    def _stop(self):
        if HAS_AUDIO:
            try:
                sd.stop()
            except Exception:
                pass

    # ============================================================
    # REKORDBOX
    # ============================================================
    def _import_rekordbox(self):
        path = filedialog.askopenfilename(
            parent=self, title="Rekordbox XML seç",
            filetypes=[("Rekordbox XML", "*.xml"), ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            tracks, playlists = self.link.load_rekordbox_xml(path)
        except Exception as exc:
            self._set_status(f"XML HATASI: {exc}")
            return
        self.rb_tracks = tracks
        lib = []
        if self.win:
            lib = getattr(self.win, "library", None) or \
                getattr(self.win, "saved_tracks", None) or []
        lib_names = {os.path.basename(t.get("path", "")).lower()
                     for t in lib if t.get("path")}
        matched = [t for t in tracks
                   if os.path.basename(t.get("path", "")).lower() in lib_names]
        self.rb_lbl.configure(
            text=f"{len(tracks)} parça · {len(matched)} kütüphaneyle eşleşti · "
                 f"{len(playlists)} playlist")
        # show the list panel (once) and rebuild it
        if not self.rb_box.winfo_ismapped():
            self.rb_box.pack(fill="x", padx=6, pady=(0, 6))
        for w in self.rb_box.winfo_children():
            w.destroy()
        for t in (matched or tracks)[:6]:
            row = ctk.CTkFrame(self.rb_box, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{t.get('name')} · {t.get('bpm') or '?'} BPM"
                                   f" · {t.get('key') or '?'}",
                         font=F_META, text_color=TEXT_SECONDARY,
                         width=240, anchor="w").pack(side="left", padx=2)
            ctk.CTkButton(row, text="▶ A", width=34, height=20,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=lambda t=t: self._load_to_deck(t, "A")).pack(
                              side="left", padx=1)
            ctk.CTkButton(row, text="▶ B", width=34, height=20,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=lambda t=t: self._load_to_deck(t, "B")).pack(
                              side="left", padx=1)
        self._set_status(f"Rekordbox: {os.path.basename(path)}")

    def _load_to_deck(self, track, deck):
        bpm = track.get("bpm")
        if bpm:
            self.link.set_tempo(float(bpm), deck)
        self.link.light_hot_cue(deck, 1, "GREEN")
        self.link.light_hot_cue(deck, 2, "CYAN")
        self._set_status(f"deck {deck} ← {track.get('name')} @{bpm} BPM, "
                         f"cue ışıkları yandı")

    # ============================================================
    def _set_status(self, text):
        self.status_lbl.configure(text=text)

    def on_close(self):
        if self._coach_job:
            try:
                self.after_cancel(self._coach_job)
            except Exception:
                pass
            self._coach_job = None
        self._stop()
        self.link.stop_clock()
        self.link.disconnect()
