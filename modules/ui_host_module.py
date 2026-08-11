"""
ORB Module — UI Host (TRON DJ Studio)
=======================================
Neon-themed futuristic DJ Music Studio with real-time waveforms,
4-deck mixer, spectrum analyzer, and hot cue pads.
"""
import math
import tkinter as tk
import time
from typing import Any, Callable, Dict, List, Optional

from .base import OrbModule


class UiHostModule(OrbModule):
    """Neon UI host — TRON DJ Studio."""

    EVENT_TOPICS = ["orb.status", "orb.module_changed", "midi.event",
                    "midi.connected", "midi.disconnected"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="ui_host")
        self._root = None
        self._theme = None
        self._module_labels: Dict[str, tk.Label] = {}
        self._status_canvas = None
        self._event_log = None
        # DJ studio widgets
        self._wave_canvases = {}
        self._spectrum_canvas = None
        self._bpm_labels = {}
        self._state_labels = {}
        self._pad_buttons = {}
        self._mixer_widgets = {}
        self._anim_running = False
        self._frame_count = 0

    def start(self) -> None:
        from orb_core.neon import Theme, Glow as GlowCls
        self._theme = Theme("tron")
        self._glow = GlowCls
        self._running = True
        self._state = "running"
        self.log("neon theme ready")

    def stop(self) -> None:
        self._anim_running = False
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
        self._running = False
        self._state = "stopped"

    # ================================================================
    # UI BUILD
    # ================================================================
    def open_window(self, title: str = "DJ AI OS — ORB NEXUS") -> Optional[tk.Tk]:
        """Open TRON DJ Studio window."""
        if self._root:
            self._root.deiconify()
            return self._root

        from orb_core.neon import Theme, apply_ttk_theme, Glow

        self._theme = Theme("tron")
        th = self._theme
        root = tk.Tk()
        root.title(title)
        root.configure(bg=th.c("bg"))
        root.geometry("1280x760")
        root.minsize(1024, 600)
        self._root = root
        apply_ttk_theme(root, th)

        self._anim_running = True

        # ──── HEADER ────
        self._build_header(root, th)

        # ──── NOTEBOOK (Tabbed Interface) ────
        self._notebook_frame = tk.Frame(root, bg=th.c("bg"))
        self._notebook_frame.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # TAB BAR
        tab_bar = tk.Frame(self._notebook_frame, bg=th.c("bg_dark"))
        tab_bar.pack(fill="x")
        self._tabs = {}
        self._current_tab = "DJ_STUDIO"
        tab_data = [
            ("DJ_STUDIO", "DJ STUDIO", th.c("accent")),
            ("BEAT_DAW", "BEAT STUDIO", th.c("accent2")),
            ("MODULES", "MODULES", th.c("accent3")),
        ]
        for key, label, color in tab_data:
            btn = tk.Label(tab_bar, text=f"  ◢{label}◣  ", bg=th.c("bg_dark"),
                          fg=color, font=("Consolas", 10, "bold"), cursor="hand2")
            btn.pack(side="left", padx=4, pady=4)
            btn.bind("<Button-1>", lambda e, k=key: self._switch_tab(k))
            self._tabs[key] = btn

        # CONTENT AREA (swappable)
        self._content_frame = tk.Frame(self._notebook_frame, bg=th.c("bg"))
        self._content_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Build sub-views
        # Tab frames (packed/unpacked on switch)
        self._tab_frames = {}
        self._build_dj_studio_tab()
        self._build_beat_daw_tab()
        self._build_modules_tab()
        self._switch_tab("DJ_STUDIO")

        # ──── FOOTER ────
        self._build_footer(root, th)

        # Start real-time animation loop
        self._animate()

        return root

    # ================================================================
    # TAB MANAGEMENT
    # ================================================================
    def _switch_tab(self, tab_key):
        self._current_tab = tab_key
        for key, frame in self._tab_frames.items():
            if key == tab_key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        # Highlight active tab
        for key, btn in self._tabs.items():
            th = self._theme
            if key == tab_key:
                btn.configure(bg=th.c("bg_panel"), fg=th.c("fg_bright"))
            else:
                btn.configure(bg=th.c("bg_dark"))

    def _build_dj_studio_tab(self):
        th = self._theme
        frame = tk.Frame(self._content_frame, bg=th.c("bg"))
        self._tab_frames["DJ_STUDIO"] = frame

        # LEFT: 4 DECKS
        decks_frame = tk.Frame(frame, bg=th.c("bg"))
        decks_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self._build_deck_grid(decks_frame, th)

        # RIGHT: MIXER + SPECTRUM + HOT CUES
        right = tk.Frame(frame, bg=th.c("bg"))
        right.pack(side="right", fill="both", expand=True)
        self._build_mixer(right, th)
        self._build_spectrum(right, th)
        self._build_hot_cues(right, th)

    def _build_beat_daw_tab(self):
        """Beat Studio DAW view: pattern sequencer + track list."""
        th = self._theme
        frame = tk.Frame(self._content_frame, bg=th.c("bg"))
        self._tab_frames["BEAT_DAW"] = frame

        # Track browser (left)
        browser = tk.Frame(frame, bg=th.c("bg_panel"), highlightthickness=1,
                          highlightbackground=th.c("border"))
        browser.pack(side="left", fill="y", padx=(0, 4), pady=4)

        tk.Label(browser, text="TRACK BROWSER", bg=th.c("bg_panel"),
                fg=th.c("accent2"), font=("Consolas", 10, "bold")).pack(anchor="w", padx=6, pady=(6, 2))

        # Search box
        search = tk.Entry(browser, bg=th.c("bg_dark"), fg=th.c("fg"),
                         insertbackground=th.c("accent"), font=("Consolas", 9),
                         relief="flat", highlightthickness=1, highlightbackground=th.c("border"))
        search.pack(fill="x", padx=6, pady=(0, 4))

        # Track listbox
        listbox = tk.Listbox(browser, bg=th.c("bg_dark"), fg=th.c("fg"),
                            selectbackground=th.c("accent"),
                            selectforeground=th.c("bg_dark"),
                            font=("Consolas", 9), relief="flat",
                            highlightthickness=0, bd=0)
        listbox.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Sample tracks
        sample_tracks = [
            "Gianluca Colletti - Baobab",
            "Hugel & Dystinct - Yama By Night",
            "Black Coffee - Drive",
            "Carl Cox - I Want You Forever",
            "Deadmau5 - Strobe",
            "Jamie xx - Gosh",
            "Daft Punk - Around The World",
            "Fisher - Lose It",
            "CamelPhat & Elderbrook - Cola",
            "Fisher - Losing It",
        ]
        for track in sample_tracks:
            listbox.insert("end", track)

        # Pattern editor (right)
        editor = tk.Frame(frame, bg=th.c("bg"))
        editor.pack(side="right", fill="both", expand=True)

        tk.Label(editor, text="PATTERN SEQUENCER", bg=th.c("bg"),
                fg=th.c("accent"), font=("Consolas", 10, "bold")).pack(anchor="w", padx=6, pady=(4, 2))

        # Step sequencer grid (16 steps)
        seq = tk.Frame(editor, bg=th.c("bg"))
        seq.pack(fill="x", padx=6, pady=4)

        # Channel names
        channels = ["KICK", "SNARE", "CLAP", "HIHAT", "BASS", "PLUCK", "PAD", "PERC"]
        self._seq_buttons = {}

        for i, ch in enumerate(channels):
            lbl = tk.Label(seq, text=f"{ch:>6}", bg=th.c("bg_panel"),
                          fg=th.c("accent") if ch in ("KICK", "BASS") else th.c("accent3"),
                          font=("Consolas", 9))
            lbl.grid(row=i, column=0, padx=2, sticky="e")
            self._seq_buttons[ch] = []
            for step in range(16):
                # Checkerboard for visual guidance
                is_beat = step % 4 == 0
                is_offbeat = step % 2 == 1
                bg = th.c("bg_panel") if is_beat else th.c("bg_panel_alt")
                if is_offbeat:
                    bg = th.c("bg_dark")

                btn = tk.Canvas(seq, width=22, height=20, bg=bg,
                               highlightthickness=1,
                               highlightbackground=th.c("border"))
                btn.grid(row=i, column=step + 1, padx=1, pady=1)
                self._seq_buttons[ch].append(btn)

        # Step numbers
        numbers = tk.Frame(seq, bg=th.c("bg"))
        numbers.grid(row=len(channels), column=0, columnspan=17)
        tk.Label(numbers, text="", bg=th.c("bg"), width=6).pack(side="left")
        for step in range(16):
            c = th.c("accent") if step % 4 == 0 else th.c("fg_dim")
            tk.Label(numbers, text=f"{step+1:2d}", bg=th.c("bg"),
                    fg=c, font=("Consolas", 7)).pack(side="left")

        # Bottom: BPM + swing + pattern controls
        ctrl = tk.Frame(editor, bg=th.c("bg_panel"), highlightthickness=1,
                       highlightbackground=th.c("border"))
        ctrl.pack(fill="x", padx=6, pady=4)

        tk.Label(ctrl, text="PATTERN CONTROLS", bg=th.c("bg_panel"),
                fg=th.c("accent"), font=("Consolas", 9, "bold")).pack(anchor="w", padx=6, pady=4)

        # BPM
        bpm_f = tk.Frame(ctrl, bg=th.c("bg_panel"))
        bpm_f.pack(fill="x", padx=6, pady=2)
        tk.Label(bpm_f, text="BPM", bg=th.c("bg_panel"), fg=th.c("fg_dim"),
                font=("Consolas", 9)).pack(side="left")
        self._daw_bpm = tk.Label(bpm_f, text="128", bg=th.c("bg_dark"),
                                fg=th.c("accent"), font=("Consolas", 12, "bold"))
        self._daw_bpm.pack(side="left", padx=8)
        tk.Button(bpm_f, text="−", bg=th.c("bg_dark"), fg=th.c("accent"),
                 font=("Consolas", 10), relief="flat", width=3,
                 command=lambda: self._bpm_step(-1)).pack(side="left")
        tk.Button(bpm_f, text="+", bg=th.c("bg_dark"), fg=th.c("accent"),
                 font=("Consolas", 10), relief="flat", width=3,
                 command=lambda: self._bpm_step(1)).pack(side="left")

        # Genre presets
        genre_f = tk.Frame(ctrl, bg=th.c("bg_panel"))
        genre_f.pack(fill="x", padx=6, pady=2)
        tk.Label(genre_f, text="GENRE", bg=th.c("bg_panel"), fg=th.c("fg_dim"),
                font=("Consolas", 9)).pack(side="left")
        for g in ["house", "techno", "melodic", "dnb", "mars"]:
            btn = tk.Label(genre_f, text=f"  {g.upper()}  ", bg=th.c("bg_dark"),
                          fg=th.c("accent2"), font=("Consolas", 8), cursor="hand2")
            btn.pack(side="left", padx=2)
            btn.bind("<Button-1>", lambda e, genre=g: self._load_genre_preset(genre))

    def _bpm_step(self, delta):
        if hasattr(self, "_daw_bpm"):
            val = int(self._daw_bpm.cget("text")) + delta
            self._daw_bpm.configure(text=str(max(60, min(200, val))))

    def _load_genre_preset(self, genre):
        """Load a genre preset into the DAW sequencer."""
        # This would load from the beat_studio module's genre patterns
        # For now just update the BPM label
        bpm_map = {"house": 128, "techno": 135, "melodic": 126, "dnb": 174, "mars": 130}
        if hasattr(self, "_daw_bpm"):
            self._daw_bpm.configure(text=str(bpm_map.get(genre, 128)))

    def _build_modules_tab(self):
        th = self._theme
        frame = tk.Frame(self._content_frame, bg=th.c("bg"))
        self._tab_frames["MODULES"] = frame

        tk.Label(frame, text="MODULE GRID", bg=th.c("bg"),
                fg=th.c("accent"), font=("Consolas", 12, "bold")).pack(anchor="w", padx=8, pady=(8, 4))

        grid = tk.Frame(frame, bg=th.c("bg"))
        grid.pack(fill="both", expand=True, padx=8)

        self._module_labels = {}
        if self.kernel:
            for name, spec in sorted(self.kernel.modules.items()):
                row = tk.Frame(grid, bg=th.c("bg_panel"))
                row.pack(fill="x", padx=4, pady=2)
                dot = tk.Canvas(row, width=14, height=14, bg=th.c("bg_panel"), highlightthickness=0)
                dot.pack(side="left")
                color = th.c("success") if spec.state.value == "running" else th.c("disabled")
                dot.create_oval(3, 3, 11, 11, fill=color, outline="")
                lbl = tk.Label(row, text=f"{name}  v{spec.manifest.version}", bg=th.c("bg_panel"),
                              fg=th.c("fg") if spec.state.value == "running" else th.c("fg_dim"),
                              font=("Consolas", 10), anchor="w")
                lbl.pack(side="left", fill="x", expand=True)
                self._module_labels[name] = (dot, lbl)
        """Top bar: title, BPM display, clock, theme switcher."""
        header = tk.Frame(root, bg=th.c("bg_dark"))
        header.pack(fill="x", padx=8, pady=(8, 4))

        # Neon title
        tk.Label(header, text="◢ DJ AI OS — ORB ◣",
                 bg=th.c("bg_dark"), fg=th.c("accent"),
                 font=("Consolas", 18, "bold")).pack(side="left", padx=8)

        # BPM display
        bpm_f = tk.Frame(header, bg=th.c("bg_panel"), highlightthickness=1,
                         highlightbackground=th.c("accent"))
        bpm_f.pack(side="left", padx=12)
        self._bpm_canvas = tk.Canvas(bpm_f, width=120, height=28,
                                     bg=th.c("bg_panel"), highlightthickness=0)
        self._bpm_canvas.pack()
        self._bpm_canvas.create_text(60, 14, text="---",
                                     fill=th.c("accent"), font=("Consolas", 14, "bold"),
                                     tags="bpm")

        # Clock
        self._clock_lbl = tk.Label(header, text="", bg=th.c("bg_dark"),
                                   fg=th.c("fg_dim"), font=("Consolas", 11))
        self._clock_lbl.pack(side="right", padx=8)

        # Theme
        from orb_core.neon import NeonButton
        NeonButton(header, text="THEME", width=90, height=26, theme=self._theme,
                   accent="accent2", command=self._cycle_theme).pack(side="right", padx=8)
        # Status
        self._hdr_status = tk.Label(header, text="MIDI: ---", bg=th.c("bg_dark"),
                                    fg=th.c("fg_dim"), font=("Consolas", 9))
        self._hdr_status.pack(side="right", padx=8)

    def _build_deck_grid(self, parent, th):
        """4-deck waveform grid: DECK A/C left, B/D right."""
        grid = tk.Frame(parent, bg=th.c("bg"))
        grid.pack(fill="both", expand=True)

        for i, did in enumerate(["A", "B", "C", "D"]):
            row, col = divmod(i, 2)
            deck = tk.Frame(grid, bg=th.c("bg_panel"), highlightthickness=1,
                           highlightbackground=th.c("border"))
            deck.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            grid.columnconfigure(col, weight=1)
            grid.rowconfigure(row, weight=1)

            # header
            h = tk.Frame(deck, bg=th.c("bg_panel"))
            h.pack(fill="x", padx=6, pady=(6, 2))
            tk.Label(h, text=f"DECK {did}", bg=th.c("bg_panel"),
                    fg=th.c("accent") if did in ("A", "B") else th.c("accent2"),
                    font=("Consolas", 11, "bold")).pack(side="left")
            self._state_labels[did] = tk.Label(h, text="STOP", bg=th.c("bg_panel"),
                                               fg=th.c("fg_dim"), font=("Consolas", 8))
            self._state_labels[did].pack(side="right")

            # waveform canvas
            wc = tk.Canvas(deck, bg=th.c("bg_dark"), highlightthickness=1,
                          highlightbackground=th.c("border"), height=80)
            wc.pack(fill="x", padx=4, pady=2)
            self._wave_canvases[did] = wc

            # transport row
            tr = tk.Frame(deck, bg=th.c("bg_panel"))
            tr.pack(fill="x", padx=4, pady=(2, 6))

            # play/pause
            for txt, color in [("▶", th.c("success")), ("⏸", th.c("warning")),
                               ("⏹", th.c("fg_dim"))]:
                btn = tk.Canvas(tr, width=28, height=22, bg=th.c("bg_panel"),
                              highlightthickness=0)
                btn.pack(side="left", padx=2)
                btn.create_oval(1, 1, 27, 21, fill=th.c("bg_dark"),
                               outline=color, width=1)
                btn.create_text(14, 11, text=txt, fill=color, font=("Consolas", 9))

            # position / time
            tk.Label(tr, text="0:00", bg=th.c("bg_panel"), fg=th.c("fg_dim"),
                    font=("Consolas", 9)).pack(side="right", padx=4)

    def _build_mixer(self, parent, th):
        """Mixer section: faders + EQ + crossfader."""
        mixer = tk.Frame(parent, bg=th.c("bg_panel"), highlightthickness=1,
                        highlightbackground=th.c("border"))
        mixer.pack(fill="x", pady=(0, 4))

        tk.Label(mixer, text="MIXER", bg=th.c("bg_panel"),
                fg=th.c("accent2"), font=("Consolas", 10, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        # Channel strips
        strip_frame = tk.Frame(mixer, bg=th.c("bg_panel"))
        strip_frame.pack(fill="x", padx=8, pady=2)

        for did, name in [("A", "CH1"), ("B", "CH2"), ("C", "CH3"), ("D", "CH4")]:
            strip = tk.Frame(strip_frame, bg=th.c("bg_panel_alt"))
            strip.pack(side="left", fill="both", expand=True, padx=2, pady=2)
            self._mixer_widgets[did] = self._build_channel_strip(strip, did, name, th)

        # Crossfader (center)
        xf = tk.Frame(mixer, bg=th.c("bg_panel"))
        xf.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(xf, text="X-FADE", bg=th.c("bg_panel"), fg=th.c("fg_dim"),
                font=("Consolas", 9)).pack(side="left")
        xf_canvas = tk.Canvas(xf, width=160, height=20, bg=th.c("bg_panel"),
                              highlightthickness=1, highlightbackground=th.c("border"))
        xf_canvas.pack(side="left", padx=4)
        xf_canvas.create_line(10, 10, 150, 10, fill=th.c("border"), width=2)
        xf_canvas.create_rectangle(80, 3, 90, 17, fill=th.c("accent"), outline="",
                                  tags="xfader")
        self._mixer_widgets["xfader"] = xf_canvas

    def _build_channel_strip(self, parent, did, label, th):
        """Single channel strip: name, fader, EQ knobs."""
        c = tk.Frame(parent, bg=th.c("bg_panel_alt"))
        c.pack(fill="both", expand=True, padx=1)

        tk.Label(c, text=label, bg=th.c("bg_panel_alt"),
                fg=th.c("fg_dim"), font=("Consolas", 8)).pack(pady=(4, 2))

        # Volume fader (vertical canvas)
        fader = tk.Canvas(c, width=24, height=100, bg=th.c("bg_dark"),
                         highlightthickness=1, highlightbackground=th.c("border"))
        fader.pack(pady=2)
        fader.create_line(12, 5, 12, 95, fill=th.c("border"), width=2)
        # knob position (default mid)
        knob_y = 50
        fader.create_rectangle(4, knob_y - 4, 20, knob_y + 4, fill=th.c("accent"), outline="")
        fader.tag_bind("knob", "<B1-Motion>", lambda e, d=did: self._drag_fader(e, d, fader))

        # EQ knobs (tiny circles)
        eq_frame = tk.Frame(c, bg=th.c("bg_panel_alt"))
        eq_frame.pack(pady=4)
        for eq_label in ["HI", "MID", "LO"]:
            knob = tk.Canvas(eq_frame, width=18, height=18, bg=th.c("bg_panel_alt"),
                           highlightthickness=0)
            knob.pack(side="left", padx=2)
            knob.create_oval(1, 1, 17, 17, fill=th.c("bg_dark"),
                           outline=th.c("accent"), width=1)
            knob.create_text(9, 9, text=eq_label[0], fill=th.c("fg_dim"),
                           font=("Consolas", 6))

        return {"did": did, "fader": fader}

    def _drag_fader(self, event, did, canvas):
        """Drag volume fader."""
        y = max(5, min(95, event.y))
        canvas.delete("knob")
        canvas.create_rectangle(4, y - 4, 20, y + 4, fill=self._theme.c("accent"), tags="knob")
        vol = 1.0 - (y - 5) / 90.0
        # Map to deck volume via deck_studio module
        deck = self.get_module("deck_studio")
        if deck:
            d = deck._engine.decks.get(did) if deck._engine else None
            if d:
                d.volume = vol

    def _build_spectrum(self, parent, th):
        """Frequency spectrum analyzer."""
        sp = tk.Frame(parent, bg=th.c("bg_panel"), highlightthickness=1,
                     highlightbackground=th.c("border"))
        sp.pack(fill="x", pady=4)
        tk.Label(sp, text="SPECTRUM", bg=th.c("bg_panel"),
                fg=th.c("spectrum"), font=("Consolas", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 2))
        self._spectrum_canvas = tk.Canvas(sp, height=60, bg=th.c("bg_dark"),
                                         highlightthickness=1, highlightbackground=th.c("border"))
        self._spectrum_canvas.pack(fill="x", padx=8, pady=(0, 4))
        # Draw initial bars
        self._draw_spectrum_idle()

    def _build_hot_cues(self, parent, th):
        """Hot cue pads section."""
        hc = tk.Frame(parent, bg=th.c("bg_panel"), highlightthickness=1,
                     highlightbackground=th.c("border"))
        hc.pack(fill="x", pady=4)
        tk.Label(hc, text="HOT CUES", bg=th.c("bg_panel"),
                fg=th.c("accent3"), font=("Consolas", 9, "bold")).pack(anchor="w", padx=8, pady=(4, 2))

        cues_frame = tk.Frame(hc, bg=th.c("bg_panel"))
        cues_frame.pack(fill="x", padx=8, pady=(0, 6))

        cue_colors = [th.c("accent"), th.c("accent2"), th.c("accent3"),
                      th.c("accent4"), th.c("accent5"), th.c("success"),
                      th.c("warning"), th.c("danger")]

        self._pad_buttons = []
        for i in range(8):
            pad = tk.Canvas(cues_frame, width=50, height=36, bg=th.c("bg_dark"),
                           highlightthickness=1, highlightbackground=th.c("border"))
            pad.pack(side="left", padx=2)
            pad.create_rectangle(2, 2, 48, 34, fill=th.c("bg_dark"),
                               outline=cue_colors[i % 8], width=2)
            pad.create_text(25, 18, text=str(i + 1), fill=cue_colors[i % 8],
                           font=("Consolas", 10, "bold"))
            pad.bind("<Button-1>", lambda e, i=i: self._pad_click(i))
            self._pad_buttons.append(pad)

    def _build_footer(self, root, th):
        """Bottom status bar."""
        footer = tk.Frame(root, bg=th.c("bg_dark"), height=30)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        tk.Label(footer, text="ORB v0.1.0", bg=th.c("bg_dark"),
                fg=th.c("fg_dim"), font=("Consolas", 9)).pack(side="left", padx=8)
        self._footer_status = tk.Label(footer, text="MIDI: scanning...",
                                       bg=th.c("bg_dark"), fg=th.c("fg_dim"),
                                       font=("Consolas", 9))
        self._footer_status.pack(side="left", padx=8)

    # ================================================================
    # ANIMATION
    # ================================================================
    def _animate(self):
        """Real-time animation loop — waveform + spectrum + state."""
        if not self._anim_running or not self._root:
            return

        self._frame_count += 1
        th = self._theme

        # Clock
        now = time.strftime("%H:%M:%S")
        if hasattr(self, "_clock_lbl"):
            self._clock_lbl.configure(text=now)

        # Waveform simulation (animated sine-ish)
        for did, canvas in self._wave_canvases.items():
            self._draw_waveform(canvas, did)

        # Spectrum idle
        self._draw_spectrum_idle()

        # BPM flicker on header
        if self._frame_count % 30 == 0 and self._bpm_canvas is not None:
            deck = self.get_module("deck_studio")
            if deck and deck._engine:
                d = deck._engine.decks.get("A")
                if d and d.track:
                    bpm = getattr(d, "_native_bpm", d.track.get("bpm", 128))
                    self._bpm_canvas.delete("bpm")
                    self._bpm_canvas.create_text(60, 14, text=f"{bpm:.0f}",
                                                 fill=th.c("accent"),
                                                 font=("Consolas", 14, "bold"), tags="bpm")
                else:
                    self._bpm_canvas.delete("bpm")
                    self._bpm_canvas.create_text(60, 14, text="---",
                                                 fill=th.c("fg_dim"),
                                                 font=("Consolas", 14, "bold"), tags="bpm")

        # Deck states
        deck_mod = self.get_module("deck_studio")
        if deck_mod and deck_mod._engine:
            for did, lbl in self._state_labels.items():
                d = deck_mod._engine.decks.get(did)
                state = "PLAY" if d and d.playing else ("PAUSE" if d and d.paused else "STOP")
                color = th.c("success") if state == "PLAY" else th.c("warning") if state == "PAUSE" else th.c("fg_dim")
                lbl.configure(text=state, fg=color)

        # MIDI status
        midi = self.get_module("midi_engine")
        if midi and hasattr(self, "_hdr_status"):
            dev = midi.get_connected_device()
            if dev:
                self._hdr_status.configure(text=f"MIDI: {dev}", fg=th.c("success"))
            else:
                self._hdr_status.configure(text="MIDI: none", fg=th.c("fg_dim"))

        self._root.after(50, self._animate)

    def _draw_waveform(self, canvas, did):
        """Draw neon waveform for a deck."""
        th = self._theme
        canvas.delete("wave")
        w = max(10, canvas.winfo_width())
        h = max(10, canvas.winfo_height())
        mid = h // 2

        # Simulated waveform (noise + frequency components)
        t = time.time()
        phase = hash(did) * 0.1
        amp = 0.3 + 0.2 * math.sin(t * 0.8 + phase)

        color = th.c("waveform")
        # Draw mirrored waveform
        pts = []
        n_bars = 80
        for i in range(n_bars):
            x = i / n_bars * w
            # Multiple frequencies for interesting shape
            val = (amp * 0.5 * math.sin(i * 0.3 + t * 3 + phase) +
                   amp * 0.3 * math.sin(i * 0.7 + t * 5 + phase * 2) +
                   amp * 0.2 * math.sin(i * 1.5 + t * 8 + phase * 3))
            bar_h = abs(val) * mid * 0.8
            # Neon color gradient
            intensity = min(1.0, abs(val) * 1.5)
            try:
                r, g, b = self._glow.hex_to_rgb(color)
            except Exception:
                r, g, b = 0, 240, 255  # default cyan
            bar_color = f"#{int(r*intensity):02x}{int(g*intensity):02x}{int(b*intensity):02x}"
            canvas.create_line(x, mid - bar_h, x, mid + bar_h,
                             fill=bar_color, tags="wave", width=1)

        # Glow underlay
        for i in range(0, n_bars, 3):
            x = i / n_bars * w
            val = (0.3 * math.sin(i * 0.3 + t * 3 + phase * 0.5))
            bar_h = abs(val) * mid * 0.4
            try:
                glow_r, glow_g, glow_b = self._glow.hex_to_rgb(th.c("glow_cyan"))
            except Exception:
                glow_r, glow_g, glow_b = 0, 240, 255
            glow_color = f"#{int(glow_r*0.3):02x}{int(glow_g*0.3):02x}{int(glow_b*0.3):02x}"
            canvas.create_line(x, mid - bar_h, x, mid + bar_h,
                             fill=glow_color, tags="wave", width=2)

        # Center line
        canvas.create_line(0, mid, w, mid, fill=th.c("border"), width=1, tags="wave")

    def _draw_spectrum_idle(self):
        """Draw idle spectrum bars."""
        canvas = self._spectrum_canvas
        if not canvas:
            return
        th = self._theme
        canvas.delete("sp")
        w = max(10, canvas.winfo_width())
        h = 60
        n_bars = 32
        bar_w = w / n_bars
        t = time.time()

        for i in range(n_bars):
            x = i * bar_w
            # Idle breathing animation
            level = abs(math.sin(t * 0.5 + i * 0.2)) * 0.3 + 0.1
            bar_h = int(level * h)
            if bar_h < 1:
                continue
            # Gradient: green -> cyan -> purple based on frequency
            progress = i / n_bars
            if progress < 0.33:
                color = th.c("glow_green")
            elif progress < 0.66:
                color = th.c("glow_cyan")
            else:
                color = th.c("glow_magenta")
            canvas.create_rectangle(x, h - bar_h, x + bar_w - 1, h,
                                   fill=color, outline="", tags="sp")

    def _pad_click(self, idx):
        """Handle hot cue pad click."""
        th = self._theme
        pad = self._pad_buttons[idx]
        pad.delete("all")
        pad.configure(bg=th.c("accent"))
        self._root.after(200, lambda: self._reset_pad(idx))

        # Trigger via deck_studio module
        deck = self.get_module("deck_studio")
        if deck:
            deck.trigger_hotcue("A", idx)
            self.publish("ui.pad_clicked", {"pad": idx})

    def _reset_pad(self, idx):
        th = self._theme
        cue_colors = [th.c("accent"), th.c("accent2"), th.c("accent3"),
                      th.c("accent4"), th.c("accent5"), th.c("success"),
                      th.c("warning"), th.c("danger")]
        pad = self._pad_buttons[idx]
        pad.delete("all")
        pad.create_rectangle(2, 2, 48, 34, fill=th.c("bg_dark"),
                           outline=cue_colors[idx % 8], width=2)
        pad.create_text(25, 18, text=str(idx + 1), fill=cue_colors[idx % 8],
                       font=("Consolas", 10, "bold"))

    def _cycle_theme(self):
        themes = self._theme.list_themes()
        idx = themes.index(self._theme.name)
        self._theme.name = themes[(idx + 1) % len(themes)]
        self._theme.set_theme(self._theme.name)
        if self._root:
            self._root.configure(bg=self._theme.c("bg"))

    # ================================================================
    # EVENTS
    # ================================================================
    async def on_event(self, event) -> None:
        if event.topic == "midi.event":
            # Forward MIDI events to UI update
            pass  # handled by animation loop

    def health_check(self) -> Dict[str, Any]:
        return {"window_open": self._root is not None}