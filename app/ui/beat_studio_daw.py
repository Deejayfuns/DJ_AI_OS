"""
DJ AI OS — Beat Studio DAW (full DAW)

Ableton/FL-style DAW for beat production:

  ┌─ TRANSPORT ───────────────────────────────────────────────┐
  │ ▶ ⏹  BPM [120]  pos 0:00  ▸ SAVE  ▸ LOAD  ▸ EXPORT STEMS │
  ├─ TRACKS ─┬─ PATTERN GRID (16 steps) ─────────────────────┤
  │ kick     │ █ · · █ █ · · █ █ · · █ █ · · █  [vol][mute] │
  │ bass     │ █ · █ · █ · █ · █ · █ · █ · █ · █            │
  ├─ PIANO ROLL (selected track) ────────────────────────────┤
  │  ░░ bars 1..8  — click to add note, right-click delete    │
  ├─ ARRANGEMENT ────────────────────────────────────────────┤
  │  bars 1..16 — pattern/midi blocks on a timeline           │
  └─ MIXER ──────────────────────────────────────────────────┘
"""

import math
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, BORDER_LIGHT, RED, RED_HOVER,
    GREEN, GREEN_DIM, AMBER, BLUE_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)
from app.ai.daw_project import DAWProject
from app.ai.daw_engine import DAWEngine
from app.ai.instruments import list_instruments

try:
    import sounddevice as sd
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

PROJECTS_DIR = os.path.join("DJ_EXPORTS", "projects")
STEMS_DIR = os.path.join("DJ_EXPORTS", "daw_stems")

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PIANO_TOP = 84   # C6
PIANO_BOTTOM = 36  # C2


