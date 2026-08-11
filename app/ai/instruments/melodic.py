"""
DJ AI OS — Melodic Instrument Plugins

Bass, pluck, pad and lead voices. Each is a registered plugin with live
automatable parameters. Melodic plugins use MIDI note numbers.
"""

import numpy as np

from .base import InstrumentPlugin, register
from . import synth_core as sc


@register
class SawBassPlugin(InstrumentPlugin):
    name = "bass_saw"
    category = "melodic"
    description = "Saw bass through a lowpass — house/techno staple."
    params = {
        "cutoff": {"min": 120, "max": 4000, "default": 500},
        "drive":  {"min": 1.0, "max": 6.0, "default": 1.4},
        "decay":  {"min": 1.0, "max": 8.0, "default": 3.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 55.0
        sig = sc.bass(kind="saw", freq=freq, dur=0.5,
                      cutoff=p["cutoff"], drive=p["drive"])
        n = len(sig)
        t = np.arange(n) / self.sr
        sig = sig * np.exp(-t * p["decay"] * 0.6)
        return self._norm(sig * velocity)


@register
class SubBassPlugin(InstrumentPlugin):
    name = "bass_sub"
    category = "melodic"
    description = "Clean sine sub bass — deep, no mud."
    params = {
        "decay": {"min": 1.0, "max": 10.0, "default": 3.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 55.0
        n = int(self.sr * 0.6)
        t = np.arange(n) / self.sr
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * p["decay"] * 0.7)
        return self._norm(sig * velocity)


@register
class PluckPlugin(InstrumentPlugin):
    name = "pluck"
    category = "melodic"
    description = "Karplus-Strong pluck — arp/lead material."
    params = {
        "damp": {"min": 0.94, "max": 0.999, "default": 0.985},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 440.0
        sig = sc.pluck(freq=freq, damp=p["damp"])
        return self._norm(sig * velocity)


@register
class PadPlugin(InstrumentPlugin):
    name = "pad"
    category = "melodic"
    description = "Detuned chord pad. Note = root; stack built from chord."
    cacheable = False  # long pad — always fresh render
    params = {
        "detune": {"min": 0.0, "max": 5.0, "default": 0.4},
        "cutoff": {"min": 300, "max": 5000, "default": 1400},
    }

    # chord interval stack (root, 3rd, 5th, 7th) — maj/min from note
    def _chord(self, root):
        return [root, root + 3, root + 7, root + 10]

    def _render(self, note=None, velocity=1.0):
        p = self._params
        root = note if note else 60
        notes = self._chord(root)
        sig = sc.pad(notes, dur=2.0, detune=p["detune"], cutoff=p["cutoff"])
        return self._norm(sig * velocity)


@register
class LeadPlugin(InstrumentPlugin):
    name = "lead"
    category = "melodic"
    description = "Monophonic lead with vibrato."
    params = {
        "vibrato": {"min": 0.0, "max": 20.0, "default": 5.0},
        "cutoff":  {"min": 800, "max": 10000, "default": 4500},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        freq = sc.note_to_freq(note) if note else 440.0
        sig = sc.lead(freq=freq, kind="square", vibrato=p["vibrato"],
                      cutoff=p["cutoff"])
        return self._norm(sig * velocity)
