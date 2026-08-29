"""
DJ AI OS — Serum/Nexus-Style Patch Synth

A professional 2-oscillator synthesizer plugin. Design basses, kicks,
leads and pads from scratch by editing a "patch":

    osc1 + osc2 -> resonant filter (SVF) -> drive -> ADSR -> out

A patch is a plain JSON dict so it can be saved, loaded and shared.
The plugin exposes every patch field as a live-automatable param, so
it plays inside LivePerformanceEngine patterns and automates like any
other instrument.

DSP notes:
- Oscillators are phase-based so the kick pitch-sweep and static
  notes share one code path.
- The filter is a Chamberlin state-variable filter (LP/BP/HP with
  resonance), implemented as an exact 2nd-order IIR and run with
  scipy.signal.lfilter (pure-numpy fallback if scipy is missing).
  Derivation: L_n = L_{n-1} + f1*B_{n-1}, B_n = f1*x_n - f1*L_{n-1}
  + (1 - f1^2 - f1*q1)*B_{n-1} gives
  BP = f1(1 - z^-1)/D, LP = f1^2 z^-1 / D,
  HP = [1-q1f1, -2+2f1q1, 1-f1q1]/D,
  D = 1 - (2 - f1^2 - f1*q1)z^-1 + (1 - f1*q1)z^-2.
  res 0..1 maps to Q in [1, 20]. Cutoff clamped to 0.45*sr.
"""

import json
import os

import numpy as np

from .base import InstrumentPlugin, register
from . import synth_core as sc
from app.core.paths import get_exports_dir

# Import once at module load so the first hit() render isn't slow.
# scipy.signal.lfilter import is ~2-6s the first time; hoisting it here
# means it happens during app startup, not on first note.
try:
    from scipy.signal import lfilter as _lfilter
    _HAVE_LFILTER = True
except Exception:
    _lfilter = None
    _HAVE_LFILTER = False

WAVES = ["sine", "saw", "square", "tri"]
FILTERS = ["lp", "bp", "hp"]

DEFAULT_PATCH = {
    "name": "init",
    "category": "bass",
    "osc1": {"wave": "saw", "coarse": 0, "detune": 0.0, "level": 0.7},
    "osc2": {"wave": "square", "coarse": 12, "detune": 0.0, "level": 0.3},
    "filter": {"type": "lp", "cutoff": 900.0, "res": 0.35},
    "env": {"a": 0.004, "d": 0.30, "s": 0.20, "r": 0.12,
            "pitch_amt": 0.0, "pitch_t": 0.05},
    "drive": 1.5,
    "level": 0.9,
}

# ============================================================
# PATCH NORMALIZATION
# ============================================================

def normalize_patch(patch):
    """Deep-merge patch over DEFAULT_PATCH, coerce types, validate names."""
    p = json.loads(json.dumps(DEFAULT_PATCH))  # deep copy
    if not isinstance(patch, dict):
        return p
    for sec in ("osc1", "osc2", "filter", "env"):
        if isinstance(patch.get(sec), dict):
            p[sec].update({k: v for k, v in patch[sec].items() if k in p[sec]})
    for key in ("name", "category", "drive", "level"):
        if key in patch:
            p[key] = patch[key]
    for o in ("osc1", "osc2"):
        if p[o]["wave"] not in WAVES:
            p[o]["wave"] = "saw"
    if p["filter"]["type"] not in FILTERS:
        p["filter"]["type"] = "lp"
    p["category"] = str(p.get("category") or "bass")
    p["name"] = str(p.get("name") or "untitled")
    return p


# ============================================================
# DSP
# ============================================================

