"""
Minimal synth engine prototype.
- Uses numpy to synthesize simple percussive sounds (kick, hat, snare-ish)
- Optionally plays via `sounddevice` if available and exports WAV

This is a starting point and should be replaced with a proper synthesis
library (pyo, fluidsynth, or a VST host) for production and live use.
"""

import math
import wave
import struct
import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None


class SynthEngine:

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate

    def _sine(self, freq, length_s, amp=1.0):
        t = np.linspace(0, length_s, int(self.sample_rate * length_s), False)
        return amp * np.sin(2 * math.pi * freq * t)

    def _decay(self, signal, decay=4.0):
        t = np.linspace(0, len(signal) / self.sample_rate, num=len(signal))
        env = np.exp(-decay * t)
        return signal * env

    def make_kick(self, freq=60, length_s=0.7):
        # pitch sweep sine + strong decay
        t = np.linspace(0, length_s, int(self.sample_rate * length_s), False)
        sweep = freq * np.exp(-6 * t) + 40
        sig = np.sin(2 * math.pi * sweep * t)
        sig = self._decay(sig, decay=6.0)
        return sig * 0.9

    def make_hat(self, length_s=0.12):
        # noise filtered short
        n = np.random.uniform(-1, 1, int(self.sample_rate * length_s))
        # simple high-pass-ish: subtract low-freq moving average
        kernel = np.ones(3) / 3.0
        low = np.convolve(n, kernel, mode="same")
        hp = n - low
        return self._decay(hp, decay=40.0) * 0.4

    def make_snare(self, length_s=0.35):
        noise = np.random.uniform(-1, 1, int(self.sample_rate * length_s))
        tone = self._sine(180, length_s, amp=0.25)
        sig = (noise * 0.7) + tone
        return self._decay(sig, decay=10.0) * 0.6

    def play(self, signal):
        if sd is None:
            raise RuntimeError("sounddevice not available")
        sd.play(signal, self.sample_rate)
        sd.wait()

    def export_wav(self, signal, path):
        # normalize
        maxv = np.max(np.abs(signal)) or 1.0
        sig16 = np.int16(signal / maxv * 32767)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(sig16.tobytes())

    def generate_beat(self, pattern, bpm=120, bars=4):
        """
        pattern: list of lists per instrument, e.g.
          {"kick": [1,0,0,0,1,0,0,0], "hat": [1,1,1,1,1,1,1,1]}
        returns a mono buffer
        """
        beat_len_s = 60.0 / bpm
        steps = len(next(iter(pattern.values())))
        total_steps = steps * bars
        step_len = beat_len_s / (steps / 4.0)  # assume 16th resolution
        out = np.zeros(int(total_steps * step_len * self.sample_rate) + 1)

        for instr, seq in pattern.items():
            for bar in range(bars):
                for i, hit in enumerate(seq):
                    if not hit:
                        continue
                    position = ((bar * steps) + i) * step_len
                    idx = int(position * self.sample_rate)
                    if instr == "kick":
                        note = self.make_kick()
                    elif instr == "hat":
                        note = self.make_hat()
                    elif instr == "snare":
                        note = self.make_snare()
                    else:
                        note = self.make_kick()
                    end = idx + len(note)
                    out[idx:end] += note[: max(0, len(out) - idx)]

        # soft clip
        out = out / (np.max(np.abs(out)) + 1e-9) * 0.95
        return out
