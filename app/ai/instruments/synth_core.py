"""
DJ AI OS — Instrument Synth Core

Pure numpy/scipy sound synthesis — the sound SOURCE for the instrument
plugin system. No external audio libs required.

Each function returns a mono float32 np.ndarray at the given sample rate.
All sounds are tuned to sit well in a DJ mix (tight transients, clean lows).
"""

import numpy as np
from numpy.fft import rfft, irfft

SR_DEFAULT = 44100


def note_to_freq(midi_note: float) -> float:
    """Convert MIDI note number to frequency (A4 = 69 = 440 Hz)."""
    return 440.0 * 2.0 ** ((midi_note - 69.0) / 12.0)


def env_exp(n, sr, decay=5.0, curve=1.0):
    """Exponential decay envelope."""
    t = np.arange(n) / sr
    return np.exp(-decay * t ** curve)


def env_ad(n, sr, a=0.002, d=0.3):
    """Attack-decay envelope."""
    t = np.arange(n) / sr
    env = np.exp(-d * t)
    if a > 0:
        atk = np.minimum(t / a, 1.0)
        env = env * atk
    return env


def soft_clip(x, drive=1.0):
    """Soft saturation (tanh) — glue/limit."""
    return np.tanh(x * drive) / np.tanh(drive) if drive > 0 else x


# ============================================================
# KICKS
# ============================================================

def kick(freq_start=150, freq_end=48, dur=0.5, click=True, body=1.0, punch=1.0, sr=SR_DEFAULT):
    """
    Punchy club kick. Pitch sweeps down (freq_start -> freq_end).
    click: adds a short transient 'knock' on top.
    body: sub level. punch: distortion amount for the punchy mid.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    # Exponential pitch sweep
    freq = freq_end + (freq_start - freq_end) * np.exp(-t * 30)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    sig = np.sin(phase)

    env = np.exp(-t * 12)
    body_sig = np.sin(2 * np.pi * freq_end * t) * env

    # Mix body + pitch-sweep + distortion
    sig = body * body_sig + 0.55 * sig * env
    if punch > 1.0:
        sig = soft_clip(sig, punch)

    if click:
        click_n = int(0.008 * sr)
        tick = np.linspace(1.0, 0.0, click_n) ** 2
        sig[:click_n] += 0.35 * tick

    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.95


def kick_808(freq=50, decay=0.6, dur=1.0, sr=SR_DEFAULT):
    """Deep sub-only 808 kick with long tail."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.9


# ============================================================
# PERCUSSION
# ============================================================

def _noise(n, sr=SR_DEFAULT, seed=None):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, n)


def snare(dur=0.35, tone=180, body=0.5, snappy=1.0, sr=SR_DEFAULT):
    """Layered snare: tone body + bandpassed noise + metallic partials."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    env = np.exp(-t * 18)

    # Body tone with slight pitch drop
    freq = tone * np.exp(-t * 40) + tone * 0.4
    tone_sig = np.sin(2 * np.pi * np.cumsum(freq) / sr) * env * body

    # Bandpass-ish noise (simple: highpass via diff, then smooth)
    hp = np.diff(noise, prepend=0)
    # Smooth a bit (moving average)
    k = 24
    kern = np.ones(k) / k
    bp = np.convolve(hp, kern, mode="same")
    noise_sig = bp * env * snappy

    # Metallic crack (3 short square bursts)
    metal = np.zeros(n)
    for start in (0.0, 0.002, 0.004):
        idx = int(start * sr)
        if idx < n:
            ln = int(0.004 * sr)
            seg = np.sign(np.sin(2 * np.pi * 2400 * np.arange(ln) / sr))
            metal[idx:idx + ln] += seg * np.exp(-np.arange(ln) / sr * 400) * 0.15

    sig = tone_sig + noise_sig + metal
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.95


def clap(dur=0.4, bursts=3, bright=1.0, sr=SR_DEFAULT):
    """Classic clap: 3 noise bursts through a bandpass + long tail."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    bw = 0.01  # band width
    for i in range(bursts):
        start = int((0.02 + i * 0.012) * sr)
        ln = n - start
        if ln <= 0:
            continue
        burst = _noise(ln, sr)
        # simple bandpass: difference of two smoothed noises
        k1, k2 = 12, 48
        s1 = np.convolve(burst, np.ones(k1) / k1, mode="same")
        s2 = np.convolve(burst, np.ones(k2) / k2, mode="same")
        band = s1 - s2
        sig[start:] += band * np.exp(-t[:ln] * 22) * bright
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.9


