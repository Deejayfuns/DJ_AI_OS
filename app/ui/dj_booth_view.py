"""
DJ AI OS — DJ Booth View (Pro DJ Style)

The immersive DJ cockpit — the "OHA" moment.
Dual decks with waveforms, hot cues, BPM/key displays, crossfader.
"""

import customtkinter as ctk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, GREEN, BLUE_BRIGHT, AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_H2, F_H3, F_BODY, F_META, F_MONO,
)
from app.ui.dj_widgets import (
    SpinningVinyl, WaveformDisplay, VUMeter, Crossfader,
    HotCuePads, BPMCounter, KeyDisplay, EnergyCurve,
)


class DJBoothView:
    """Builder for the Pro DJ Booth view."""

    def __init__(self, win):
        self.win = win
        self._vu_phase = 0

    def build(self, parent):
        win = self.win

        # Title bar
        title_bar = ctk.CTkFrame(parent, fg_color=SURFACE, corner_radius=0, height=40)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(
            title_bar, text="DJ BOOTH", font=F_H2, text_color=RED
        ).pack(side="left", padx=16)

        ctk.CTkLabel(
            title_bar, text="PRO PERFORMANCE MODE", font=F_META, text_color=TEXT_DIM
        ).pack(side="left", padx=12)

        # Status badges
        self.deck_a_badge = ctk.CTkLabel(
            title_bar, text="DECK A: --", font=F_MONO, text_color=BLUE_BRIGHT,
            fg_color=BG, corner_radius=4, padx=8, pady=2,
        )
        self.deck_a_badge.pack(side="right", padx=8)

        self.deck_b_badge = ctk.CTkLabel(
            title_bar, text="DECK B: --", font=F_MONO, text_color=RED,
            fg_color=BG, corner_radius=4, padx=8, pady=2,
        )
        self.deck_b_badge.pack(side="right", padx=8)

        # === MAIN BOOTH AREA ===
        booth = ctk.CTkFrame(parent, fg_color=BG, corner_radius=0)
        booth.pack(fill="both", expand=True, padx=4, pady=4)

        # === TOP: Deck A | Center Info | Deck B ===
        top = ctk.CTkFrame(booth, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=4)

        # Deck A
        deck_a = ctk.CTkFrame(top, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BLUE_BRIGHT)
        deck_a.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(deck_a, text="DECK A", font=F_BODY, text_color=BLUE_BRIGHT).pack(anchor="w", padx=10, pady=(6, 0))

        self.vinyl_a = SpinningVinyl(deck_a, radius=65)
        self.vinyl_a.pack(pady=4)

        # BPM + Key row for Deck A
        info_a = ctk.CTkFrame(deck_a, fg_color="transparent")
        info_a.pack(fill="x", padx=8, pady=(0, 6))

        self.bpm_a = BPMCounter(info_a, width=120, height=60)
        self.bpm_a.pack(side="left", padx=2)

        self.key_a = KeyDisplay(info_a, width=80, height=60)
        self.key_a.pack(side="left", padx=2)

        # Center info
        center = ctk.CTkFrame(top, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        center.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(center, text="MIX INFO", font=F_BODY, text_color=TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(6, 0))

        self.bpm_match = ctk.CTkLabel(
            center, text="BPM: --", font=F_MONO, text_color=GREEN
        )
        self.bpm_match.pack(anchor="w", padx=10, pady=4)

        self.key_match = ctk.CTkLabel(
            center, text="KEY: --", font=F_MONO, text_color=BLUE_BRIGHT
        )
        self.key_match.pack(anchor="w", padx=10)

        self.mix_advice = ctk.CTkLabel(
            center, text="Mix ipucu bekleniyor...", font=F_META, text_color=TEXT_DIM,
            wraplength=200, justify="left"
        )
        self.mix_advice.pack(anchor="w", padx=10, pady=4)

        # Crossfader
        self.crossfader = Crossfader(center, width=200, height=30)
        self.crossfader.pack(pady=(4, 8))

        # Deck B
        deck_b = ctk.CTkFrame(top, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=RED)
        deck_b.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ctk.CTkLabel(deck_b, text="DECK B", font=F_BODY, text_color=RED).pack(anchor="w", padx=10, pady=(6, 0))

        self.vinyl_b = SpinningVinyl(deck_b, radius=65)
        self.vinyl_b.pack(pady=4)

        info_b = ctk.CTkFrame(deck_b, fg_color="transparent")
        info_b.pack(fill="x", padx=8, pady=(0, 6))

        self.bpm_b = BPMCounter(info_b, width=120, height=60)
        self.bpm_b.pack(side="left", padx=2)

        self.key_b = KeyDisplay(info_b, width=80, height=60)
        self.key_b.pack(side="left", padx=2)

        # === WAVEFORMS ===
        wave_frame = ctk.CTkFrame(booth, fg_color=SURFACE, corner_radius=8, border_width=1, border_color=BORDER)
        wave_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(wave_frame, text="WAVEFORMS", font=F_BODY, text_color=TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(6, 0))

        self.waveform_a = WaveformDisplay(wave_frame, height=80)
        self.waveform_a.pack(fill="x", padx=8, pady=2)

        self.waveform_b = WaveformDisplay(wave_frame, height=80)
        self.waveform_b.pack(fill="x", padx=8, pady=(0, 6))

        # === HOT CUES + VU METERS ===
        bottom = ctk.CTkFrame(booth, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=4)

        # VU A
        vu_a_frame = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=6)
        vu_a_frame.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(vu_a_frame, text="VU A", font=F_META, text_color=TEXT_DIM).pack(pady=(4, 0))
        self.vu_a = VUMeter(vu_a_frame, height=100, width=16)
        self.vu_a.pack(padx=6, pady=4)

        # Hot Cues A
        cues_a_frame = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=6)
        cues_a_frame.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(cues_a_frame, text="HOT CUES A", font=F_META, text_color=TEXT_DIM).pack(anchor="w", padx=8, pady=(4, 0))
        self.hot_cues_a = HotCuePads(cues_a_frame, deck="A")
        self.hot_cues_a.pack(fill="x", padx=4, pady=(0, 4))

        # Energy Curve
        energy_frame = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=6)
        energy_frame.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(energy_frame, text="SET ENERGY", font=F_META, text_color=TEXT_DIM).pack(anchor="w", padx=8, pady=(4, 0))
        self.energy_curve = EnergyCurve(energy_frame, height=60)
        self.energy_curve.pack(fill="x", padx=4, pady=(0, 4))

        # Hot Cues B
        cues_b_frame = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=6)
        cues_b_frame.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(cues_b_frame, text="HOT CUES B", font=F_META, text_color=TEXT_DIM).pack(anchor="w", padx=8, pady=(4, 0))
        self.hot_cues_b = HotCuePads(cues_b_frame, deck="B")
        self.hot_cues_b.pack(fill="x", padx=4, pady=(0, 4))

        # VU B
        vu_b_frame = ctk.CTkFrame(bottom, fg_color=SURFACE, corner_radius=6)
        vu_b_frame.pack(side="left", padx=(4, 0))
        ctk.CTkLabel(vu_b_frame, text="VU B", font=F_META, text_color=TEXT_DIM).pack(pady=(4, 0))
        self.vu_b = VUMeter(vu_b_frame, height=100, width=16)
        self.vu_b.pack(padx=6, pady=4)

        # Load initial data
        self._refresh_from_decks()

    def _animated_vu(self, base_level):
        """Simulate a live, beat-synced VU signal around a track's energy."""
        import math
        self._vu_phase += 1
        ph = self._vu_phase
        beat = math.sin(ph * 0.9) * 0.18          # slow beat envelope
        ripple = math.sin(ph * 2.7 + 1.3) * 0.08  # high-frequency ripple
        base = float(base_level or 0.4)
        level = max(0.05, min(1.0, base * 0.55 + 0.45 + beat + ripple))
        return level

    def _refresh_from_decks(self):
        """Load data from the main window's deck engine."""
        win = self.win
        deck_engine = getattr(win, "deck_engine", None)
        if not deck_engine:
            return

        deck_a = deck_engine.decks.get("A", {}).get("track") or {}
        deck_b = deck_engine.decks.get("B", {}).get("track") or {}

        # Update Deck A
        if deck_a:
            self.vinyl_a.set_track(deck_a)
            self.vinyl_a.start_spin()
            bpm = deck_a.get("bpm", 0)
            key = deck_a.get("camelot", deck_a.get("key", ""))
            self.bpm_a.set_bpm(bpm, confidence=0.85)
            self.key_a.set_key(key)
            self.deck_a_badge.configure(text=f"DECK A: {bpm:.0f} BPM")
            self.waveform_a.set_info(bpm=bpm, key=key)
            if deck_a.get("waveform"):
                self.waveform_a.set_waveform(deck_a["waveform"])
                self.vu_a.set_level(self._animated_vu(deck_a.get("energy", 0.5)))
        else:
            self.vu_a.set_level(0.0)

        # Update Deck B
        if deck_b:
            self.vinyl_b.set_track(deck_b)
            self.vinyl_b.start_spin()
            bpm = deck_b.get("bpm", 0)
            key = deck_b.get("camelot", deck_b.get("key", ""))
            self.bpm_b.set_bpm(bpm, confidence=0.85)
            self.key_b.set_key(key)
            self.deck_b_badge.configure(text=f"DECK B: {bpm:.0f} BPM")
            self.waveform_b.set_info(bpm=bpm, key=key)
            if deck_b.get("waveform"):
                self.waveform_b.set_waveform(deck_b["waveform"])
                self.vu_b.set_level(self._animated_vu(deck_b.get("energy", 0.5)))
        else:
            self.vu_b.set_level(0.0)

        # BPM match
        bpm_a = deck_a.get("bpm", 0)
        bpm_b = deck_b.get("bpm", 0)
        if bpm_a and bpm_b:
            diff = abs(bpm_a - bpm_b)
            if diff < 2:
                self.bpm_match.configure(text=f"BPM MATCHED ({diff:.1f})", text_color=GREEN)
            else:
                self.bpm_match.configure(text=f"BPM DIFF: {diff:.1f}", text_color=AMBER)

        # Key compatibility
        key_a = deck_a.get("camelot", "")
        key_b = deck_b.get("camelot", "")
        if key_a and key_b:
            from app.ai.library_ai import LibraryAI
            compatible = key_b in LibraryAI.key_compatibility(None, key_a)
            self.key_a.set_key(key_a, compatible=compatible)
            self.key_b.set_key(key_b, compatible=compatible)
            self.key_match.configure(
                text=f"KEY: {key_a} <-> {key_b} {'HARMONIC' if compatible else ''}",
                text_color=GREEN if compatible else AMBER,
            )

        # Energy curve
        current_set = getattr(win, "current_set", []) or getattr(win, "library", []) or []
        if current_set:
            energies = [t.get("energy", 0.5) for t in current_set]
            self.energy_curve.set_energies(energies)

        # Hot cues (simulated)
        for i in range(8):
            self.hot_cues_a.set_pad(i, active=bool(deck_a.get("hot_cues")) and i < len(deck_a.get("hot_cues", [])))
            self.hot_cues_b.set_pad(i, active=bool(deck_b.get("hot_cues")) and i < len(deck_b.get("hot_cues", [])))

    def refresh(self):
        self._refresh_from_decks()