def _osc_phase(kind, phase):
    """Render an oscillator from a phase array (radians)."""
    if kind == "sine":
        return np.sin(phase)
    p = (phase / (2 * np.pi)) % 1.0
    if kind == "saw":
        return 2.0 * p - 1.0
    if kind == "square":
        return np.where(p < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4.0 * np.abs(p - 0.5) - 1.0
    return np.sin(phase)


def svf_filter(sig, cutoff, res, mode="lp", sr=44100):
    """
    Chamberlin state-variable filter. mode in {'lp','bp','hp'}.
    res 0..1 -> Q in [1, 20]. Vectorized via scipy; scalar fallback.
    Returns float32, same length as sig.
    """
    fc = float(max(20.0, min(0.45 * sr, cutoff)))
    f1 = 2.0 * np.sin(np.pi * fc / sr)
    q1 = 1.0 / (1.0 + 19.0 * max(0.0, min(1.0, res)))

    if mode == "bp":
        b = [f1, -f1, 0.0]
    elif mode == "hp":
        b = [1.0 - q1 * f1, -2.0 + 2.0 * f1 * q1, 1.0 - q1 * f1]
    else:  # lp
        b = [0.0, f1 * f1, 0.0]
    a = [1.0, -(2.0 - f1 * f1 - f1 * q1), (1.0 - f1 * q1)]

    if _HAVE_LFILTER:
        return _lfilter(b, a, sig).astype(np.float32)
    # scalar biquad fallback: b0 x[n] + b1 x[n-1] + b2 x[n-2] - a1 y[n-1] - a2 y[n-2]
    y = np.empty_like(sig)
    x1 = x2 = y1 = y2 = 0.0
    for i, x in enumerate(sig):
        y[i] = b[0] * x + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1, y2, y1 = x1, x, y1, y[i]
    return y.astype(np.float32)


def env_adsr(n, sr=44100, a=0.004, d=0.3, s=0.2, r=0.12):
    """One-shot ADSR: linear attack, exp decay to sustain, hold, exp release."""
    n = max(1, int(n))
    na = max(1, int(a * sr))
    nd = max(1, int(d * sr))
    nr = max(1, int(r * sr))

    env = np.ones(n, dtype=np.float64)
    # attack
    aa = min(na, n)
    env[:aa] = np.linspace(0.0, 1.0, aa)
    # decay
    ndd = 0
    if aa < n:
        ndd = min(nd, n - aa)
        t = np.linspace(0.0, 1.0, ndd)
        env[aa:aa + ndd] = s + (1.0 - s) * np.exp(-t * 5.0)
    # sustain hold
    hold_end = n - nr
    seg_end = aa + ndd
    if seg_end < hold_end:
        env[seg_end:hold_end] = s
    # release
    if nr < n:
        rel_start = max(0, n - nr)
        t = np.linspace(0.0, 1.0, n - rel_start)
        env[rel_start:] *= np.exp(-t * 5.0)
    return env


def render_patch(patch, freq, dur, sr=44100, velocity=1.0):
    """
    Render a patch at a frequency for dur seconds.
    osc1 + osc2 -> SVF filter -> soft_clip(drive) -> ADSR -> level.
    Returns float32 mono.
    """
    p = normalize_patch(patch)
    n = max(1, int(dur * sr))
    t = np.arange(n) / sr

    o1, o2 = p["osc1"], p["osc2"]
    flt = p["filter"]
    env = p["env"]

    pitch_amt = float(env.get("pitch_amt") or 0.0)
    pitch_t = max(0.001, float(env.get("pitch_t") or 0.05))

    # ---- oscillators (phase-based; pitch sweep for kicks) ----
    if abs(pitch_amt) > 0.001:
        sweep = 2.0 ** (pitch_amt * np.exp(-t / pitch_t) / 12.0)
        ph1 = 2 * np.pi * np.cumsum(freq * sweep) / sr
        ph2 = 2 * np.pi * np.cumsum(freq * sweep *
                                    2.0 ** (o2["coarse"] / 12 + o2["detune"] / 1200)) / sr
        f1 = freq * 2.0 ** (o1["coarse"] / 12 + o1["detune"] / 1200)
    else:
        ph1 = 2 * np.pi * freq * 2.0 ** (o1["coarse"] / 12 + o1["detune"] / 1200) * t
        ph2 = 2 * np.pi * freq * 2.0 ** (o2["coarse"] / 12 + o2["detune"] / 1200) * t
        f1 = freq * 2.0 ** (o1["coarse"] / 12 + o1["detune"] / 1200)

    sig = o1["level"] * _osc_phase(o1["wave"], ph1)
    sig = sig + o2["level"] * _osc_phase(o2["wave"], ph2)

    # ---- filter ----
    sig = svf_filter(sig, flt["cutoff"], flt["res"], flt["type"], sr)

    # ---- drive ----
    if p["drive"] > 1.0:
        sig = sc.soft_clip(sig, p["drive"])

    # ---- ADSR ----
    adsr = env_adsr(n, sr, a=env["a"], d=env["d"], s=env["s"], r=env["r"])
    sig = sig * adsr

    out = (sig * float(p["level"]) * float(velocity)).astype(np.float32)
    return out


# ============================================================
# FACTORY PRESETS
# ============================================================

PATCH_PRESETS = {
    "acid_bass": {
        "name": "acid_bass", "category": "bass",
        "osc1": {"wave": "saw", "coarse": 0, "detune": 0, "level": 0.8},
        "osc2": {"wave": "square", "coarse": 12, "detune": 0, "level": 0.3},
        "filter": {"type": "lp", "cutoff": 620, "res": 0.6},
        "env": {"a": 0.004, "d": 0.32, "s": 0.25, "r": 0.1,
                "pitch_amt": 0, "pitch_t": 0.05},
        "drive": 2.0, "level": 0.9,
    },
    "sub_drop": {
        "name": "sub_drop", "category": "bass",
        "osc1": {"wave": "sine", "coarse": 0, "detune": 0, "level": 1.0},
        "osc2": {"wave": "sine", "coarse": -12, "detune": 0, "level": 0.0},
        "filter": {"type": "lp", "cutoff": 240, "res": 0.1},
        "env": {"a": 0.002, "d": 0.9, "s": 0.6, "r": 0.25,
                "pitch_amt": -24, "pitch_t": 0.15},
        "drive": 1.2, "level": 0.95,
    },
    "growl_bass": {
        "name": "growl_bass", "category": "bass",
        "osc1": {"wave": "saw", "coarse": 0, "detune": 10, "level": 0.8},
        "osc2": {"wave": "saw", "coarse": 0, "detune": -10, "level": 0.8},
        "filter": {"type": "bp", "cutoff": 420, "res": 0.7},
        "env": {"a": 0.003, "d": 0.35, "s": 0.3, "r": 0.1,
                "pitch_amt": 0, "pitch_t": 0.05},
        "drive": 3.2, "level": 0.85,
    },
    "tech_kick": {
        "name": "tech_kick", "category": "kick",
        "osc1": {"wave": "sine", "coarse": 0, "detune": 0, "level": 1.0},
        "osc2": {"wave": "sine", "coarse": -12, "detune": 0, "level": 0.0},
        "filter": {"type": "lp", "cutoff": 320, "res": 0.15},
        "env": {"a": 0.001, "d": 0.28, "s": 0.0, "r": 0.12,
                "pitch_amt": 24, "pitch_t": 0.045},
        "drive": 1.6, "level": 0.95,
    },
    "pluck_lead": {
        "name": "pluck_lead", "category": "lead",
        "osc1": {"wave": "saw", "coarse": 0, "detune": 0, "level": 0.7},
        "osc2": {"wave": "tri", "coarse": 12, "detune": 5, "level": 0.5},
        "filter": {"type": "lp", "cutoff": 2600, "res": 0.2},
        "env": {"a": 0.002, "d": 0.22, "s": 0.0, "r": 0.15,
                "pitch_amt": 0, "pitch_t": 0.05},
        "drive": 1.3, "level": 0.85,
    },
    "warm_pad": {
        "name": "warm_pad", "category": "pad",
        "osc1": {"wave": "saw", "coarse": 0, "detune": 8, "level": 0.5},
        "osc2": {"wave": "saw", "coarse": 0, "detune": -8, "level": 0.5},
        "filter": {"type": "lp", "cutoff": 950, "res": 0.2},
        "env": {"a": 0.55, "d": 0.5, "s": 0.7, "r": 1.4,
                "pitch_amt": 0, "pitch_t": 0.05},
        "drive": 1.1, "level": 0.7,
    },
    "bell_arp": {
        "name": "bell_arp", "category": "pluck",
        "osc1": {"wave": "sine", "coarse": 0, "detune": 0, "level": 0.8},
        "osc2": {"wave": "sine", "coarse": 12, "detune": 0, "level": 0.5},
        "filter": {"type": "bp", "cutoff": 3200, "res": 0.5},
        "env": {"a": 0.001, "d": 0.4, "s": 0.0, "r": 0.35,
                "pitch_amt": 0, "pitch_t": 0.05},
        "drive": 1.0, "level": 0.8,
    },
}


# ============================================================
# PATCH JSON STORE
# ============================================================

PATCH_DIR = os.path.join(str(get_exports_dir()), "patches")


def save_patch(patch, name=None, out_dir=PATCH_DIR):
    """Save a patch to {out_dir}/{name}.json. Returns the path."""
    p = normalize_patch(patch)
    name = (name or p.get("name") or "patch").strip()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"patch": p, "version": 1}, fh, indent=2, ensure_ascii=False)
    return path


