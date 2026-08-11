"""
DJ AI OS — Pioneer FX Engine
============================
Realtime DJ effects, pure numpy + scipy. No GPU, no model. Every effect
takes a mono float32 buffer and returns a mono float32 buffer the same
length, so a rack can chain them in any order. This is the software FX
brain behind the Pioneer Link panel — MIDI-learn a knob on a CDJ/DJM/XDJ
and it drives these live.

FX catalogue (Pioneer-inspired):
    echo        — beat-synced feedback delay
    reverb      — Schroeder-ish space (cheap, no IR)
    filter      — resonant lowpass sweeping an LFO (or a fixed cutoff)
    flanger     — modulated comb, Jet-style
    phaser      — allpass ladder sweeping an LFO
    gate        — beat gate / beat-repeat (the "stab" effect)
    bitcrush    — downsample + bit-depth destroy
    dist        — tanh waveshaper "phatt" drive
    duck        — sidechain-style volume pump on the beat

Each effect returns `wet` material; the rack mixes dry + wet, so you can
run 4 of them and still keep the original signal underneath.
"""

import numpy as np


# ---------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------

def _norm(x):
    x = np.asarray(x, dtype=np.float32)
    peak = float(np.max(np.abs(x))) + 1e-9
    return (x / peak * 0.95).astype(np.float32)


def _lfo(sr, n, rate_hz, phase=0.0):
    """0..1 sine LFO over n samples."""
    t = np.arange(n) / sr
    return (0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t + phase)).astype(np.float32)


def _lfilter(b, a, x):
    from scipy.signal import lfilter
    return lfilter(b, a, x, axis=0)


def _biquad_lp(x, sr, cutoff_hz, q=0.8):
    """Resonant 2nd-order lowpass, per-block cutoff sweep."""
    w0 = 2 * np.pi * cutoff_hz / sr
    cw = np.cos(w0)
    alpha = np.sin(w0) / (2 * q)
    b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return _lfilter(b, a, x)


def _biquad_allpass(x, sr, freq_hz, q=0.8):
    """2nd-order allpass (the phaser building block)."""
    w0 = 2 * np.pi * freq_hz / sr
    alpha = np.sin(w0) / (2 * q)
    b = [1 - alpha, -2 * np.cos(w0), 1 + alpha]
    a = [1 + alpha, -2 * np.cos(w0), 1 - alpha]
    return _lfilter(b, a, x)


