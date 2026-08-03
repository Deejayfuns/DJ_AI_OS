"""Futuristic full-screen DJ Booth view.

Assembles all dj_widgets into a cockpit layout:
- Dual spinning vinyls (Deck A / Deck B)
- BPM scope (oscilloscope)
- Energy orb
- Harmonic wheel
- VU meters
- Crossfader
- Set energy curve

Launch via Ctrl+B or sidebar 'DJ Booth' button.
"""

import customtkinter as ctk

from app.ui.theme import (
    ACCENT,
    BACKGROUND,
    CARD,
    F_H2,
    F_H3,
    F_BODY,
    F_BODY_BOLD,
    F_META,
    GLASS_BG,
    GLASS_BORDER,
    MUTED,
    NEON_BLUE,
    NEON_MAGENTA,
    NEON_PURPLE,
    PANEL,
    TEXT,
)
from app.ui.glass import GlassCard
from app.ui.dj_widgets import (
    SpinningVinyl,
    BPMScope,
    EnergyOrb,
    HarmonicWheel,
    VUMeter,
    Crossfader,
    SetEnergyCurve,
    BOOTH_BG as _BOOTH_BG,
    SCOPE_GREEN,
    SCOPE_BLUE,
)


class DJBoothView:
    """Builder for the DJ Booth view. Called from MainWindow."""

    def __init__(self, win):
        self.win = win

    def build(self, parent):
        win = self.win

        # Title bar
        title_bar = ctk.CTkFrame(parent, fg_color=GLASS_BG, corner_radius=8,
                                  border_width=1, border_color=GLASS_BORDER)
        title_bar.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            title_bar,
            text="NEON PERFORMANCE COCKPIT",
            font=F_H2,
            text_color=ACCENT,
        ).pack(side="left", padx=14, pady=8)

        ctk.CTkLabel(
            title_bar,
            text="Ctrl+B ile acilir/kapanir",
            font=F_META,
            text_color=MUTED,
        ).pack(side="right", padx=14)

        # Main cockpit area
        cockpit = ctk.CTkFrame(parent, fg_color=_BOOTH_BG, corner_radius=8)
        cockpit.pack(fill="both", expand=True, padx=8, pady=4)

        # === TOP ROW: Deck A | BPM Scope | Deck B ===
        top_row = ctk.CTkFrame(cockpit, fg_color="transparent")
        top_row.pack(fill="x", padx=8, pady=8)

        # Deck A
        deck_a_frame = ctk.CTkFrame(top_row, fg_color=CARD, corner_radius=8,
                                     border_width=1, border_color=NEON_PURPLE)
        deck_a_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(deck_a_frame, text="DECK A", font=F_BODY_BOLD,
                      text_color=NEON_BLUE).pack(anchor="w", padx=10, pady=(8, 0))

        self.vinyl_a = SpinningVinyl(deck_a_frame, radius=75)
        self.vinyl_a.pack(pady=4)

        self.deck_a_info = ctk.CTkLabel(deck_a_frame, text="BPM -- | KEY --",
                                         font=F_BODY, text_color=TEXT)
        self.deck_a_info.pack(pady=(0, 8))

        # BPM Scope (center)
        scope_frame = ctk.CTkFrame(top_row, fg_color=CARD, corner_radius=8,
                                    border_width=1, border_color=GLASS_BORDER)
        scope_frame.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(scope_frame, text="BPM SCOPE", font=F_BODY_BOLD,
                      text_color=SCOPE_GREEN).pack(anchor="w", padx=10, pady=(8, 0))

        self.bpm_scope = BPMScope(scope_frame, width=380, height=100)
        self.bpm_scope.pack(padx=8, pady=4)

        # Energy Orb
        self.energy_orb = EnergyOrb(scope_frame, radius=30)
        self.energy_orb.pack(pady=4)

        # Deck B
        deck_b_frame = ctk.CTkFrame(top_row, fg_color=CARD, corner_radius=8,
                                     border_width=1, border_color=NEON_PURPLE)
        deck_b_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))

        ctk.CTkLabel(deck_b_frame, text="DECK B", font=F_BODY_BOLD,
                      text_color=SCOPE_BLUE).pack(anchor="w", padx=10, pady=(8, 0))

        self.vinyl_b = SpinningVinyl(deck_b_frame, radius=75)
        self.vinyl_b.pack(pady=4)

        self.deck_b_info = ctk.CTkLabel(deck_b_frame, text="BPM -- | KEY --",
                                         font=F_BODY, text_color=TEXT)
        self.deck_b_info.pack(pady=(0, 8))

        # === MIDDLE ROW: VU A | Harmonic Wheel | VU B ===
        mid_row = ctk.CTkFrame(cockpit, fg_color="transparent")
        mid_row.pack(fill="x", padx=8, pady=4)

        # VU Meter A
        vu_a_frame = ctk.CTkFrame(mid_row, fg_color=CARD, corner_radius=8)
        vu_a_frame.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(vu_a_frame, text="VU A", font=F_META,
                      text_color=MUTED).pack(pady=(6, 0))
        self.vu_a = VUMeter(vu_a_frame, height=130, width=20)
        self.vu_a.pack(padx=8, pady=4)

        # Harmonic Wheel
        wheel_frame = ctk.CTkFrame(mid_row, fg_color=CARD, corner_radius=8,
                                    border_width=1, border_color=NEON_PURPLE)
        wheel_frame.pack(side="left", fill="both", expand=True, padx=4)

        ctk.CTkLabel(wheel_frame, text="HARMONIC WHEEL", font=F_BODY_BOLD,
                      text_color=NEON_PURPLE).pack(anchor="w", padx=10, pady=(8, 0))

        self.harmonic_wheel = HarmonicWheel(wheel_frame, radius=95)
        self.harmonic_wheel.pack(pady=4)

        # VU Meter B
        vu_b_frame = ctk.CTkFrame(mid_row, fg_color=CARD, corner_radius=8)
        vu_b_frame.pack(side="left", padx=(4, 0))
        ctk.CTkLabel(vu_b_frame, text="VU B", font=F_META,
                      text_color=MUTED).pack(pady=(6, 0))
        self.vu_b = VUMeter(vu_b_frame, height=130, width=20)
        self.vu_b.pack(padx=8, pady=4)

        # === CROSSFADER ===
        fader_frame = ctk.CTkFrame(cockpit, fg_color=CARD, corner_radius=8)
        fader_frame.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(fader_frame, text="CROSSFADER", font=F_META,
                      text_color=MUTED).pack(pady=(6, 0))

        self.crossfader = Crossfader(fader_frame, width=500, height=30)
        self.crossfader.pack(pady=(0, 8))

        # === BOTTOM: Energy Curve + Status ===
        bottom_row = ctk.CTkFrame(cockpit, fg_color="transparent")
        bottom_row.pack(fill="x", padx=8, pady=(4, 8))

        # Energy Curve
        curve_frame = ctk.CTkFrame(bottom_row, fg_color=CARD, corner_radius=8)
        curve_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.energy_curve = SetEnergyCurve(curve_frame, width=500, height=55)
        self.energy_curve.pack(padx=8, pady=6)

        # Status panel
        status_frame = ctk.CTkFrame(bottom_row, fg_color=CARD, corner_radius=8,
                                     width=260)
        status_frame.pack(side="right", fill="y", padx=(4, 0))
        status_frame.pack_propagate(False)

        ctk.CTkLabel(status_frame, text="SET STATUS", font=F_BODY_BOLD,
                      text_color=ACCENT).pack(anchor="w", padx=10, pady=(10, 4))

        self.status_tracks = ctk.CTkLabel(status_frame, text="TRACKS: 0/0",
                                           font=F_BODY, text_color=TEXT)
        self.status_tracks.pack(anchor="w", padx=10)

        self.status_now = ctk.CTkLabel(status_frame, text="NOW: ---",
                                        font=F_BODY, text_color=NEON_BLUE,
                                        wraplength=220, justify="left")
        self.status_now.pack(anchor="w", padx=10, pady=4)

        self.status_heart = ctk.CTkLabel(status_frame, text="HEART: --",
                                          font=F_BODY, text_color=NEON_MAGENTA)
        self.status_heart.pack(anchor="w", padx=10)

        self.status_mix = ctk.CTkLabel(status_frame, text="MIX: ---",
                                        font=F_META, text_color=MUTED,
                                        wraplength=220, justify="left")
        self.status_mix.pack(anchor="w", padx=10, pady=4)

        # Load initial data from decks
        self._refresh_from_decks()

    def _refresh_from_decks(self):
        """Load data from the main window's deck engine."""
        win = self.win
        deck_engine = getattr(win, "deck_engine", None)
        if not deck_engine:
            return

        deck_a = deck_engine.decks.get("A", {}).get("track") or {}
        deck_b = deck_engine.decks.get("B", {}).get("track") or {}

        # Update vinyls
        if deck_a:
            self.vinyl_a.set_track(deck_a)
            self.deck_a_info.configure(
                text=f"BPM {deck_a.get('bpm', '--')} | KEY {deck_a.get('camelot', deck_a.get('key', '--'))}"
            )
        if deck_b:
            self.vinyl_b.set_track(deck_b)
            self.deck_b_info.configure(
                text=f"BPM {deck_b.get('bpm', '--')} | KEY {deck_b.get('camelot', deck_b.get('key', '--'))}"
            )

        # BPM Scope
        bpm_a = deck_a.get("bpm", 120)
        energy_a = deck_a.get("energy", 0.5)
        self.bpm_scope.update_data(bpm=bpm_a, energy=energy_a)

        # Energy Orb
        avg_energy = (deck_a.get("energy", 0.5) + deck_b.get("energy", 0.5)) / 2
        self.energy_orb.set_energy(avg_energy)

        # Harmonic Wheel
        self.harmonic_wheel.set_keys(
            deck_a=deck_a.get("camelot", deck_a.get("key", "")),
            deck_b=deck_b.get("camelot", deck_b.get("key", "")),
        )

        # VU meters (simulated levels)
        self.vu_a.set_level(energy_a)
        self.vu_b.set_level(deck_b.get("energy", 0.3))

        # Energy curve — use current set if available
        current_set = getattr(win, "current_set", []) or getattr(win, "library", []) or []
        if current_set:
            energies = [t.get("energy", 0.5) for t in current_set]
            now_index = getattr(win, "playback", None)
            # Try to get current track index from playback
            current_idx = 0
            if hasattr(now_index, '_index'):
                current_idx = now_index._index
            self.energy_curve.set_energies(energies, current_idx)

        # BPM Match Report
        bpm_report = deck_engine.bpm_match_report()
        if bpm_report.get("matched"):
            match_text = f"BPM MATCHED | diff={bpm_report.get('diff', 0)} | {bpm_report.get('key_a', '')} <-> {bpm_report.get('key_b', '')}"
            if bpm_report.get("harmonic_match"):
                match_text += " | HARMONIC OK"
        elif bpm_report.get("reason") != "DECK_EMPTY":
            match_text = f"BPM DIFF: {bpm_report.get('diff', 0)} | {bpm_report.get('recommendation', '')}"
        else:
            match_text = "BPM: deck bos"

        self.status_mix.configure(text=match_text)

        # Status
        total = len(current_set)
        self.status_tracks.configure(text=f"TRACKS: {total}")

        # Now playing
        now = getattr(win, "is_playing", False)
        if now:
            current_set = getattr(win, "current_set", [])
            if current_set:
                name = current_set[0].get("name", "---")
                self.status_now.configure(text=f"NOW: {name}")

    def refresh(self):
        """Public refresh method."""
        self._refresh_from_decks()