def load_patch(name_or_path, out_dir=PATCH_DIR):
    """Load a patch by name or full path. Returns normalized dict."""
    if os.path.sep in str(name_or_path) or "/" in str(name_or_path):
        path = name_or_path
    else:
        path = os.path.join(out_dir, f"{name_or_path}.json")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return normalize_patch(data.get("patch", data))


def list_patches(out_dir=PATCH_DIR):
    """Return sorted patch names (json basenames) in out_dir."""
    if not os.path.isdir(out_dir):
        return []
    return sorted(f[:-5] for f in os.listdir(out_dir)
                  if f.lower().endswith(".json"))


# ============================================================
# PLUGIN
# ============================================================

@register
class PatchSynthPlugin(InstrumentPlugin):
    name = "synth_patch"
    category = "melodic"
    description = "Serum-style 2-osc patch synth — design basses/kicks/leads from scratch."
    cacheable = True

    params = {
        "osc1_wave":   {"min": 0, "max": 3, "default": 1},     # saw
        "osc1_coarse": {"min": -24, "max": 24, "default": 0},
        "osc1_detune": {"min": -50, "max": 50, "default": 0},
        "osc1_level":  {"min": 0, "max": 1, "default": 0.7},
        "osc2_wave":   {"min": 0, "max": 3, "default": 2},     # square
        "osc2_coarse": {"min": -24, "max": 24, "default": 12},
        "osc2_detune": {"min": -50, "max": 50, "default": 0},
        "osc2_level":  {"min": 0, "max": 1, "default": 0.3},
        "filter_type": {"min": 0, "max": 2, "default": 0},     # lp
        "filter_cutoff": {"min": 30, "max": 16000, "default": 900},
        "filter_res":  {"min": 0, "max": 1, "default": 0.35},
        "env_a":       {"min": 0.001, "max": 2.0, "default": 0.004},
        "env_d":       {"min": 0.01, "max": 3.0, "default": 0.30},
        "env_s":       {"min": 0.0, "max": 1.0, "default": 0.20},
        "env_r":       {"min": 0.01, "max": 3.0, "default": 0.12},
        "pitch_amt":   {"min": -48, "max": 48, "default": 0},
        "pitch_t":     {"min": 0.01, "max": 1.0, "default": 0.05},
        "drive":       {"min": 1.0, "max": 8.0, "default": 1.5},
        "level":       {"min": 0.0, "max": 1.0, "default": 0.9},
    }

    # ---- patch <-> params ----
    def set_patch(self, patch):
        p = normalize_patch(patch)
        self._patch_meta = {"name": p["name"], "category": p["category"]}
        for key, val in self._patch_to_params(p).items():
            self.set_param(key, val)

    def get_patch(self):
        p = self._patch_from_params()
        meta = getattr(self, "_patch_meta", {})
        p["name"] = meta.get("name", p.get("name", "untitled"))
        p["category"] = meta.get("category", p.get("category", "bass"))
        return p

    def _patch_to_params(self, patch):
        p = normalize_patch(patch)
        o1, o2 = p["osc1"], p["osc2"]
        flt = p["filter"]
        env = p["env"]
        return {
            "osc1_wave": WAVES.index(o1["wave"]),
            "osc1_coarse": o1["coarse"], "osc1_detune": o1["detune"],
            "osc1_level": o1["level"],
            "osc2_wave": WAVES.index(o2["wave"]),
            "osc2_coarse": o2["coarse"], "osc2_detune": o2["detune"],
            "osc2_level": o2["level"],
            "filter_type": FILTERS.index(flt["type"]),
            "filter_cutoff": flt["cutoff"], "filter_res": flt["res"],
            "env_a": env["a"], "env_d": env["d"], "env_s": env["s"],
            "env_r": env["r"], "pitch_amt": env["pitch_amt"],
            "pitch_t": env["pitch_t"],
            "drive": p["drive"], "level": p["level"],
        }

    def _patch_from_params(self):
        prm = self._params
        return {
            "name": "synth_patch", "category": "bass",
            "osc1": {"wave": WAVES[int(prm["osc1_wave"])],
                     "coarse": prm["osc1_coarse"], "detune": prm["osc1_detune"],
                     "level": prm["osc1_level"]},
            "osc2": {"wave": WAVES[int(prm["osc2_wave"])],
                     "coarse": prm["osc2_coarse"], "detune": prm["osc2_detune"],
                     "level": prm["osc2_level"]},
            "filter": {"type": FILTERS[int(prm["filter_type"])],
                       "cutoff": prm["filter_cutoff"], "res": prm["filter_res"]},
            "env": {"a": prm["env_a"], "d": prm["env_d"], "s": prm["env_s"],
                    "r": prm["env_r"], "pitch_amt": prm["pitch_amt"],
                    "pitch_t": prm["pitch_t"]},
            "drive": prm["drive"], "level": prm["level"],
        }

    def _patch_duration(self):
        prm = self._params
        return float(max(0.15, min(2.5, prm["env_a"] + prm["env_d"] + prm["env_r"] + 0.05)))

    # ---- render ----
    def _render(self, note=None, velocity=1.0):
        freq = sc.note_to_freq(note) if note else sc.note_to_freq(36)
        sig = render_patch(self._patch_from_params(), freq,
                           self._patch_duration(), self.sr, velocity=velocity)
        return self._norm(sig)