def hat_closed(dur=0.08, bright=1.0, sr=SR_DEFAULT):
    """Closed hi-hat: highpass noise, very short decay."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    hp = np.diff(noise, prepend=0) * 0.5
    sig = hp * np.exp(-t * 90)
    # brightness tilt: emphasize highs via sharper diff
    sig = np.convolve(sig, np.array([1.0, -0.5]), mode="same") * bright
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.7


def hat_open(dur=0.35, bright=1.0, sr=SR_DEFAULT):
    """Open hi-hat: longer decay, noise wash."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    hp = np.diff(noise, prepend=0) * 0.5
    sig = hp * np.exp(-t * 18)
    sig = np.convolve(sig, np.array([1.0, -0.4]), mode="same") * bright
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


def shaker(dur=0.18, sr=SR_DEFAULT):
    """Shaker / cabasa: bright bursts."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    # bandpass around 4-6k
    hp = np.diff(noise, prepend=0)
    hp = np.convolve(hp, np.ones(8) / 8, mode="same")
    env = np.exp(-t * 40) * np.minimum(t / 0.01, 1.0)
    return (hp * env / (np.max(np.abs(hp * env)) + 1e-9)) * 0.6


def rim(dur=0.1, sr=SR_DEFAULT):
    """Rimshot / woodblock: short resonant tone."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = 850
    sig = np.sin(2 * np.pi * f * t) * np.exp(-t * 60)
    sig += np.sin(2 * np.pi * f * 2.7 * t) * np.exp(-t * 120) * 0.4
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


def tom(freq=120, dur=0.35, sr=SR_DEFAULT):
    """Tom: pitch-dropping drum body."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    freq_s = freq * np.exp(-t * 20) + freq * 0.3
    sig = np.sin(2 * np.pi * np.cumsum(freq_s) / sr) * np.exp(-t * 14)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.85


# ============================================================
# MELODIC
# ============================================================

def _oscillator(kind, freq, n, sr, phase0=0.0):
    t = np.arange(n) / sr
    if kind == "sine":
        return np.sin(2 * np.pi * freq * t + phase0)
    if kind == "saw":
        p = (freq * t + phase0 / (2 * np.pi)) % 1.0
        return 2.0 * p - 1.0
    if kind == "square":
        p = (freq * t + phase0 / (2 * np.pi)) % 1.0
        return np.where(p < 0.5, 1.0, -1.0)
    if kind == "tri":
        p = (freq * t + phase0 / (2 * np.pi)) % 1.0
        return 4.0 * np.abs(p - 0.5) - 1.0
    return np.sin(2 * np.pi * freq * t + phase0)


def one_pole_lp(sig, cutoff, sr=SR_DEFAULT):
    """One-pole lowpass filter (vectorized via scipy if available)."""
    if cutoff >= 20000:
        return sig.copy()
    if cutoff <= 20:
        return np.zeros_like(sig)
    rc = 1.0 / (2 * np.pi * cutoff)
    alpha = 1.0 / (rc * sr + 1.0)
    try:
        from scipy.signal import lfilter
        return lfilter([alpha], [1, -(1 - alpha)], sig).astype(sig.dtype)
    except Exception:
        y = np.empty_like(sig)
        acc = 0.0
        for i in range(len(sig)):
            acc += alpha * (sig[i] - acc)
            y[i] = acc
        return y


def bass(kind="saw", freq=55, dur=0.5, cutoff=400, drive=1.0, slide_to=None, sr=SR_DEFAULT):
    """
    Bass voice. kind: saw|square|tri|sine. Optional slide_to for pitch bend
    (synth-funk style). Runs through a lowpass + optional saturation.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr

    if slide_to is not None:
        f = freq + (slide_to - freq) * np.minimum(t / dur, 1.0)
        # naive FM-less approach: integrate phase
        phase = 2 * np.pi * np.cumsum(f) / sr
        raw = np.sin(phase) if kind == "sine" else None
        if raw is None:
            # reconstruct via resampling the oscillator over varying freq
            raw = _oscillator(kind, freq, n, sr)
            # crude pitch bend by time-stretching phase
            phase2 = np.cumsum(f) / freq
            idx = np.minimum(phase2, n - 1).astype(int)
            raw = raw[idx]
    else:
        raw = _oscillator(kind, freq, n, sr)

    # Lowpass to shape
    sig = one_pole_lp(raw, cutoff, sr)
    env = env_ad(n, sr, a=0.004, d=3.0)
    sig = sig * env
    if drive != 1.0:
        sig = soft_clip(sig, drive)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


