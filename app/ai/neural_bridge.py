"""
DJ AI OS — Neural Bridge
========================
The Eiffel Tower of transitions: take two REAL tracks from your library,
pull a few "timbral DNA" windows out of each, then render a beat-synced
line whose sonic identity slides from Track A to Track B.

Unlike a normal EQ crossfade (which just fades two songs in/out), the
Neural Bridge *morphs the sound itself*: the first hit is pure Track A,
the last hit is pure Track B, and everything between is a timbre that
never existed — the AI's own material bridging two records.

    bridge = NeuralBridge()
    bridge.analyze("track_a.mp3", "track_b.mp3")
    audio  = bridge.render(bpm=128, bars=4, root_semis=0)
    sf.write("bridge.wav", audio, 44100)

Pure numpy + the spectral-morph primitive from neural_synth. No model
download, no GPU, runs in a second or two per bridge.
"""

import os

import numpy as np

from app.ai.instruments.neural_synth import spectral_morph

SR = 44100


def _fade(sig, ms=6):
    """Short fade in/out so hits don't click."""
    n = int(SR * ms / 1000)
    if len(sig) > 2 * n:
        f = np.linspace(0, 1, n, dtype=np.float32)
        sig[:n] *= f
        sig[-n:] *= f[::-1]
    return sig


def _load_mono(path, sr=SR):
    """Load any audio file to mono float32 at `sr`. soundfile first,
    librosa as fallback."""
    try:
        import soundfile as sf
        data, fs = sf.read(path, dtype="float32", always_2d=True)
        ch = data.mean(axis=1)
    except Exception:
        try:
            import librosa
            ch, fs = librosa.load(path, sr=sr, mono=True)
            return ch.astype(np.float32)
        except Exception as exc:
            raise RuntimeError(f"load failed: {exc}") from exc
    if fs != sr:
        n_out = int(len(ch) * sr / fs)
        idx = np.clip(np.arange(n_out) * (len(ch) / n_out), 0, len(ch) - 1)
        ch = np.interp(idx, np.arange(len(ch)), ch).astype(np.float32)
    return ch


