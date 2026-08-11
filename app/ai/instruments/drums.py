"""
DJ AI OS — Percussion Instrument Plugins

Real drum kit built on the synth core. Each plugin wraps one synthesized
sound and exposes live-automatable parameters.
"""

import numpy as np

from .base import InstrumentPlugin, register
from . import synth_core as sc


@register
class KickPlugin(InstrumentPlugin):
    name = "kick"
    category = "percussion"
    description = "Punchy club kick with pitch sweep, click and drive."
    params = {
        "freq_start": {"min": 60, "max": 300, "default": 150},
        "freq_end":   {"min": 30, "max": 90, "default": 48},
        "body":       {"min": 0.2, "max": 1.5, "default": 1.0},
        "punch":      {"min": 1.0, "max": 5.0, "default": 1.0},
        "decay":      {"min": 2.0, "max": 20.0, "default": 12.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.kick(freq_start=p["freq_start"], freq_end=p["freq_end"],
                      body=p["body"], punch=p["punch"])
        # apply decay via envelope scaling (shorter = tighter)
        n = len(sig)
        t = np.arange(n) / self.sr
        sig = sig * np.exp(-t * max(0, 6 - p["decay"] * 0.35))
        return self._norm(sig * velocity)


@register
class Kick808Plugin(InstrumentPlugin):
    name = "kick_808"
    category = "percussion"
    description = "Deep sub-only 808 kick — long tail for trap/techno."
    params = {
        "freq":  {"min": 30, "max": 90, "default": 50},
        "decay": {"min": 2.0, "max": 14.0, "default": 6.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.kick_808(freq=p["freq"], decay=p["decay"])
        return self._norm(sig * velocity)


@register
class SnarePlugin(InstrumentPlugin):
    name = "snare"
    category = "percussion"
    description = "Layered snare: tone body + snappy noise + metallic crack."
    params = {
        "tone":   {"min": 120, "max": 260, "default": 180},
        "body":   {"min": 0.2, "max": 1.5, "default": 0.5},
        "snappy": {"min": 0.3, "max": 1.8, "default": 1.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.snare(tone=p["tone"], body=p["body"], snappy=p["snappy"])
        return self._norm(sig * velocity)


@register
class ClapPlugin(InstrumentPlugin):
    name = "clap"
    category = "percussion"
    description = "Classic 3-burst bandpassed clap."
    params = {
        "bursts": {"min": 2, "max": 5, "default": 3},
        "bright": {"min": 0.4, "max": 2.0, "default": 1.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.clap(bursts=int(p["bursts"]), bright=p["bright"])
        return self._norm(sig * velocity)


@register
class HatClosedPlugin(InstrumentPlugin):
    name = "hat"
    category = "percussion"
    description = "Closed hi-hat: tight highpassed noise."
    params = {
        "dur":    {"min": 0.03, "max": 0.15, "default": 0.08},
        "bright": {"min": 0.4, "max": 2.0, "default": 1.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.hat_closed(dur=p["dur"], bright=p["bright"])
        return self._norm(sig * velocity)


@register
class HatOpenPlugin(InstrumentPlugin):
    name = "hat_open"
    category = "percussion"
    description = "Open hi-hat: long noise wash."
    params = {
        "dur":    {"min": 0.15, "max": 0.8, "default": 0.35},
        "bright": {"min": 0.4, "max": 2.0, "default": 1.0},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.hat_open(dur=p["dur"], bright=p["bright"])
        return self._norm(sig * velocity)


@register
class ShakerPlugin(InstrumentPlugin):
    name = "shaker"
    category = "percussion"
    description = "Bright shaker / cabasa."
    params = {
        "dur": {"min": 0.05, "max": 0.4, "default": 0.18},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.shaker(dur=p["dur"])
        return self._norm(sig * velocity)


@register
class RimPlugin(InstrumentPlugin):
    name = "rim"
    category = "percussion"
    description = "Rimshot / woodblock."
    params = {
        "dur": {"min": 0.04, "max": 0.2, "default": 0.1},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.rim(dur=p["dur"])
        return self._norm(sig * velocity)


@register
class TomPlugin(InstrumentPlugin):
    name = "tom"
    category = "percussion"
    description = "Pitch-dropping tom drum."
    params = {
        "freq": {"min": 60, "max": 300, "default": 120},
        "dur":  {"min": 0.1, "max": 0.8, "default": 0.35},
    }

    def _render(self, note=None, velocity=1.0):
        p = self._params
        sig = sc.tom(freq=p["freq"], dur=p["dur"])
        return self._norm(sig * velocity)