def pluck(freq=440, dur=0.8, damp=0.985, sr=SR_DEFAULT):
    """
    Karplus-Strong pluck — plucky string sound, great for leads/arps.
    """
    n = int(sr * dur)
    # delay line length = one period
    d = int(sr / freq)
    if d < 2:
        d = 2
    burst = _noise(d, sr) * 0.5
    sig = np.zeros(n)
    # Fill with feedback loop
    for i in range(n):
        sig[i] = burst[i % d]
        burst[i % d] = damp * (burst[i % d] + burst[(i - 1) % d]) * 0.5
    env = np.exp(-np.arange(n) / sr * 2.2)
    return (sig * env / (np.max(np.abs(sig)) + 1e-9)) * 0.85


def pad(notes, dur=2.0, detune=0.4, cutoff=1200, sr=SR_DEFAULT):
    """Warm detuned pad — chord stack of saws/triangles through a slow LP."""
    n = int(sr * dur)
    sig = np.zeros(n)
    for midi in notes:
        f = note_to_freq(midi)
        for det in (-detune, 0.0, detune):
            fd = f * 2 ** (det / 100.0)
            sig += _oscillator("saw", fd, n, sr) * 0.5
    # Slow attack + release
    t = np.arange(n) / sr
    atk = np.minimum(t / 0.6, 1.0)
    rel = np.exp(-np.maximum(t - dur + 0.5, 0) * 3)
    env = atk * rel
    sig = sig * env
    sig = one_pole_lp(sig, cutoff, sr)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.7