def extract_reps(path, n=4, win=0.35, min_gap=1.0, sr=SR):
    """Pull `n` representative windows out of a track.

    Windows are centred on the loudest RMS peaks, spaced >= min_gap apart,
    so each one captures a different musical moment (drop, fill, vocal,
    chord stab...). These windows ARE the track's timbral DNA."""
    audio = _load_mono(path, sr=sr)
    hop = int(sr * 0.05)
    win_n = int(sr * win)
    if len(audio) < win_n * 2:
        audio = np.tile(audio, int(np.ceil(win_n * 2 / len(audio))))[: win_n * 2]

    # RMS envelope
    frames = max(len(audio) // hop, 1)
    rms = np.zeros(frames)
    for i in range(frames):
        seg = audio[i * hop: i * hop + hop]
        if len(seg):
            rms[i] = float(np.sqrt(np.mean(seg ** 2)))
    if rms.max() <= 0:
        rms[:] = 1.0  # silent file -> fake peaks so we still return windows

    # pick peaks, greedy, spaced by min_gap
    picks = []
    order = np.argsort(rms)[::-1]
    for idx in order:
        t_s = idx * 0.05
        if all(abs(t_s - p) >= min_gap for p in picks):
            picks.append(t_s)
        if len(picks) >= n:
            break
    picks = sorted(picks)

    reps = []
    for t_s in picks:
        c = int(t_s * sr)
        c = min(max(c, win_n // 2), len(audio) - win_n // 2)
        w = audio[c - win_n // 2: c + win_n // 2].copy()
        w = _fade(w, ms=4)
        peak = float(np.max(np.abs(w))) + 1e-9
        reps.append((w / peak * 0.9).astype(np.float32))
    return reps


# ---------------------------------------------------------------------
# THE BRIDGE
# ---------------------------------------------------------------------

class NeuralBridge:
    """Morph Track A into Track B, on-beat, in a musical motif."""

    # sparse, musical 4-bar motif (16 steps/bar). 1 = hit. Feel changes
    # in bar 4 (a lift right before Track B lands).
    _PATTERN = [
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],
        [1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0],
        [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1],
    ]
    # note steps within a minor-ish scale, relative to root
    _SCALE = [0, 3, 5, 7, 10, 12, 15, 17]

    def __init__(self, sample_rate=SR):
        self.sr = sample_rate
        self.reps_a = []
        self.reps_b = []
        self.path_a = None
        self.path_b = None
        self.name_a = ""
        self.name_b = ""
        self.audio = None
        self.render_seconds = 0.0

    # ---- analysis -------------------------------------------------
    def analyze(self, path_a, path_b, n=4, win=0.35):
        """Extract timbral DNA from both tracks. Cheap (~1-2s/track)."""
        self.path_a, self.path_b = path_a, path_b
        self.name_a = os.path.basename(path_a)
        self.name_b = os.path.basename(path_b)
        self.reps_a = extract_reps(path_a, n=n, win=win, sr=self.sr)
        self.reps_b = extract_reps(path_b, n=n, win=win, sr=self.sr)
        return {"reps_a": len(self.reps_a), "reps_b": len(self.reps_b)}

    # ---- rendering -------------------------------------------------
    def render(self, bpm=128, bars=4, root_semis=0, spread=0.5,
               out_path=None):
        """Render the bridge: `bars` bars of hits at `bpm`, timbre sliding
        A -> B. Returns stereo float32 audio (and writes WAV if out_path)."""
        steps_per_bar = 16
        step_s = 60.0 / bpm / 4.0          # 16th-note duration
        n_steps = steps_per_bar * bars

        na = len(self.reps_a) or 1
        nb = len(self.reps_b) or 1
        pattern = [self._PATTERN[b % 4] for b in range(bars)]
        pattern = [p for bar in pattern for p in bar]   # flatten

        total = 0
        for s in range(n_steps):
            if pattern[s]:
                total += 1

        place = np.zeros(n_steps, dtype=np.int32)       # hit index per step
        k = 0
        for s in range(n_steps):
            if pattern[s]:
                place[s] = k
                k += 1

        # morph curve: first hit ~pure A, last hit ~pure B, swept through
        # latent/spectral space in between. ease-in-out so the identity
        # lingers, crosses, then lands. `spread` shifts the crossing later
        # (0.5 = centre, 0.9 = almost all A until the final bars).
        ease = lambda x: x * x * (3 - 2 * x)
        t_hits = [i / (total - 1) for i in range(total)] if total > 1 else [0.0]
        t_hits = [ease(max(0.0, min(1.0, t + (0.5 - spread)))) for t in t_hits]

        gap_n = int(0.015 * self.sr)
        audio = []
        for s in range(n_steps):
            if pattern[s]:
                i = int(place[s])
                ta = i % na
                tb = i % nb
                sig = spectral_morph(self.reps_a[ta], self.reps_b[tb],
                                     t_hits[i], sr=self.sr)
                sig = self._transpose(sig, root_semis)
                peak = float(np.max(np.abs(sig))) + 1e-9
                sig = (sig / peak * 0.9).astype(np.float32)
                audio.append(_fade(sig))
                audio.append(np.zeros(gap_n, dtype=np.float32))
            else:
                audio.append(np.zeros(step_n(self.sr, step_s), dtype=np.float32))
        mono = np.concatenate(audio)

        # gentle stereo: 7ms Haas delay on the right channel for width
        d = int(0.007 * self.sr)
        r = np.concatenate([np.zeros(d, dtype=np.float32), mono[:-d]])
        stereo = np.stack([mono, r], axis=1).astype(np.float32)
        self.audio = stereo
        self.render_seconds = len(mono) / self.sr

        if out_path:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            import soundfile as sf
            sf.write(out_path, stereo, self.sr)

        return stereo

    def _transpose(self, sig, semis):
        f = 2.0 ** (semis / 12.0)
        if abs(f - 1.0) < 1e-4:
            return np.asarray(sig, dtype=np.float32)
        n_out = int(len(sig) / f)
        n_out = max(16, min(n_out, int(self.sr * 3.0)))
        idx = np.clip(np.arange(n_out) * f, 0, len(sig) - 1)
        return np.interp(idx, np.arange(len(sig)), sig).astype(np.float32)


def step_n(sr, step_s):
    return max(1, int(sr * step_s))
