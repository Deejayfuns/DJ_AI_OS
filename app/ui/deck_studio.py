"""
DJ AI OS — Deck Studio (Virtual DJ / Rekordbox style, 4-deck)

A 4-deck DJ interface driven by the FourDeckEngine. Looks like a modern
Virtual DJ / Rekordbox layout:

  ┌──────────────┬──────────────┐
  │ DECK A       │ DECK B       │
  │ wave + pads  │ wave + pads  │
  ├──────────────┼──────────────┤
  │ DECK C       │ DECK D       │
  │ (layer 2)    │ (layer 2)    │
  ├──────────────┴──────────────┤
  │ MIXER: crossfader + EQ/fader │
  └─────────────────────────────┘

Hardware: a Pioneer XDJ-RR/RX2 HID controller (when connected) drives
jog/tempo/buttons/pads/crossfader live. No hardware present = fully
usable with mouse (simulated position clocks).
"""

import hashlib
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, BORDER_LIGHT, RED, RED_HOVER,
    GREEN, GREEN_DIM, AMBER, BLUE_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_DIM, F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)

from app.ai.four_deck_engine import FourDeckEngine
from app.ai.hid_engine import HIDDeckController, discover_devices

# XDJ-RR MIDI note map: note -> (kind, deck, control)
# Populated from live calibration; transport/pads follow the Pioneer
# DDJ-family convention (deck A low notes, deck B high notes).
XDJRR_MAP = {
    # transport (A/B)
    36: ("play", "A", None), 37: ("cue", "A", None), 38: ("sync", "A", None),
    40: ("play", "B", None), 41: ("cue", "B", None), 42: ("sync", "B", None),
    # hot cue pads (8 per deck)
    **{n: ("pad", "A", i) for i, n in enumerate(range(60, 68))},
    **{n: ("pad", "B", i) for i, n in enumerate(range(72, 80))},
}