def lead(freq=440, dur=1.0, kind="square", vibrato=5.0, cutoff=4000, sr=SR_DEFAULT):
    """Monophonic lead: osc + vibrato + LP + envelope."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = freq * (1 + vibrato / 100.0 * np.sin(2 * np.pi * 5.5 * t))
    raw = _oscillator(kind, f, n, sr)
    sig = one_pole_lp(raw, cutoff, sr)
    env = env_ad(n, sr, a=0.01, d=2.0)
    sig = sig * env
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


# ============================================================
# FX
# ============================================================

def fx_distort(sig, drive=2.0, tone=6000):
    """Distortion + tone lowpass."""
    out = soft_clip(sig, drive)
    return one_pole_lp(out, tone)


def fx_delay(sig, sr=SR_DEFAULT, time_s=0.375, feedback=0.35, mix=0.25):
    """Simple feedback delay."""
    delay = int(time_s * sr)
    if delay <= 0:
        return sig
    out = np.copy(sig)
    tail = np.copy(sig)
    for _ in range(3):
        tail = np.concatenate([np.zeros(delay), tail])[:len(sig)]
        tail = tail * feedback
        out += tail * mix
    return out


def fx_reverb(sig, sr=SR_DEFAULT, room=0.4, mix=0.3):
    """
    Cheap Schroeder reverb (2 comb + 2 allpass). Good enough for glue.
    """
    comb_times = [0.0297, 0.0371]
    allpass_times = [0.0050, 0.0117]

    def comb(x, delay_n, fb):
        y = np.zeros_like(x)
        buf = np.zeros(delay_n)
        for i in range(len(x)):
            b = buf[i % delay_n]
            y[i] = x[i] + b * fb
            buf[i % delay_n] = x[i] + b * fb
        return y

    def allpass(x, delay_n, fb):
        y = np.zeros_like(x)
        buf = np.zeros(delay_n)
        for i in range(len(x)):
            b = buf[i % delay_n]
            y[i] = -x[i] + b
            buf[i % delay_n] = x[i] + b * fb
        return y

    wet = np.zeros_like(sig)
    for ct in comb_times:
        wet += comb(sig, int(ct * sr), room)
    wet /= len(comb_times)
    for at in allpass_times:
        wet = allpass(wet, int(at * sr), 0.5)
    return sig * (1 - mix) + wet * mix


def fx_sidechain(sig, bpm, sr=SR_DEFAULT, amount=0.6):
    """Simple sidechain pump synced to beat (4-to-the-floor ducking)."""
    beat = 60.0 / bpm
    n = len(sig)
    t = np.arange(n) / sr
    phase = (t % beat) / beat
    # pump down at start of each beat, recover after ~50%
    env = np.where(phase < 0.5, 1 - amount * (1 - phase * 2), 1.0)
    return sig * env


# ============================================================
# MELODIC TECHNO KIT
# ============================================================
# Signature sounds of melodic techno: dark long kicks, rolling basses,
# wide atmospheric pads, bright repetitive arps, metallic ticks,
# risers and drones. Tuned to sit in the 118-132 BPM club pocket.

def kick_tech(freq=45, decay=0.55, dur=1.0, click=0.05, sr=SR_DEFAULT):
    """
    Melodic techno kick: dark, long sub tail, minimal click, big body.
    These kick deep but don't 'thump' — they roll.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    # slow-ish pitch drop, deep target
    f = freq + 150 * np.exp(-t * 40)
    phase = 2 * np.pi * np.cumsum(f) / sr
    sig = np.sin(phase)

    # body: sine at target + slight second harmonic
    body = np.sin(2 * np.pi * freq * t) * np.exp(-t * decay * 2)
    env = np.exp(-t * decay)
    sig = 0.75 * sig * env + 0.5 * body

    # soft click
    if click > 0:
        cn = int(0.006 * sr)
        sig[:cn] += click * np.linspace(1, 0, cn) ** 2

    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.95


def rolling_bass(freq=55, cutoff=320, dur=0.25, drive=1.6, accent=0.0, sr=SR_DEFAULT):
    """
    Rolling bass — the melodic techno signature. A short, filtered,
    slightly saturated single-note pulse that runs on 16ths. The filter
    'growl' comes from the drive + low cutoff.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    raw = _oscillator("saw", freq, n, sr)
    # shape with quick attack + longer-ish body
    atk = np.minimum(t / 0.002, 1.0)
    rel = np.exp(-t * (2.0 + accent * 8))
    env = atk * rel
    raw = raw * env
    # lowpass creates the roll (dark, resonant)
    sig = one_pole_lp(raw, cutoff, sr)
    # saturation adds the growl
    sig = soft_clip(sig, drive)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.85


def arp_pluck(freq=660, dur=0.25, bright=1.0, decay=3.0, sr=SR_DEFAULT):
    """
    Bright repetitive arp pluck — the other melodic techno signature.
    Fast attack, short decay, clean tone with a little noise for 'pluck'.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    # pluck body: sine + octave for brightness
    sig = np.sin(2 * np.pi * freq * t) * 0.7
    sig += np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 20) * 0.3 * bright
    # noise transient
    noise = _noise(int(0.004 * sr), sr) * 0.5
    sig[:len(noise)] += noise
    env = np.exp(-t * decay)
    sig = sig * env
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


