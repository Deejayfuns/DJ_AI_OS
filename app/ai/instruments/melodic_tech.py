"""
DJ AI OS — Melodic Techno Kit

The signature sounds of melodic techno: dark long kicks, rolling basses,
wide atmospheric pads, bright repetitive arps, metallic ticks, risers,
drones, tech percussion and stabs.

Registered as standard plugins — discoverable via list_instruments(),
mountable by Astra Nexus, usable in LivePerformancePanel.
"""

import numpy as np

from .base import InstrumentPlugin, register
from . import synth_core as sc


# ============================================================
# DRUMS
# ============================================================

@register
class KickTechPlugin(InstrumentPlugin):
    name = "kick_tech"
    category = "percussion"
    description = "Dark melodic techno kick — long sub tail, deep roll."
    params = {
        "freq":  {"min": 35, "max": 70, "default": 45},
        "decay": {"min": 0.2, "max": 1.0, "default": 0.55},
        "click": {"min": 0.0, "max": 0.3, "default": 0.05},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.kick_tech(freq=p["freq"], decay=p["decay"], click=p["click"])
        return self._norm(sig * velocity)


@register
class ClapTechPlugin(InstrumentPlugin):
    name = "clap_tech"
    category = "percussion"
    description = "Darker longer clap — melodic tech percussion."
    params = {
        "body":   {"min": 0.1, "max": 1.0, "default": 0.5},
        "snappy": {"min": 0.3, "max": 1.5, "default": 0.8},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.clap_tech(body=p["body"], snappy=p["snappy"])
        return self._norm(sig * velocity)


@register
class HatTechPlugin(InstrumentPlugin):
    name = "hat_tech"
    category = "percussion"
    description = "Sharp darker hi-hat — less hiss, more tick."
    params = {
        "dur":    {"min": 0.03, "max": 0.15, "default": 0.07},
        "bright": {"min": 0.3, "max": 1.5, "default": 0.7},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.hat_tech(dur=p["dur"], bright=p["bright"])
        return self._norm(sig * velocity)


@register
class TickPlugin(InstrumentPlugin):
    name = "tick"
    category = "percussion"
    description = "Metallic tick — the perkyon glue of melodic techno."
    params = {
        "freq":  {"min": 1200, "max": 5000, "default": 2100},
        "bright": {"min": 0.3, "max": 2.0, "default": 1.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.tick(freq=p["freq"], bright=p["bright"])
        return self._norm(sig * velocity)


@register
class DeepTomPlugin(InstrumentPlugin):
    name = "tom_deep"
    category = "percussion"
    description = "Deep round tom — low-end fill material."
    params = {
        "freq": {"min": 55, "max": 160, "default": 85},
        "dur":  {"min": 0.2, "max": 0.9, "default": 0.5},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.deep_tom(freq=p["freq"], dur=p["dur"])
        return self._norm(sig * velocity)


# ============================================================
# MELODIC / TEXTURE
# ============================================================

@register
class RollingBassPlugin(InstrumentPlugin):
    name = "bass_roll"
    category = "melodic"
    description = "Rolling bass — the melodic techno signature pulse."
    params = {
        "cutoff": {"min": 120, "max": 900, "default": 320},
        "drive":  {"min": 1.0, "max": 4.0, "default": 1.6},
        "accent": {"min": 0.0, "max": 1.0, "default": 0.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 55.0
        sig = sc.rolling_bass(freq=freq, cutoff=p["cutoff"], drive=p["drive"],
                              accent=p["accent"])
        return self._norm(sig * velocity)


@register
class ArpPluckPlugin(InstrumentPlugin):
    name = "arp_pluck"
    category = "melodic"
    description = "Bright repetitive arp pluck — melodic techno arps."
    params = {
        "bright": {"min": 0.3, "max": 2.0, "default": 1.0},
        "decay":  {"min": 1.0, "max": 8.0, "default": 3.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 660.0
        sig = sc.arp_pluck(freq=freq, bright=p["bright"], decay=p["decay"])
        return self._norm(sig * velocity)


@register
class TechPadPlugin(InstrumentPlugin):
    name = "pad_tech"
    category = "melodic"
    description = "Wide atmospheric pad — dark, airy, lots of motion."
    cacheable = False  # long evolving pad
    params = {
        "width":  {"min": 1.0, "max": 20.0, "default": 7.0},
        "cutoff": {"min": 300, "max": 4000, "default": 1100},
    }

    def _chord(self, root):
        # minor 7 — the melodic techno workhorse chord
        return [root, root + 3, root + 7, root + 10, root + 14]

    def _render(self, note=None, velocity=1.0):
        p = self._params
        root = note if note else 60
        notes = self._chord(root)
        sig = sc.tech_pad(notes, dur=4.0, width=p["width"], cutoff=p["cutoff"],
                          detune=0.8)
        return self._norm(sig * velocity)


@register
class DronePlugin(InstrumentPlugin):
    name = "drone"
    category = "melodic"
    description = "Atmospheric tonal drone — the bed under the arrangement."
    cacheable = False
    params = {
        "cutoff": {"min": 120, "max": 1200, "default": 400},
        "detune": {"min": 0.0, "max": 8.0, "default": 1.5},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 55.0
        sig = sc.drone(freq=freq, cutoff=p["cutoff"], detune=p["detune"])
        return self._norm(sig * velocity)


@register
class StabPlugin(InstrumentPlugin):
    name = "stab"
    category = "melodic"
    description = "Short filtered saw stabs — rhythmic punctuation."
    params = {
        "cutoff": {"min": 500, "max": 8000, "default": 2500},
        "drive":  {"min": 1.0, "max": 5.0, "default": 2.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 220.0
        sig = sc.stabs(freq=freq, cutoff=p["cutoff"], drive=p["drive"])
        return self._norm(sig * velocity)


# ============================================================
# FX
# ============================================================

@register
class RiserPlugin(InstrumentPlugin):
    name = "riser"
    category = "percussion"
    description = "Riser/uplift — tension builder for phrase endings."
    cacheable = False
    params = {
        "dur": {"min": 1.0, "max": 4.0, "default": 2.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.fx_riser(dur=p["dur"])
        return self._norm(sig * velocity)