class DeckCard(ctk.CTkFrame):
    """One deck: transport + position + hot cue pads."""

    PAD_COLORS = [RED, AMBER, GREEN, BLUE_BRIGHT, "#9B59B6", "#E91E63",
                  "#00BCD4", "#8BC34A"]

    def __init__(self, master, deck_id, engine, on_pad=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BORDER)
        self.deck_id = deck_id
        self.engine = engine
        self.deck = engine.decks[deck_id]
        self.on_pad = on_pad or (lambda *a: None)

        # header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))
        ctk.CTkLabel(hdr, text=f"DECK {deck_id}", font=F_H3,
                     text_color=RED if deck_id in ("A", "B") else BLUE_BRIGHT).pack(side="left")
        self.state_lbl = ctk.CTkLabel(hdr, text="EMPTY", font=F_MONO,
                                      text_color=TEXT_DIM, fg_color=BG,
                                      corner_radius=3, padx=6, pady=2)
        self.state_lbl.pack(side="right")

        # track title
        self.title_lbl = ctk.CTkLabel(self, text="—", font=F_BODY_BOLD,
                                      text_color=TEXT_PRIMARY, anchor="w", wraplength=280)
        self.title_lbl.pack(fill="x", padx=8, pady=(0, 2))
        self.meta_lbl = ctk.CTkLabel(self, text="", font=F_META, text_color=TEXT_DIM, anchor="w")
        self.meta_lbl.pack(fill="x", padx=8)

        # waveform canvas
        self.wave_canvas = tk.Canvas(self, height=48, bg="#0E0E16", highlightthickness=0)
        self.wave_canvas.pack(fill="x", padx=8, pady=(2, 2))
        self._wave_data = None

        # position
        self.pos_lbl = ctk.CTkLabel(self, text="0:00 / 0:00", font=F_MONO,
                                    text_color=TEXT_SECONDARY)
        self.pos_lbl.pack(fill="x", padx=8, pady=(0, 0))
        self.pos_slider = ctk.CTkSlider(self, from_=0, to=1000, command=self._on_seek)
        self.pos_slider.pack(fill="x", padx=8, pady=(0, 4))

        # transport
        tr = ctk.CTkFrame(self, fg_color="transparent")
        tr.pack(fill="x", padx=8, pady=2)
        for text, cmd in (("▶", self._play), ("⏸", self._pause), ("⏹", self._stop),
                          ("CUE", self._cue), ("SYNC", self._sync)):
            ctk.CTkButton(tr, text=text, width=40, height=28, corner_radius=3,
                          fg_color=SURFACE_RAISED, hover_color=BORDER,
                          text_color=TEXT_SECONDARY, font=F_META,
                          command=cmd).pack(side="left", padx=1)

        # tempo
        trow = ctk.CTkFrame(self, fg_color="transparent")
        trow.pack(fill="x", padx=8, pady=(2, 0))
        ctk.CTkLabel(trow, text="TMP", font=("Consolas", 8), text_color=TEXT_DIM,
                     width=30).pack(side="left")
        self.tempo_slider = ctk.CTkSlider(trow, from_=0, to=200, command=self._on_tempo)
        self.tempo_slider.set(100)
        self.tempo_slider.pack(side="left", fill="x", expand=True, padx=4)
        self.bpm_lbl = ctk.CTkLabel(trow, text="—", font=F_MONO, text_color=AMBER, width=52)
        self.bpm_lbl.pack(side="left")

        # hot cue pads 2x4
        pads = ctk.CTkFrame(self, fg_color="transparent")
        pads.pack(fill="x", padx=8, pady=4)
        self.pad_btns = []
        for r in range(2):
            rowf = ctk.CTkFrame(pads, fg_color="transparent")
            rowf.pack(fill="x")
            for c in range(4):
                idx = r * 4 + c
                b = ctk.CTkButton(
                    rowf, text=f"{idx + 1}", width=56, height=26, corner_radius=3,
                    fg_color=SURFACE_RAISED, hover_color=BORDER,
                    text_color=TEXT_DIM, font=("Consolas", 9), border_width=1,
                    border_color=BORDER,
                    command=lambda p=idx: self._pad(p))
                b.pack(side="left", padx=1, pady=1)
                self.pad_btns.append(b)

    # ---- transport handlers ----
    def _play(self):
        if not self.deck.loaded:
            return
        self.deck.play()

    def _pause(self):
        if self.deck.loaded:
            self.deck.pause()

    def _stop(self):
        if self.deck.loaded:
            self.deck.stop()

    def _cue(self):
        if self.deck.loaded:
            self.deck.back_to_cue()

    def _sync(self):
        if self.deck.loaded:
            self.engine._sync_deck(self.deck)

    def _on_seek(self, val):
        if self.deck.length:
            self.deck.seek(val / 1000.0 * self.deck.length)

    def _on_tempo(self, val):
        self.deck.set_tempo(val / 100.0)
        self._refresh_bpm()

    def _pad(self, idx):
        if not self.deck.loaded:
            return
        self.on_pad(self.deck_id, idx)
        if idx in self.deck.hot_cues:
            self.deck.trigger_hot_cue(idx)
        else:
            self.deck.set_hot_cue(idx)
        self._refresh_pads()

    # ---- waveform ----
    def _load_wave(self, track):
        """Use the track's waveform data if present, else a deterministic shape."""
        data = track.get("waveform") or track.get("wave") or None
        if data:
            vals = [abs(float(v or 0)) for v in data]
            if vals:
                peak = max(vals) or 1.0
                self._wave_data = [v / peak for v in vals]
                return
        # deterministic pseudo-waveform from track name hash
        import hashlib
        seed = hashlib.md5(
            (track.get("title") or track.get("name") or "").encode()).digest()
        rng = seed[0] * 251 + seed[1] * 47 + seed[2]
        n = 220
        out = []
        for i in range(n):
            phase = i / n
            base = abs(0.5 + 0.5 * math.sin(phase * 6.28 * (3 + rng % 4) + rng))
            env = 0.35 + 0.65 * (0.4 + 0.6 * abs(math.sin(phase * 3.14)))
            out.append(base * env * (0.5 + (i * 2654435761) % 5 / 8.0))
        self._wave_data = out

    def _draw_wave(self):
        c = self.wave_canvas
        c.delete("all")
        w = c.winfo_width()
        h = 48
        if w < 10:
            return
        data = self._wave_data or []
        if not data:
            c.create_text(w // 2, h // 2, text="—", fill="#555570", font=("Consolas", 10))
            return
        n = len(data)
        center = h / 2
        # played portion colored green, rest dim
        frac = 0.0
        if self.deck.length:
            frac = min(1.0, self.deck.position / self.deck.length)
        for i in range(0, n, 1):
            x0 = i / n * w
            x1 = (i + 1) / n * w
            amp = data[i] * (h / 2 - 3)
            played = (i / n) < frac
            color = "#2ECC71" if played else "#3A3A52"
            c.create_rectangle(x0, center - amp, x1, center + amp,
                               fill=color, outline="")
        # playhead
        ph_x = frac * w
        c.create_line(ph_x, 0, ph_x, h, fill="#F5A623", width=1)

    # ---- state refresh ----
    def refresh(self):
        d = self.deck
        if d.loaded:
            t = d.track or {}
            if t.get("title") or t.get("name"):
                self.title_lbl.configure(text=t.get("title") or t.get("name") or "?")
                key = t.get("key") or t.get("camelot") or ""
                bpm = t.get("bpm") or ""
                self.meta_lbl.configure(text=f"{key}  {bpm} BPM")
                self.state_lbl.configure(
                    text="PLAY" if d.playing else ("PAUSE" if d.paused else "LOADED"),
                    text_color=GREEN if d.playing else (AMBER if d.paused else TEXT_SECONDARY))
                if self._wave_data is None:
                    self._load_wave(t)
            else:
                self.title_lbl.configure(text="—")
                self.meta_lbl.configure(text="")
                self.state_lbl.configure(text="EMPTY", text_color=TEXT_DIM)
        else:
            self.title_lbl.configure(text="—")
            self.meta_lbl.configure(text="")
            self.state_lbl.configure(text="EMPTY", text_color=TEXT_DIM)
            self._wave_data = None

        m, s = int(d.position) // 60, int(d.position) % 60
        ml, sl = int(d.length) // 60, int(d.length) % 60
        self.pos_lbl.configure(text=f"{m}:{s:02d} / {ml}:{sl:02d}")
        if d.length:
            self.pos_slider.set(min(1000, int(d.position / d.length * 1000)))
        self._draw_wave()
        self._refresh_bpm()
        self._refresh_pads()

    def _refresh_bpm(self):
        t = self.deck.track or {}
        bpm = t.get("bpm") or 120
        self.bpm_lbl.configure(text=f"{bpm * self.deck.tempo:.1f}")

    def _refresh_pads(self):
        for i, b in enumerate(self.pad_btns):
            if i in self.deck.hot_cues:
                b.configure(fg_color=self.PAD_COLORS[i % 8],
                            text_color="#FFF", border_color=self.PAD_COLORS[i % 8])
            else:
                b.configure(fg_color=SURFACE_RAISED, text_color=TEXT_DIM,
                            border_color=BORDER)


class DeckStudioPanel(ctk.CTkFrame):
    """Full 4-deck studio with mixer + library browser + HID."""

    def __init__(self, master, win=None):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.win = win
        self.engine = FourDeckEngine(callback=self._on_engine_event)
        self.hid = None
        self._events = []          # UI-thread event backlog
        self._poll_job = None

        self.selected_deck = "A"
        self._build()
        self._refresh_all()
        self._try_hid()
        self._poll()

    # ============================================================
    # BUILD
    # ============================================================
    def _build(self):
        # ---- top bar ----
        top = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0)
        top.pack(fill="x")
        inner = ctk.CTkFrame(top, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(inner, text="DECK STUDIO", font=F_H3, text_color=RED).pack(side="left")
        self.hid_lbl = ctk.CTkLabel(inner, text="HID: ara...", font=F_META,
                                    text_color=TEXT_DIM, fg_color=BG,
                                    corner_radius=3, padx=8, pady=2)
        self.hid_lbl.pack(side="right", padx=6)
        ctk.CTkButton(inner, text="CALIBRATE", width=84, height=24, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=AMBER, command=self._toggle_calibrate).pack(side="right", padx=4)
        ctk.CTkButton(inner, text="LAYER", width=84, height=24, font=F_META,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      command=self._toggle_layer).pack(side="right", padx=4)
        self.layer_lbl = ctk.CTkLabel(inner, text="A/B", font=F_MONO,
                                      text_color=BLUE_BRIGHT, width=40)
        self.layer_lbl.pack(side="right")

        # ---- main: browser left + decks ----
        main = ctk.CTkFrame(self, fg_color=BG)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # browser
        browser = ctk.CTkFrame(main, fg_color=SURFACE, corner_radius=8, width=260)
        browser.pack(side="left", fill="y", padx=(0, 8))
        browser.pack_propagate(False)
        btop = ctk.CTkFrame(browser, fg_color="transparent")
        btop.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(btop, text="KAYNAK", font=F_META, text_color=TEXT_DIM).pack(side="left")
        ctk.CTkButton(btop, text="REKORDBOX XML", width=96, height=22, font=("Consolas", 8),
                      fg_color=SURFACE_RAISED, hover_color=BORDER, text_color=AMBER,
                      command=self._load_rekordbox).pack(side="right")
        self.rb_info = ctk.CTkLabel(browser, text="", font=("Consolas", 8),
                                    text_color=TEXT_DIM, anchor="w")
        self.rb_info.pack(fill="x", padx=8)
        self.playlist_combo = ctk.CTkComboBox(browser, values=["(kütüphane)"], height=24,
                                              font=("Consolas", 9),
                                              command=self._on_playlist_change)
        self.playlist_combo.set("(kütüphane)")
        self.playlist_combo.pack(fill="x", padx=8, pady=(2, 2))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._reload_browser())
        se = ctk.CTkEntry(browser, textvariable=self.search_var, height=26,
                          font=F_META, placeholder_text="ara...")
        se.pack(fill="x", padx=8, pady=(0, 4))
        self.track_list = tk.Listbox(
            browser, bg="#14141E", fg="#F0F0F5", selectbackground=RED,
            selectforeground="#FFF", font=("Segoe UI", 10),
            highlightthickness=0, bd=0)
        self.track_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.track_list.bind("<Double-Button-1>", self._load_dbl)
        self.track_list.bind("<<ListboxSelect>>", lambda e: None)

        # decks area
        decks_area = ctk.CTkFrame(main, fg_color=BG)
        decks_area.pack(side="left", fill="both", expand=True)

        grid = ctk.CTkFrame(decks_area, fg_color=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1, uniform="d")
        grid.rowconfigure((0, 1), weight=1, uniform="d")
        self.cards = {}
        for i, did in enumerate(("A", "B", "C", "D")):
            r, c = i // 2, i % 2
            card = DeckCard(grid, did, self.engine, on_pad=self._on_pad)
            card.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)
            self.cards[did] = card

        # ---- mixer ----
        mixer = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=8, height=88)
        mixer.pack(fill="x", padx=8, pady=(0, 8))
        self._build_mixer(mixer)

    def _build_mixer(self, mixer):
        inner = ctk.CTkFrame(mixer, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(inner, text="MIXER", font=F_META, text_color=TEXT_DIM).grid(
            row=0, column=0, rowspan=3, sticky="w", padx=(0, 8))

        # channel faders for active pair
        self.fader_a = self._mixer_slider(inner, 0, 1, "CH A", 100, self._on_fader_a)
        self.fader_b = self._mixer_slider(inner, 1, 1, "CH B", 100, self._on_fader_b)

        # EQ band sliders (hi/mid/low per active pair) — compact 3 rows
        self.eq_hi_a = self._mixer_slider(inner, 0, 2, "HI A", 100, lambda v: self._on_eq("A", "hi", v))
        self.eq_mid_a = self._mixer_slider(inner, 0, 3, "MID A", 100, lambda v: self._on_eq("A", "mid", v))
        self.eq_low_a = self._mixer_slider(inner, 0, 4, "LOW A", 100, lambda v: self._on_eq("A", "low", v))
        self.eq_hi_b = self._mixer_slider(inner, 1, 2, "HI B", 100, lambda v: self._on_eq("B", "hi", v))
        self.eq_mid_b = self._mixer_slider(inner, 1, 3, "MID B", 100, lambda v: self._on_eq("B", "mid", v))
        self.eq_low_b = self._mixer_slider(inner, 1, 4, "LOW B", 100, lambda v: self._on_eq("B", "low", v))

        # crossfader
        cf = ctk.CTkFrame(inner, fg_color="transparent")
        cf.grid(row=0, column=6, rowspan=3, padx=12, sticky="ns")
        ctk.CTkLabel(cf, text="X-FADER", font=("Consolas", 8), text_color=TEXT_DIM).pack()
        self.xfader = ctk.CTkSlider(cf, from_=0, to=100, width=20, height=130,
                                    command=self._on_crossfader)
        self.xfader.pack(pady=2)
        self.xfader.set(50)

        # master volume
        mv = ctk.CTkFrame(inner, fg_color="transparent")
        mv.grid(row=0, column=7, rowspan=3, padx=8, sticky="ns")
        ctk.CTkLabel(mv, text="MASTER", font=("Consolas", 8), text_color=TEXT_DIM).pack()
        self.master_slider = ctk.CTkSlider(mv, from_=0, to=100, width=20, height=130,
                                           command=lambda v: self.engine.set_master_volume(v / 100))
        self.master_slider.pack(pady=2)
        self.master_slider.set(100)

    def _mixer_slider(self, parent, row, col, label, hi, cmd):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, padx=6, sticky="ns")
        ctk.CTkLabel(f, text=label, font=("Consolas", 7), text_color=TEXT_DIM).pack()
        s = ctk.CTkSlider(f, from_=0, to=hi, width=20, height=120, command=cmd)
        s.pack(pady=2)
        s.set(hi)
        return s

    # ============================================================
    # MIXER HANDLERS
    # ============================================================
    def _on_fader_a(self, v):
        self.engine.fader("A", v / 100)

    def _on_fader_b(self, v):
        self.engine.fader("B", v / 100)

    def _on_eq(self, side, band, v):
        self.engine.eq(side, band, (v - 50) / 50)

    def _on_crossfader(self, v):
        self.engine.crossfade(v / 100)

    def _toggle_layer(self):
        layer = self.engine.toggle_layer()
        self.layer_lbl.configure(text="C/D" if layer == 2 else "A/B")
        self._refresh_all()

    # ============================================================
    # LIBRARY / LOAD
    # ============================================================
    def _library(self):
        if getattr(self, "_rb_tracks", None):
            return self._rb_tracks
        if self.win:
            return (self.win.library or self.win.saved_tracks or [])
        return []

    def _load_rekordbox(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Rekordbox XML seç",
            filetypes=[("Rekordbox XML", "*.xml"), ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            from app.core.rekordbox_import import RekordboxImporter
            imp = RekordboxImporter()
            self._rb_all_tracks, self._rb_playlists = imp.parse(path)
            if not self._rb_playlists:
                self._rb_tracks = self._rb_all_tracks
                self.rb_info.configure(
                    text=f"Rekordbox: {len(self._rb_tracks)} track")
                self.playlist_combo.configure(values=["(kütüphane)"])
                self._reload_browser()
            else:
                names = ["(kütüphane)"] + [p["name"].split("/")[-1]
                                           for p in self._rb_playlists]
                self.playlist_combo.configure(values=names)
                self.playlist_combo.set(names[0])
                self._rb_tracks = self._rb_all_tracks
                self.rb_info.configure(
                    text=f"Rekordbox: {len(self._rb_all_tracks)} track, "
                         f"{len(self._rb_playlists)} playlist")
                self._reload_browser()
        except Exception as exc:
            self.rb_info.configure(text=f"XML hata: {exc}")

    def _on_playlist_change(self, name):
        if not getattr(self, "_rb_playlists", None):
            return
        if name == "(kütüphane)":
            self._rb_tracks = self._rb_all_tracks
        else:
            for i, pl in enumerate(self._rb_playlists):
                if pl["name"].split("/")[-1] == name:
                    from app.core.rekordbox_import import RekordboxImporter
                    self._rb_tracks = RekordboxImporter().playlist_tracks(
                        self._rb_playlists, i, self._rb_all_tracks)
                    break
        self._reload_browser()

    def _reload_browser(self):
        q = self.search_var.get().lower()
        lib = self._library()
        self.track_list.delete(0, "end")
        self._browser_tracks = []
        for t in lib:
            title = (t.get("title") or t.get("name") or "")
            artist = t.get("artist") or ""
            if q and q not in f"{title} {artist}".lower():
                continue
            self._browser_tracks.append(t)
            self.track_list.insert("end", f"{title} — {artist}")
        if not hasattr(self, "_browser_tracks"):
            self._browser_tracks = []

    def _load_dbl(self, _evt):
        sel = self.track_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._browser_tracks):
            self.load_to_deck(self.selected_deck, self._browser_tracks[idx])

    def select_deck(self, deck_id):
        self.selected_deck = deck_id
        self.set_status(f"Hedef deck: {deck_id}")

    def load_to_deck(self, deck_id, track):
        d = self.engine.decks[deck_id]
        d.load(track)
        self.cards[deck_id].refresh()

    def set_status(self, msg):
        self.hid_lbl.configure(text=msg)

    # ============================================================
    # PADS
    # ============================================================
    def _on_pad(self, deck_id, idx):
        self.engine.decks[deck_id].set_hot_cue(idx)

    # ============================================================
    # HID + MIDI
    # ============================================================
    def _try_hid(self):
        devs = discover_devices()
        if not devs:
            self._try_midi()   # XDJ-RR/RX2 control over MIDI, HID is display
            return
        dev = devs[0]
        self.hid = HIDDeckController(device=dev, callback=self._on_hid_event)
        ok = self.hid.start()
        # XDJ-RR/RX2: control data is MIDI even though a HID interface exists
        midi_ok = self._try_midi(silent=True)
        if ok:
            self.hid_lbl.configure(
                text=f"HID: {dev['product']} bagli"
                     + (" + MIDI" if midi_ok else ""), text_color=GREEN)
        elif midi_ok:
            self.hid_lbl.configure(text="MIDI: XDJ-RR bagli", text_color=GREEN)
        else:
            self.hid_lbl.configure(
                text=f"HID: {self.hid.connection_error}", text_color=AMBER)

    def _try_midi(self, silent=False):
        """Open the Pioneer XDJ-RR MIDI input and listen for controls."""
        try:
            import mido
            if "Pioneer DJ XDJ-RR MIDI" not in " ".join(mido.get_input_names()):
                return False
            port_name = [p for p in mido.get_input_names()
                         if "XDJ-RR" in p][0]
            self._midi_in = mido.open_input(port_name)
            self._midi_listening = True
            self._midi_thread = threading.Thread(target=self._midi_loop,
                                                 daemon=True)
            self._midi_thread.start()
            if not silent:
                self.hid_lbl.configure(text=f"MIDI: {port_name}", text_color=GREEN)
            return True
        except Exception:
            return False

    def _midi_loop(self):
        while getattr(self, "_midi_listening", False) and self._midi_in:
            try:
                msg = self._midi_in.receive(timeout=0.1)
                if msg is not None:
                    self._events.append(("midi", msg))
            except Exception:
                continue

    def _toggle_calibrate(self):
        if not self.hid:
            self.set_status("HID yok — kalibre edilemez")
            return
        if self.hid._calibrate:
            self.hid.stop_calibrate()
            self.set_status("Kalibrasyon durdu")
        else:
            self.hid.start_calibrate()
            self.set_status("KALIBRASYON: donanimda kontrol calistir...")

    def _on_hid_event(self, evt):
        # thread-safe: stash for UI thread
        self._events.append(evt)
        # layer/browser handled immediately if cheap
        if evt.get("type") in ("button", "pad", "layer"):
            try:
                self.engine.handle_hid_event(evt)
            except Exception:
                pass

    # ============================================================
    # MIDI EVENT ROUTING (XDJ-RR)
    # ============================================================
    def _handle_midi(self, msg):
        """Route a MIDI message from the XDJ-RR to deck operations."""
        try:
            from app.ai.xdj_rr_midi import translate
            layer = self.engine.layer  # 1 or 2
            evt = translate(msg, layer=layer)
            if evt is None:
                return
            self._route_translated(evt)
        except Exception:
            pass

    def _route_translated(self, evt):
        t = evt.get("type")
        deck_id = evt.get("deck")
        val = evt.get("value", 0)
        # Track tempo coarse values per deck for 14-bit combination
        if not hasattr(self, "_tempo_coarse"):
            self._tempo_coarse = {}
        if t == "play":
            d = self.engine.decks.get(deck_id)
            if d:
                if d.playing:
                    d.pause()
                else:
                    d.play()
                self.selected_deck = deck_id
        elif t == "cue":
            d = self.engine.decks.get(deck_id)
            if d and d.loaded:
                d.back_to_cue()
        elif t == "sync":
            d = self.engine.decks.get(deck_id)
            if d and d.loaded:
                self.engine._sync_deck(d)
        elif t == "pad":
            d = self.engine.decks.get(deck_id)
            idx = evt.get("pad")
            if d and idx is not None:
                if idx in d.hot_cues:
                    d.trigger_hot_cue(idx)
                else:
                    d.set_hot_cue(idx)
        elif t == "jog":
            d = self.engine.decks.get(deck_id)
            if d and d.loaded:
                d.seek(d.position + evt.get("delta", 0) * 0.001)
        # === Tempo fader (14-bit: coarse CC33 + fine CC48) ===
        elif t == "tempo_coarse":
            self._tempo_coarse[deck_id] = val
        elif t == "tempo_fine":
            coarse = self._tempo_coarse.get(deck_id, 64)
            # Combine 14-bit: coarse (7 bits) << 7 | fine (7 bits)
            combined = (coarse << 7) | val
            # 0-16383 -> tempo 0.5-2.0 (center 8192 = 1.0)
            tempo = 0.5 + (combined / 16383.0) * 1.5
            d = self.engine.decks.get(deck_id)
            if d:
                d.set_tempo(tempo)
        # === Mixer / Deck controls (from CC_MAP) ===
        elif t == "tempo":
            d = self.engine.decks.get(deck_id)
            if d:
                # value 0..1 -> tempo 0.5..2.0
                d.set_tempo(0.5 + val * 1.5)
        elif t == "eq_hi":
            d = self.engine.decks.get(deck_id)
            if d:
                d.eq["hi"] = val * 2.0 - 1.0  # -1..1
        elif t == "eq_mid":
            d = self.engine.decks.get(deck_id)
            if d:
                d.eq["mid"] = val * 2.0 - 1.0
        elif t == "eq_low":
            d = self.engine.decks.get(deck_id)
            if d:
                d.eq["low"] = val * 2.0 - 1.0
        elif t == "filter":
            d = self.engine.decks.get(deck_id)
            if d:
                d.filter = val * 2.0 - 1.0
        elif t == "fader":
            d = self.engine.decks.get(deck_id)
            if d:
                d.volume = val
        elif t == "crossfader":
            self.engine.crossfade(val)
        elif t in ("fader_ch1", "fader_ch2"):
            target_deck = self.engine.active_pair[0] if t == "fader_ch1" else self.engine.active_pair[1]
            d = self.engine.decks.get(target_deck)
            if d:
                d.volume = val
        elif t == "shift":
            pass

    # ============================================================
    # ENGINE / UI REFRESH
    # ============================================================
    def _on_engine_event(self, evt):
        pass  # polling handles refresh

    def _refresh_all(self):
        for did, card in self.cards.items():
            card.refresh()

    def _poll(self):
        # drain HID + MIDI events -> engine
        while self._events:
            evt = self._events.pop(0)
            if isinstance(evt, tuple) and evt[0] == "midi":
                self._handle_midi(evt[1])
            else:
                self.engine.handle_hid_event(evt)
        self._refresh_all()
        self._poll_job = self.after(150, self._poll)

    def destroy(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
        self._midi_listening = False
        if getattr(self, "_midi_in", None):
            try:
                self._midi_in.close()
            except Exception:
                pass
        if self.hid:
            self.hid.stop()
        self.engine.stop_all()
        super().destroy()