def tech_pad(notes, dur=4.0, width=7.0, cutoff=1100, detune=0.8, sr=SR_DEFAULT):
    """
    Wide atmospheric melodic techno pad. Heavy detune (width in cents),
    slow attack, long tail, airy. Different from the house `pad` — darker,
    more motion.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for midi in notes:
        f = note_to_freq(midi)
        # detune spread across many voices for width
        for det in np.linspace(-width, width, 6):
            fd = f * 2 ** (det / 1200.0)
            sig += _oscillator("saw", fd, n, sr) * 0.22
            sig += _oscillator("sine", f, n, sr) * 0.1  # keep the core clean
    # slow attack, long release
    atk = np.minimum(t / 0.9, 1.0)
    rel = np.exp(-np.maximum(t - dur + 1.2, 0) * 2.5)
    env = atk * rel
    sig = sig * env
    sig = one_pole_lp(sig, cutoff, sr)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.7


def tick(freq=2100, dur=0.035, bright=1.0, sr=SR_DEFAULT):
    """Metallic tick — the perkyon/percussive glue of melodic techno."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.sin(2 * np.pi * freq * t)
    sig += np.sin(2 * np.pi * freq * 2.98 * t) * 0.3 * bright
    env = np.exp(-t * 90)
    sig = sig * env
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.6


def fx_riser(dur=2.0, f_start=200, f_end=8000, sr=SR_DEFAULT):
    """
    Riser / uplift: noise with rising resonant filter + volume swell.
    Dropped at the end of phrases to build tension.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    # rising one-pole cutoff (approx via chunked filtering)
    sig = np.zeros(n)
    steps = 48
    seg = n // steps
    for i in range(steps):
        f = f_start + (f_end - f_start) * (i / steps) ** 2
        chunk = one_pole_lp(noise[i * seg:(i + 1) * seg], f, sr)
        sig[i * seg:(i + 1) * seg] = chunk
    swell = (t / dur) ** 2.5
    sig = sig * swell
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.7


def drone(freq=55, dur=4.0, cutoff=400, detune=1.5, sr=SR_DEFAULT):
    """Atmospheric drone — tonal bed under the arrangement."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for det in (-detune, 0, detune):
        fd = freq * 2 ** (det / 1200.0)
        sig += _oscillator("saw", fd, n, sr) * 0.3
        sig += np.sin(2 * np.pi * freq * t) * 0.3
    sig = one_pole_lp(sig, cutoff, sr)
    atk = np.minimum(t / 1.2, 1.0)
    sig = sig * atk
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.55


def clap_tech(dur=0.5, body=0.5, snappy=0.8, sr=SR_DEFAULT):
    """
    Darker, longer clap — less bright, more tail. Melodic tech percussion.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for i in range(4):
        start = int((0.01 + i * 0.015) * sr)
        ln = n - start
        if ln <= 0:
            continue
        burst = _noise(ln, sr)
        # bandpass via diff of two smears
        s1 = np.convolve(burst, np.ones(16) / 16, mode="same")
        s2 = np.convolve(burst, np.ones(64) / 64, mode="same")
        band = s1 - s2
        sig[start:] += band * np.exp(-t[:ln] * 16) * snappy
    # tonal body
    tone = np.sin(2 * np.pi * 320 * t) * np.exp(-t * 22) * body
    sig += tone
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.85


def hat_tech(dur=0.07, bright=0.7, sr=SR_DEFAULT):
    """Sharp, darker hi-hat — less hiss, more tick."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = _noise(n, sr)
    hp = np.diff(noise, prepend=0) * 0.6
    sig = hp * np.exp(-t * 110)
    sig = np.convolve(sig, np.array([1.0, -0.6]), mode="same") * bright
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.65


def deep_tom(freq=85, dur=0.5, sr=SR_DEFAULT):
    """Deep round tom — low-end fill material."""
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = freq * np.exp(-t * 18) + freq * 0.4
    sig = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 9)
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8


def stabs(freq=220, dur=0.3, cutoff=2500, drive=2.0, sr=SR_DEFAULT):
    """
    Tech stabs — short filtered saw chords used as rhythmic punctuation.
    freq = root frequency; stack of 3rds/5ths built by the plugin.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    raw = _oscillator("saw", freq, n, sr)
    raw += _oscillator("saw", freq * 1.5, n, sr) * 0.6
    raw += _oscillator("saw", freq * 2.0, n, sr) * 0.3
    sig = one_pole_lp(raw, cutoff, sr)
    sig = soft_clip(sig, drive)
    env = np.exp(-t * 12) * np.minimum(t / 0.002, 1.0)
    sig = sig * env
    return (sig / (np.max(np.abs(sig)) + 1e-9)) * 0.8