def _as_mono(x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        x = x.mean(axis=1)
    return x.reshape(-1)


def _fb_comb(x, d, f):
    """Feedback comb: y[n] = x[n] + f*y[n-d], via geometric accumulation.

    O((n/d) * n) instead of lfilter's dense O(n*d) — d can be tens of
    thousands of samples (long echo/reverb tails) without slowing down."""
    n = len(x)
    out = np.zeros(n, dtype=np.float64)
    x64 = x.astype(np.float64)
    fk = 1.0
    k = 0
    while fk > 1e-4 and k * d < n:
        if k == 0:
            out += x64
        else:
            off = k * d
            if off < n:
                out[off:] += x64[: n - off] * fk
        fk *= f
        k += 1
    return out.astype(np.float32)


# ---------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------

def fx_echo(x, sr, time_s=0.25, feedback=0.45, wet=0.35):
    """Beat-synced feedback delay. time_s = one echo repeat length."""
    x = _as_mono(x)
    d = max(1, int(sr * time_s))
    y = _fb_comb(x, d, feedback)
    out = x + wet * y
    return _norm(out)


def fx_reverb(x, sr, wet=0.45, decay=0.5, size=1.0):
    """Schroeder-ish reverb: 4 feedback combs + 2 allpasses, no IR file."""
    x = _as_mono(x)
    sr_f = float(sr)
    comb_len = [int(sr_f * s) for s in (0.0297, 0.0371, 0.0411, 0.0437)]
    out = np.zeros_like(x)
    for d in comb_len:
        d = max(1, int(d * size))
        out += _fb_comb(x, d, decay)
    out = out / len(comb_len)
    # dampen with two allpasses (freqs safely below Nyquist)
    out = _biquad_allpass(out, sr, 0.16 * sr_f, 0.7)
    out = _biquad_allpass(out, sr, 0.09 * sr_f, 0.7)
    out = _lfilter([1.0], [1.0, -0.15], out)
    return _norm(x + wet * out)


def fx_filter(x, sr, cutoff_hz=8000.0, resonance=0.7, lfo_rate=0.0,
              lfo_depth=0.0, wet=1.0):
    """Resonant lowpass. If lfo_rate>0, cutoff sweeps through the LFO."""
    x = _as_mono(x)
    n = len(x)
    if lfo_rate > 0:
        l = _lfo(sr, n, lfo_rate)
        lo = max(60.0, cutoff_hz * (1.0 - lfo_depth))
        hi = min(18000.0, cutoff_hz * (1.0 + lfo_depth))
        cut = lo + l * (hi - lo)
    else:
        cut = np.full(n, float(cutoff_hz))
    # block-wise time-varying biquad (vectorized across blocks)
    block = 1024
    y = np.zeros(n, dtype=np.float32)
    for i in range(0, n, block):
        seg = x[i:i + block]
        c = float(cut[i])
        y[i:i + block] = _biquad_lp(seg, sr, c, resonance)
    return _norm(x * (1 - wet) + y * wet)


def fx_flanger(x, sr, rate_hz=0.25, depth_ms=6.0, feedback=0.25, wet=0.5):
    """Modulated short delay — the sweeping Jet/flanger."""
    x = _as_mono(x)
    n = len(x)
    max_d = int(sr * (depth_ms / 1000.0) * 1.5) + 1
    buf = np.concatenate([np.zeros(max_d, dtype=np.float32), x])
    l = _lfo(sr, n, rate_hz)
    delay_s = (1.0 - l) * (sr * depth_ms / 1000.0) + 1.0
    idx = np.arange(n, dtype=np.float64) + max_d - delay_s
    idx = np.clip(idx, 0, len(buf) - 1)
    delayed = np.interp(idx, np.arange(len(buf)), buf).astype(np.float32)
    y = x + wet * (delayed + feedback * delayed)
    return _norm(y)


def fx_phaser(x, sr, rate_hz=0.3, stages=4, depth=0.7, wet=0.5):
    """Allpass-ladder phaser sweeping an LFO."""
    x = _as_mono(x)
    n = len(x)
    base = 300.0
    span = 1400.0 * depth
    block = 1024
    y = x.copy()
    for i in range(0, n, block):
        seg = x[i:i + block]
        t0 = i / sr
        phase = 2 * np.pi * rate_hz * (t0 + np.arange(len(seg)) / sr)
        freq = base + span * (0.5 + 0.5 * np.sin(phase))
        v = seg.copy()
        for _ in range(stages):
            v = _biquad_allpass(v, sr, float(freq[0]), 0.9)
        y[i:i + block] = v
    return _norm(x * (1 - wet) + y * wet)


def fx_gate(x, sr, bpm=128, step="16", hold=0.5, repeat=False, wet=1.0):
    """Beat gate / beat-repeat. step: '4'=1/4 '8'=1/8 '16'=1/16 '32'=1/32."""
    x = _as_mono(x)
    n = len(x)
    step_div = {"4": 4, "8": 8, "16": 16, "32": 32}.get(str(step), 16)
    step_n = max(1, int(sr * 60.0 / bpm / (step_div / 4.0)))
    steps = max(1, n // step_n)
    gate_on = int(round(steps * hold))
    y = np.zeros(n, dtype=np.float32)
    for s in range(steps):
        i0 = s * step_n
        i1 = min(n, i0 + step_n)
        if s < gate_on:
            if repeat and s > 0:
                prev = y[max(0, i0 - step_n):max(0, i0)]
                y[i0:i1] = prev[: i1 - i0] if len(prev) >= i1 - i0 else \
                    np.resize(prev, i1 - i0)
            else:
                y[i0:i1] = x[i0:i1]
    return _norm(x * (1 - wet) + y * wet)


def fx_bitcrush(x, sr, bits=8, downsample=2, wet=0.8):
    """Destroy: quantize depth + sample-and-hold at a reduced rate."""
    x = _as_mono(x)
    q = 2 ** max(2, bits)
    y = np.round(x * q) / q
    hold = max(1, int(downsample))
    y = y[::hold]
    y = np.repeat(y, hold)
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    y = y[: len(x)]
    return _norm(x * (1 - wet) + y * wet)


def fx_dist(x, sr, drive=2.0, wet=0.7):
    """Tanh waveshaper 'phatt' drive."""
    x = _as_mono(x)
    y = np.tanh(drive * x) / np.tanh(drive)
    return _norm(x * (1 - wet) + y * wet)


def fx_duck(x, sr, bpm=128, amount=0.6):
    """Sidechain-style pump on every beat (loud->soft->loud)."""
    x = _as_mono(x)
    n = len(x)
    beat_n = max(1, int(sr * 60.0 / bpm))
    t = np.arange(n) % beat_n
    env = np.cos(np.pi * t / beat_n)
    env = (env + 1) * 0.5 * amount + (1 - amount)
    return _norm(x * env.astype(np.float32))


# ---------------------------------------------------------------------
# THE RACK
# ---------------------------------------------------------------------

FX_CATALOG = {
    "echo":     fx_echo,
    "reverb":   fx_reverb,
    "filter":   fx_filter,
    "flanger":  fx_flanger,
    "phaser":   fx_phaser,
    "gate":     fx_gate,
    "bitcrush": fx_bitcrush,
    "dist":     fx_dist,
    "duck":     fx_duck,
}

# default params for each effect (all share a `wet`)
FX_PARAMS = {
    "echo":     {"time_s": 0.25, "feedback": 0.45, "wet": 0.35},
    "reverb":   {"wet": 0.45, "decay": 0.5, "size": 1.0},
    "filter":   {"cutoff_hz": 8000.0, "resonance": 0.7, "lfo_rate": 0.3,
                 "lfo_depth": 0.5, "wet": 0.8},
    "flanger":  {"rate_hz": 0.25, "depth_ms": 6.0, "feedback": 0.25,
                 "wet": 0.5},
    "phaser":   {"rate_hz": 0.3, "stages": 4, "depth": 0.7, "wet": 0.5},
    "gate":     {"step": "16", "hold": 0.5, "repeat": False, "wet": 1.0},
    "bitcrush": {"bits": 8, "downsample": 2, "wet": 0.8},
    "dist":     {"drive": 2.0, "wet": 0.7},
    "duck":     {"amount": 0.6},
}


class FXRack:
    """Up to N FX slots chained over a source. `apply` returns the mix.

    Each slot: {"type": str, "params": dict, "active": bool}.
    Chain order = list order. BPM is passed along so beat effects sync."""

    def __init__(self, slots=4, bpm=128):
        self.slots = [{"type": None, "params": {}, "active": False}
                      for _ in range(slots)]
        self.bpm = bpm

    def set(self, slot, fx_type, params=None):
        if slot < 0 or slot >= len(self.slots):
            return
        self.slots[slot] = {
            "type": fx_type,
            "params": dict(FX_PARAMS.get(fx_type, {})),
            "active": bool(fx_type),
        }
        if params:
            self.slots[slot]["params"].update(params)

    def clear(self, slot):
        if 0 <= slot < len(self.slots):
            self.slots[slot] = {"type": None, "params": {}, "active": False}

    def set_param(self, slot, key, value):
        if 0 <= slot < len(self.slots):
            self.slots[slot]["params"][key] = value

    def active_slots(self):
        return [s for s in self.slots if s["active"] and s["type"]]

    def apply(self, audio, bpm=None):
        """audio: mono float32. Returns processed mono float32."""
        x = _as_mono(audio)
        if bpm is None:
            bpm = self.bpm
        for s in self.slots:
            if not (s["active"] and s["type"]):
                continue
            fn = FX_CATALOG.get(s["type"])
            if fn is None:
                continue
            import inspect
            sig = inspect.signature(fn)
            p = {k: v for k, v in s["params"].items() if k in sig.parameters}
            if "bpm" in sig.parameters:
                p["bpm"] = bpm  # only the beat-synced fx actually use it
            x = fn(x, 44100, **p)
        return x

    def state(self):
        return [{"type": s["type"], "params": dict(s["params"]),
                 "active": s["active"]} for s in self.slots]