class DAWPanel(ctk.CTkFrame):
    """Full DAW panel: transport, pattern grid, piano roll, arrangement, mixer."""

    def __init__(self, master, project=None, win=None):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.win = win
        self.project = project or DAWProject(bpm=126)
        self.engine = DAWEngine(self.project)
        self.sr = 44100
        self._stream = None
        self._stream_thread = None
        self._playing = False
        self._poll_job = None
        self._selected_track = self.project.tracks[0].name if self.project.tracks else None

        self._build()
        if not self.project.tracks:
            self._seed_default_project()
        self._select_track(self._selected_track or self.project.tracks[0].name)
        self._refresh_all()

    # ============================================================
    # BUILD
    # ============================================================
    def _build(self):
        self._build_transport()
        self._build_track_area()
        self._build_piano_roll()
        self._build_arrangement()
        self._build_mixer()

    def _build_transport(self):
        tr = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0)
        tr.pack(fill="x")
        inner = ctk.CTkFrame(tr, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(inner, text="DAW", font=F_H3, text_color=RED).pack(side="left", padx=(0, 8))
        self.play_btn = ctk.CTkButton(inner, text="▶", width=44, height=28, font=F_BODY_BOLD,
                                      fg_color=GREEN, hover_color=GREEN_DIM, text_color="#FFF",
                                      command=self._toggle_play)
        self.play_btn.pack(side="left", padx=2)
        ctk.CTkButton(inner, text="⏹", width=40, height=28, font=F_BODY_BOLD,
                      fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._stop).pack(side="left", padx=2)

        ctk.CTkLabel(inner, text="BPM", font=F_META, text_color=TEXT_DIM).pack(side="left", padx=(10, 4))
        self.bpm_entry = ctk.CTkEntry(inner, width=56, height=26, font=F_MONO,
                                      fg_color=BG, border_color=BORDER)
        self.bpm_entry.insert(0, str(int(self.project.bpm)))
        self.bpm_entry.bind("<Return>", lambda e: self._set_bpm())
        self.bpm_entry.pack(side="left", padx=(0, 4))
        self.pos_lbl = ctk.CTkLabel(inner, text="0:00", font=F_MONO, text_color=AMBER)
        self.pos_lbl.pack(side="left", padx=12)

        ctk.CTkButton(inner, text="SAVE", width=60, height=26, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._save).pack(side="right", padx=2)
        ctk.CTkButton(inner, text="LOAD", width=60, height=26, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._load).pack(side="right", padx=2)
        ctk.CTkButton(inner, text="EXPORT STEMS", width=110, height=26, font=F_META,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      command=self._export).pack(side="right", padx=2)

    def _build_track_area(self):
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6)
        box.pack(fill="x", padx=8, pady=(8, 4))
        hdr = ctk.CTkFrame(box, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="STEP SEQUENCER", font=F_META, text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(hdr, text="+ TRACK", width=72, height=22, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=TEXT_SECONDARY,
                      command=self._add_track).pack(side="right")

        self.track_rows = ctk.CTkFrame(box, fg_color=BG, corner_radius=4)
        self.track_rows.pack(fill="x", padx=8, pady=(0, 8))
        self._cell_buttons = {}

    def _rebuild_track_rows(self):
        for w in self.track_rows.winfo_children():
            w.destroy()
        self._cell_buttons = {}
        for r, t in enumerate(self.project.tracks):
            row = ctk.CTkFrame(self.track_rows, fg_color="transparent")
            row.pack(fill="x", pady=1)

            # track name button (select -> piano roll)
            nm = ctk.CTkButton(row, text=t.name, width=100, height=22, corner_radius=3,
                               fg_color=SURFACE_RAISED, hover_color=BORDER,
                               text_color=BLUE_BRIGHT if t.name == self._selected_track else TEXT_SECONDARY,
                               font=F_META, command=lambda n=t.name: self._select_track(n))
            nm.pack(side="left", padx=2)

            # instrument combo
            combo = ctk.CTkComboBox(row, values=list_instruments(), width=120, height=22,
                                    font=("Consolas", 9), command=lambda v, n=t.name: self._set_inst(n, v))
            combo.set(t.instrument)
            combo.pack(side="left", padx=2)

            # 16 step cells
            self._cell_buttons[t.name] = []
            for s in range(16):
                b = ctk.CTkButton(row, text="", width=24, height=22, corner_radius=2,
                                  fg_color=GREEN if t.steps[s] else SURFACE_RAISED,
                                  hover_color=BORDER, border_width=1, border_color=BORDER,
                                  command=lambda n=t.name, si=s: self._toggle_step(n, si))
                b.pack(side="left", padx=1)
                self._cell_buttons[t.name].append(b)

            # volume mini + mute/solo
            ctk.CTkLabel(row, text="VOL", font=("Consolas", 7), text_color=TEXT_DIM).pack(
                side="left", padx=(8, 2))
            vs = ctk.CTkSlider(row, from_=0, to=100, width=70, height=12,
                               command=lambda v, n=t.name: self._set_vol(n, v / 100))
            vs.set(t.volume * 100)
            vs.pack(side="left", padx=2)
            mu = ctk.CTkButton(row, text="M", width=24, height=22, corner_radius=2,
                               fg_color=RED if t.muted else SURFACE_RAISED,
                               hover_color=BORDER, text_color="#FFF" if t.muted else TEXT_DIM,
                               font=("Consolas", 8),
                               command=lambda n=t.name: self._toggle_mute(n))
            mu.pack(side="left", padx=1)
            so = ctk.CTkButton(row, text="S", width=24, height=22, corner_radius=2,
                               fg_color=AMBER if t.solo else SURFACE_RAISED,
                               hover_color=BORDER, text_color="#000" if t.solo else TEXT_DIM,
                               font=("Consolas", 8),
                               command=lambda n=t.name: self._toggle_solo(n))
            so.pack(side="left", padx=1)

    def _build_piano_roll(self):
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6)
        box.pack(fill="x", padx=8, pady=4)
        hdr = ctk.CTkFrame(box, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="PIANO ROLL", font=F_META, text_color=TEXT_DIM).pack(side="left")
        self.pr_track_lbl = ctk.CTkLabel(hdr, text="", font=F_META, text_color=BLUE_BRIGHT)
        self.pr_track_lbl.pack(side="left", padx=8)

        self.pr_canvas = tk.Canvas(box, height=180, bg="#12121C", highlightthickness=0)
        self.pr_canvas.pack(fill="x", padx=8, pady=(0, 6))
        self.pr_canvas.bind("<Button-1>", self._pr_click)
        self.pr_canvas.bind("<B3-Motion>", self._pr_drag)
        self.pr_canvas.bind("<Button-3>", self._pr_delete)
        self.pr_canvas.bind("<Configure>", lambda e: self._refresh_piano_roll())

    def _build_arrangement(self):
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6)
        box.pack(fill="x", padx=8, pady=4)
        hdr = ctk.CTkFrame(box, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text="ARRANGEMENT", font=F_META, text_color=TEXT_DIM).pack(side="left")
        ctk.CTkLabel(hdr, text="track'a sag tikla → pattern ekle", font=F_META,
                     text_color=TEXT_DIM).pack(side="right")

        self.arr_canvas = tk.Canvas(box, height=90, bg="#12121C", highlightthickness=0)
        self.arr_canvas.pack(fill="x", padx=8, pady=(0, 6))
        self.arr_canvas.bind("<Button-1>", self._arr_click)
        self.arr_canvas.bind("<Button-3>", self._arr_delete)
        self.arr_canvas.bind("<Configure>", lambda e: self._refresh_arrangement())

    def _build_mixer(self):
        box = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6)
        box.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkLabel(box, text="MIXER", font=F_META, text_color=TEXT_DIM).pack(
            anchor="w", padx=8, pady=(6, 2))
        self.mixer_frame = ctk.CTkFrame(box, fg_color=BG, corner_radius=4)
        self.mixer_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._mixer_sliders = {}

    def _rebuild_mixer(self):
        for w in self.mixer_frame.winfo_children():
            w.destroy()
        self._mixer_sliders = {}
        for t in self.project.tracks:
            ch = ctk.CTkFrame(self.mixer_frame, fg_color=SURFACE_RAISED, corner_radius=4,
                              width=86)
            ch.pack(side="left", padx=3, pady=4, fill="y")
            ch.pack_propagate(False)
            ctk.CTkLabel(ch, text=t.name, font=("Consolas", 8),
                         text_color=BLUE_BRIGHT if t.name == self._selected_track else TEXT_SECONDARY).pack()
            vol = ctk.CTkSlider(ch, from_=0, to=100, width=60, height=90,
                                command=lambda v, n=t.name: self._set_vol(n, v / 100))
            vol.set(t.volume * 100)
            vol.pack(pady=2)
            pan = ctk.CTkSlider(ch, from_=-100, to=100, width=60, height=60,
                                command=lambda v, n=t.name: self._set_pan(n, v / 100))
            pan.set(t.pan * 100)
            pan.pack(pady=2)
            ctk.CTkLabel(ch, text=f"PAN {t.pan:+.1f}", font=("Consolas", 7),
                         text_color=TEXT_DIM).pack()
            self._mixer_sliders[t.name] = (vol, pan)

    # ============================================================
    # TRACK ACTIONS
    # ============================================================
    def _seed_default_project(self):
        self.project.bpm = 126
        kick = self.project.add_track("kick", "kick_tech",
                                      pattern=[1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
        kick.volume = 1.0
        hat = self.project.add_track("hat", "hat_tech",
                                     pattern=[0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0])
        hat.volume = 0.5
        bass = self.project.add_track("bass", "bass_roll",
                                      pattern=[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
        bass.note_root = 36
        bass.volume = 0.9
        lead = self.project.add_track("lead", "synth_patch", pattern=[0] * 16)
        lead.notes = [{"pitch": 60, "start": 0, "dur": 0.5, "vel": 0.8},
                      {"pitch": 64, "start": 1, "dur": 0.5, "vel": 0.8},
                      {"pitch": 67, "start": 2, "dur": 0.5, "vel": 0.8},
                      {"pitch": 64, "start": 3, "dur": 1.0, "vel": 0.8}]
        for n in ("kick", "hat", "bass"):
            self.project.add_block("pattern", n, 0, 4)
        self.project.add_block("midi", "lead", 0, 4)
        self.engine.mark_dirty()
        self._selected_track = "bass"

    def _add_track(self):
        n = f"track{len(self.project.tracks) + 1}"
        self.project.add_track(n, "bass_roll")
        self.project.add_block("pattern", n, 0, 4)
        self.engine.mark_dirty()
        self._select_track(n)

    def _set_inst(self, name, inst):
        t = self.project.get_track(name)
        if t:
            t.instrument = inst
            self.engine.mark_dirty()

    def _toggle_step(self, name, idx):
        t = self.project.get_track(name)
        if not t:
            return
        t.steps[idx] = 1 - t.steps[idx]
        btn = self._cell_buttons[name][idx]
        btn.configure(fg_color=GREEN if t.steps[idx] else SURFACE_RAISED,
                      border_color=GREEN if t.steps[idx] else BORDER)
        self.engine.mark_dirty()

    def _set_vol(self, name, v):
        t = self.project.get_track(name)
        if t:
            t.volume = max(0.0, min(1.5, v))
            self.engine.mark_dirty()

    def _set_pan(self, name, v):
        t = self.project.get_track(name)
        if t:
            t.pan = max(-1.0, min(1.0, v))
            self.engine.mark_dirty()
        if name in self._mixer_sliders:
            # refresh label via next redraw
            self._rebuild_mixer()

    def _toggle_mute(self, name):
        t = self.project.get_track(name)
        if t:
            t.muted = not t.muted
            self._rebuild_track_rows()

    def _toggle_solo(self, name):
        t = self.project.get_track(name)
        if t:
            t.solo = not t.solo
            self._rebuild_track_rows()

    def _select_track(self, name):
        self._selected_track = name
        self.pr_track_lbl.configure(text=name)
        self._refresh_piano_roll()
        self._rebuild_track_rows()
        self._rebuild_mixer()

    # ============================================================
    # PIANO ROLL
    # ============================================================
    def _pr_note_h(self):
        rows = PIANO_TOP - PIANO_BOTTOM + 1
        return max(1.0, 180.0 / rows)

    def _pr_bar_px(self, cw):
        # 4 bars across the canvas width
        return cw / 4.0

    def _pr_to_pitch(self, y):
        return PIANO_TOP - int(y // self._pr_note_h())

    def _pr_to_bar(self, x):
        cw = self.pr_canvas.winfo_width()
        if cw < 10:
            return 0.0
        return max(0.0, x / self._pr_bar_px(cw))

    def _pr_add_note(self, bar, pitch):
        t = self.project.get_track(self._selected_track)
        if not t:
            return
        bar = round(bar * 4) / 4  # snap to 16th
        pitch = max(PIANO_BOTTOM, min(PIANO_TOP, pitch))
        # replace note at same slot
        t.notes = [n for n in t.notes if not (abs(n["start"] - bar) < 0.06 and n["pitch"] == pitch)]
        t.notes.append({"pitch": pitch, "start": bar, "dur": 0.5, "vel": 0.9})
        t.notes.sort(key=lambda n: n["start"])
        self.engine.mark_dirty()
        self._refresh_piano_roll()

    def _pr_delete(self, evt):
        t = self.project.get_track(self._selected_track)
        if not t:
            return
        pitch = self._pr_to_pitch(evt.y)
        bar = self._pr_to_bar(evt.x)
        t.notes = [n for n in t.notes
                   if not (abs(n["start"] - bar) < 0.12 and n["pitch"] == pitch)]
        self.engine.mark_dirty()
        self._refresh_piano_roll()

    def _pr_click(self, evt):
        self._pr_add_note(self._pr_to_bar(evt.x), self._pr_to_pitch(evt.y))

    def _pr_drag(self, evt):
        self._pr_add_note(self._pr_to_bar(evt.x), self._pr_to_pitch(evt.y))

    def _refresh_piano_roll(self):
        c = self.pr_canvas
        c.delete("all")
        cw = c.winfo_width()
        if cw < 10:
            return
        t = self.project.get_track(self._selected_track)
        nh = self._pr_note_h()
        bp = self._pr_bar_px(cw)

        # rows
        for p in range(PIANO_BOTTOM, PIANO_TOP + 1):
            y = (PIANO_TOP - p) * nh
            black = "#" in NOTE_NAMES[p % 12]
            c.create_line(0, y, cw, y, fill="#1C1C2C" if black else "#16161F")
            if p % 12 == 0:
                c.create_text(3, y + 2, text=NOTE_NAMES[p % 12] + str(p // 12 - 1),
                              fill="#555570", anchor="nw", font=("Consolas", 7))
        # bar lines
        for b in range(5):
            x = b * bp
            c.create_line(x, 0, x, 180, fill="#2A2A3A")
            c.create_text(x + 3, 2, text=str(b + 1), fill="#555570", anchor="nw",
                          font=("Consolas", 7))
        if t:
            for n in t.notes:
                x = n["start"] * bp
                y = (PIANO_TOP - n["pitch"]) * nh
                w = max(6, n["dur"] * bp)
                c.create_rectangle(x, y + 1, x + w, y + nh - 2,
                                   fill=BLUE_BRIGHT, outline="", tags="note")
                c.create_rectangle(x, y + 1, x + w, y + nh - 2,
                                   outline="#FFFFFF", width=0)

    # ============================================================
    # ARRANGEMENT
    # ============================================================
    def _arr_bar_px(self, cw):
        return max(30.0, cw / 16.0)

    def _arr_click(self, evt):
        cw = self.arr_canvas.winfo_width()
        bp = self._arr_bar_px(cw)
        bar = int(evt.x // bp)
        # determine track by row height
        nh = max(20.0, 90.0 / max(1, len(self.project.tracks)))
        row = int(evt.y // nh)
        if row < len(self.project.tracks) and self.project.tracks:
            tname = self.project.tracks[row].name
            # toggle pattern block at that bar
            existing = [b for b in self.project.blocks
                        if b["track"] == tname and b["type"] == "pattern"
                        and int(b["start"]) == bar]
            if existing:
                self.project.blocks.remove(existing[0])
            else:
                self.project.add_block("pattern", tname, bar, 4)
            self.engine.mark_dirty()
            self._refresh_arrangement()

    def _arr_delete(self, evt):
        cw = self.arr_canvas.winfo_width()
        bp = self._arr_bar_px(cw)
        bar = int(evt.x // bp)
        nh = max(20.0, 90.0 / max(1, len(self.project.tracks)))
        row = int(evt.y // nh)
        if row < len(self.project.tracks):
            tname = self.project.tracks[row].name
            self.project.blocks = [b for b in self.project.blocks
                                   if not (b["track"] == tname and int(b["start"]) == bar)]
            self.engine.mark_dirty()
            self._refresh_arrangement()

    def _refresh_arrangement(self):
        c = self.arr_canvas
        c.delete("all")
        cw = c.winfo_width()
        if cw < 10:
            return
        bp = self._arr_bar_px(cw)
        tracks = self.project.tracks
        nh = max(20.0, 90.0 / max(1, len(tracks)))

        for r, t in enumerate(tracks):
            y = r * nh
            c.create_rectangle(0, y, cw, y + nh, fill="#14141E", outline="")
            c.create_text(4, y + 4, text=t.name, fill=TEXT_DIM, anchor="nw",
                          font=("Consolas", 8))
            for b in self.project.blocks:
                if b["track"] != t.name:
                    continue
                x = b["start"] * bp
                w = max(20, b["length"] * bp)
                color = AMBER if b["type"] == "midi" else RED
                c.create_rectangle(x + 1, y + 2, x + w - 1, y + nh - 3,
                                   fill=color, outline="", stipple="gray50" if False else "")
                c.create_text(x + 4, y + 4, text=b["type"][:3].upper(),
                              fill="#FFF", anchor="nw", font=("Consolas", 7))
        # bar lines
        for b in range(17):
            x = b * bp
            c.create_line(x, 0, x, 90, fill="#22222E")

    # ============================================================
    # TRANSPORT / PLAYBACK
    # ============================================================
    def _set_bpm(self):
        try:
            bpm = int(float(self.bpm_entry.get()))
        except Exception:
            return
        self.project.bpm = max(60, min(180, bpm))
        self.engine.mark_dirty()

    def _toggle_play(self):
        if self._playing:
            self._stop()
        else:
            self._play()

    def _play(self):
        if not HAS_AUDIO:
            self.pos_lbl.configure(text="audio yok")
            return
        self.engine.play()
        self._playing = True
        self.play_btn.configure(text="⏸", fg_color=AMBER)
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def _stream_loop(self):
        try:
            gen = self.engine.iter_stream(chunk_size=1024)
            with sd.OutputStream(samplerate=self.sr, channels=2, dtype="float32",
                                 blocksize=1024) as stream:
                for block in gen:
                    stream.write(block)
        except Exception as exc:
            self.after(0, lambda: self.pos_lbl.configure(text=f"play hata: {exc}"))

    def _stop(self):
        self.engine.stop()
        self._playing = False
        self.play_btn.configure(text="▶", fg_color=GREEN)
        self.pos_lbl.configure(text="0:00")

    def _poll(self):
        if self._playing:
            bar = self.engine.playhead
            total = self.project.arrangement_length() * bpm_to_seconds(self.project.bpm)
            self.pos_lbl.configure(text=f"{int(bar // 60)}:{int(bar % 60):02d}")
        self._poll_job = self.after(200, self._poll)

    # ============================================================
    # SAVE / LOAD / EXPORT
    # ============================================================
    def _save(self):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        path = filedialog.asksaveasfilename(
            initialdir=PROJECTS_DIR, defaultextension=".json",
            initialfile=f"{self.project.name}.json",
            filetypes=[("DAW Project", "*.json")])
        if not path:
            return
        self.project.name = os.path.splitext(os.path.basename(path))[0]
        self.project.save(path)
        self.pos_lbl.configure(text="kaydedildi ✓")

    def _load(self):
        path = filedialog.askopenfilename(
            initialdir=PROJECTS_DIR, filetypes=[("DAW Project", "*.json")])
        if not path:
            return
        try:
            self.project = DAWProject().load(path)
            self.engine.project = self.project
            self.engine.mark_dirty()
            self.bpm_entry.delete(0, "end")
            self.bpm_entry.insert(0, str(int(self.project.bpm)))
            self._selected_track = self.project.tracks[0].name if self.project.tracks else None
            if self._selected_track:
                self._select_track(self._selected_track)
            self._refresh_all()
            self.pos_lbl.configure(text="yüklendi ✓")
        except Exception as exc:
            messagebox.showerror("DAW", f"yükleme hatası: {exc}")

    def _export(self):
        path = filedialog.asksaveasfilename(
            initialdir="DJ_EXPORTS", defaultextension=".wav",
            initialfile=f"{self.project.name}_mix.wav",
            filetypes=[("WAV", "*.wav")])
        if not path:
            return
        try:
            res = self.engine.export_wav(path, stems_dir=STEMS_DIR)
            self.pos_lbl.configure(
                text=f"export ✓ {len(res['stems'])} stem + mix")
        except Exception as exc:
            messagebox.showerror("DAW", f"export hatası: {exc}")

    # ============================================================
    # REFRESH
    # ============================================================
    def from_beat_result(self, result):
        """Build a DAW project from a BeatStudio.generate() result."""
        patterns = result.get("pattern") or {}
        if not patterns:
            return False
        self.project = DAWProject(bpm=int(result.get("bpm", 126)))
        inst_map = {
            "kick": "kick_tech", "hat": "hat_tech", "hat_up": "hat_tech",
            "snare": "snare", "clap": "clap", "perc": "perc",
            "bass": "bass_roll", "pad": "pad_tech", "arp": "arp_pluck",
            "tick": "tick", "tom": "tom",
        }
        for ch, pattern in patterns.items():
            inst = inst_map.get(ch, "bass_roll")
            tr = self.project.add_track(ch, inst, pattern)
            if ch == "bass":
                tr.note_root = 36
            self.project.add_block("pattern", ch, 0, 4)
        # if there's a lead/pad, give it a midi clip too
        for ch in ("pad", "arp"):
            if ch in patterns and patterns[ch]:
                self.project.add_block("midi", ch, 0, 4)
        self.engine.project = self.project
        self.engine.mark_dirty()
        self.bpm_entry.delete(0, "end")
        self.bpm_entry.insert(0, str(int(self.project.bpm)))
        self._selected_track = self.project.tracks[0].name if self.project.tracks else None
        if self._selected_track:
            self._select_track(self._selected_track)
        else:
            self._refresh_all()
        return True

    def _refresh_all(self):
        self._rebuild_track_rows()
        self._rebuild_mixer()
        self._refresh_piano_roll()
        self._refresh_arrangement()

    def destroy(self):
        self._stop()
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
        super().destroy()


def bpm_to_seconds(bpm):
    return 60.0 / bpm
