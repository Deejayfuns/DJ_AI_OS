"""
DJ AI OS — AI Beat Studio

Generate professional beats from text/voice commands.
Channel-by-channel synthesis: kick, hat, snare, clap, percussion, bass, pad, arp.

Usage:
    studio = BeatStudio()
    result = studio.generate("128 BPM tech house beat with heavy kick")
    studio.export_mix(result, "output.wav")
    studio.export_stems(result, "stems/")
"""

import os
import re
import wave
import math
import random
import time
from typing import List, Dict, Any, Generator, Optional
import numpy as np

try:
    import sounddevice as sd
    HAS_SOUND_DEVICE = True
except Exception:
    HAS_SOUND_DEVICE = False

try:
    import rtmidi
    HAS_RTMIDI = True
except Exception:
    HAS_RTMIDI = False

try:
    import mido
    HAS_MIDO = True
except Exception:
    HAS_MIDO = False

try:
    from linkables import AbletonLink
    HAS_LINK = True
except Exception:
    HAS_LINK = False

try:
    from app.ai.synth_engine import SynthEngine
except Exception:
    SynthEngine = None


# ============================================================
# GENRE PATTERN LIBRARY
# ============================================================

GENRE_PATTERNS = {
    "house": {
        "bpm_range": (118, 130),
        "swing": 0.15,
        "patterns": {
            "kick":   [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "hat":    [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
            "hat_up": [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,1,0, 0,1,0,0, 0,0,1,0, 0,1,0,0],
            "bass":   [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,0,0,1],
        },
    },
    "tech_house": {
        "bpm_range": (124, 130),
        "swing": 0.1,
        "patterns": {
            "kick":   [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "hat":    [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
            "hat_up": [0,1,0,0, 0,1,0,0, 0,1,0,0, 0,1,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
            "perc":   [0,0,0,1, 0,0,1,0, 0,0,0,1, 0,0,1,0],
            "bass":   [1,0,0,0, 0,0,0,1, 0,0,1,0, 0,0,0,0],
        },
    },
    "afro_house": {
        "bpm_range": (118, 126),
        "swing": 0.2,
        "patterns": {
            "kick":   [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "hat":    [0,0,1,0, 0,1,0,0, 0,0,1,0, 0,1,0,0],
            "hat_up": [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,1,0],
            "clap":   [0,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
            "perc":   [0,0,1,0, 0,1,0,1, 0,0,1,0, 0,1,0,0],
            "bass":   [1,0,0,1, 0,0,0,0, 1,0,0,0, 0,0,1,0],
        },
    },
    "melodic_house": {
        "bpm_range": (120, 126),
        "swing": 0.1,
        "patterns": {
            "kick":   [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "hat":    [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
            "hat_up": [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
            "bass":   [1,0,0,0, 0,0,1,0, 0,0,0,0, 0,1,0,0],
        },
    },
    "techno": {
        "bpm_range": (128, 140),
        "swing": 0.05,
        "patterns": {
            "kick":   [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0],
            "hat":    [0,0,1,0, 0,0,1,0, 0,0,1,0, 0,0,1,0],
            "hat_up": [0,1,0,0, 0,1,0,0, 0,1,0,0, 0,1,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 0,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,0,1, 0,0,0,0, 0,0,0,1, 0,0,0,0],
            "bass":   [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,1,0],
        },
    },
    "drum_and_bass": {
        "bpm_range": (170, 176),
        "swing": 0.05,
        "patterns": {
            "kick":   [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
            "hat":    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
            "hat_up": [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,1],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,0,0, 0,0,1,0, 0,0,0,0, 0,0,1,0],
            "bass":   [1,0,0,0, 0,0,0,1, 0,1,0,0, 0,0,0,0],
        },
    },
    "trap": {
        "bpm_range": (130, 160),
        "swing": 0.25,
        "patterns": {
            "kick":   [1,0,0,0, 0,0,0,0, 1,0,0,1, 0,0,0,0],
            "hat":    [1,1,1,1, 1,1,1,1, 1,1,1,1, 1,1,1,1],
            "hat_up": [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0,0,0],
            "bass":   [1,0,0,0, 0,0,1,0, 1,0,0,0, 0,1,0,0],
        },
    },
    "hip_hop": {
        "bpm_range": (85, 100),
        "swing": 0.3,
        "patterns": {
            "kick":   [1,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0],
            "hat":    [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
            "hat_up": [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "perc":   [0,0,1,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
            "bass":   [1,0,0,0, 0,0,0,0, 1,0,0,1, 0,0,0,0],
        },
    },
    "mars": {
        "bpm_range": (124, 138),
        "swing": 0.12,
        "patterns": {
            "kick":   [1,0,0,1, 1,0,0,0, 1,0,0,1, 1,0,0,0],
            "hat":    [0,1,0,1, 0,1,0,1, 0,1,0,1, 0,1,0,1],
            "hat_up": [1,0,1,0, 1,0,1,0, 1,0,1,0, 1,0,1,0],
            "snare":  [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0],
            "clap":   [0,0,0,0, 1,0,0,0, 0,0,0,0, 0,0,0,1],
            "perc":   [0,0,0,0, 0,0,0,1, 0,0,0,0, 0,0,1,0],
            "bass":   [1,0,0,1, 0,0,1,0, 1,0,0,0, 1,0,0,1],
        },
    },
}

# Voice command parsing
BPM_PATTERN = re.compile(r"(\d{2,3})\s*(?:bpm|tempo)")
GENRE_KEYWORDS = {
    "house": "house",
    "tech house": "tech_house",
    "high tech": "tech_house",
    "deep tech": "tech_house",
    "afro": "afro_house",
    "afro house": "afro_house",
    "melodic": "melodic_house",
    "melodic house": "melodic_house",
    "deep house": "melodic_house",
    "techno": "techno",
    "dark": "techno",
    "industrial": "techno",
    "dnb": "drum_and_bass",
    "drum and bass": "drum_and_bass",
    "drum & bass": "drum_and_bass",
    "d&b": "drum_and_bass",
    "trap": "trap",
    "hip hop": "hip_hop",
    "hip-hop": "hip_hop",
    "boom bap": "hip_hop",
    "mars": "mars",
    "space": "mars",
    "interstellar": "mars",
    "galaxy": "mars",
    "orbit": "mars",
    "astronaut": "mars",
    "space tech": "mars",
    "space house": "mars",
}


class BeatStudio:
    """
    AI Beat Studio — generate professional beats from text commands.

    Usage:
        studio = BeatStudio()
        result = studio.generate("128 BPM tech house beat")
        studio.export_mix(result, "output.wav")
    """

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.synth = SynthEngine(sample_rate) if SynthEngine else None
        self.last_result = None

    def generate(self, command, bars=4, variation=0.3):
        """
        Parse a text/voice command and generate a beat.

        command: str — "128 BPM tech house beat with heavy kick"
        bars: int — number of bars (4, 8, 16)
        variation: float —0.0 to1.0 — how much variation to add

        Returns: dict with bpm, genre, stems (dict of np.array), pattern, mix
        """
        # Parse command
        genre = self._parse_genre(command)
        bpm = self._parse_bpm(command)

        # Get pattern
        pattern_data = GENRE_PATTERNS.get(genre, GENRE_PATTERNS["house"])

        if not bpm:
            low, high = pattern_data["bpm_range"]
            bpm = random.randint(low, high)

        swing = pattern_data.get("swing", 0.1)

        # Generate stems from pattern
        stems = self._pattern_to_stems(
            pattern_data["patterns"], bpm, bars, swing, variation
        )

        # Mix stems together
        mix = self._mix_stems(stems)

        # Normalize
        maxv = np.max(np.abs(mix)) or 1.0
        mix = mix / maxv * 0.95

        result = {
            "bpm": bpm,
            "genre": genre,
            "bars": bars,
            "pattern": pattern_data["patterns"],
            "stems": stems,
            "mix": mix,
            "sample_rate": self.sample_rate,
            "duration": len(mix) / self.sample_rate,
        }

        self.last_result = result
        return result

    def modify(self, result, instruction):
        """Modify an existing beat based on text instruction."""
        inst_lower = instruction.lower()

        if "kick" in inst_lower and ("sert" in inst_lower or "hard" in inst_lower or "strong" in inst_lower):
            # Make kick harder — boost level
            for key in result["stems"]:
                if "kick" in key.lower():
                    result["stems"][key] *= 1.3
                    result["stems"][key] = np.clip(result["stems"][key], -0.98, 0.98)
            result["mix"] = self._mix_stems(result["stems"])
            result["mix"] = result["mix"] / (np.max(np.abs(result["mix"])) + 1e-9) * 0.95

        elif "hat" in inst_lower or "hihat" in inst_lower:
            # Modify hi-hat pattern
            pass

        elif "bpm" in inst_lower or "tempo" in inst_lower:
            m = re.search(r"(\d{2,3})", instruction)
            if m:
                new_bpm = int(m.group(1))
                result["bpm"] = new_bpm

        elif "bar" in inst_lower or "fill" in inst_lower:
            result["bars"] += 4
            # Regenerate with more bars
            new_result = self.generate(f"{result['bpm']} BPM {result['genre']}", bars=result["bars"])
            result.update(new_result)

        self.last_result = result
        return result

    def _parse_genre(self, text):
        """Extract genre from text command."""
        text_lower = text.lower()
        for keyword, genre in sorted(GENRE_KEYWORDS.items(), key=lambda x: -len(x[0])):
            if keyword in text_lower:
                return genre
        return "house"

    def _parse_bpm(self, text):
        """Extract BPM from text command."""
        m = BPM_PATTERN.search(text.lower())
        return int(m.group(1)) if m else None

    def _pattern_to_stems(self, patterns, bpm, bars, swing, variation):
        """Convert step patterns to audio stems (numpy arrays)."""
        if not self.synth:
            return self._generate_simple_stems(patterns, bpm, bars)

        beat_len = 60.0 / bpm
        steps_per_bar = 16
        total_steps = steps_per_bar * bars
        step_len = beat_len / 4.0  # 16th note resolution
        total_samples = int(total_steps * step_len * self.sample_rate) + self.sample_rate
        sr = self.sample_rate

        stems = {}
        for instr, seq in patterns.items():
            stem = np.zeros(total_samples)

            for bar in range(bars):
                for i, hit in enumerate(seq):
                    if not hit:
                        continue

                    # Apply swing to off-beats
                    position = ((bar * steps_per_bar) + i) * step_len
                    if i % 2 == 1:
                        position += swing * step_len * 0.3

                    # Add small random timing variation
                    position += random.uniform(-variation * 0.002, variation * 0.002)

                    idx = int(position * sr)

                    if idx >= total_samples:
                        continue

                    # Generate instrument sound
                    if "kick" in instr:
                        note = self.synth.make_kick(freq=55 + random.randint(-5, 5))
                    elif "hat" in instr and "up" in instr:
                        note = self.synth.make_hat(length_s=0.08) * 0.6
                    elif "hat" in instr:
                        note = self.synth.make_hat(length_s=0.12)
                    elif "snare" in instr:
                        note = self.synth.make_snare(length_s=0.3)
                    elif "clap" in instr:
                        note = self.synth.make_snare(length_s=0.2) * 0.7
                    elif "perc" in instr:
                        note = self.synth.make_hat(length_s=0.06) * 0.5
                    elif "bass" in instr:
                        note = self.synth.make_kick(freq=80, length_s=0.2) * 0.4
                    else:
                        note = self.synth.make_hat(length_s=0.1) * 0.3

                    # Apply velocity variation
                    velocity = 0.8 + random.uniform(-variation * 0.2, variation * 0.2)
                    note = note * max(0.5, min(1.2, velocity))

                    if idx >= total_samples:
                        continue

                    available = total_samples - idx
                    if available <= 0:
                        continue

                    note = note[:min(len(note), available)]
                    target = stem[idx:idx + len(note)]

                    if len(target) == len(note):
                        stem[idx:idx + len(note)] += note
                    elif len(target) > 0:
                        stem[idx:idx + min(len(note), len(target))] += note[:min(len(note), len(target))]

            stems[instr] = stem

        return stems

    def _generate_simple_stems(self, patterns, bpm, bars):
        """Fallback stem generation without SynthEngine."""
        beat_len = 60.0 / bpm
        steps_per_bar = 16
        total_steps = steps_per_bar * bars
        step_len = beat_len / 4.0
        total_samples = int(total_steps * step_len * self.sample_rate) + self.sample_rate
        sr = self.sample_rate
        stems = {}

        for instr, seq in patterns.items():
            stem = np.zeros(total_samples)
            for bar in range(bars):
                for i, hit in enumerate(seq):
                    if not hit:
                        continue
                    position = ((bar * steps_per_bar) + i) * step_len
                    idx = int(position * sr)
                    if idx >= total_samples:
                        continue

                    # Simple sine click
                    length = min(0.15, total_samples / sr - position)
                    t = np.linspace(0, length, int(sr * length), False)
                    freq = 55 if "kick" in instr else 800
                    note = np.sin(2 * np.pi * freq * t) * np.exp(-8 * t) * 0.5
                    end = min(idx + len(note), total_samples)
                    stem[idx:end] += note[:end - idx]

            stems[instr] = stem
        return stems

    def _mix_stems(self, stems):
        """Mix all stems together with per-instrument levels."""
        if not stems:
            return np.zeros(1)

        max_len = max(len(s) for s in stems.values())
        mix = np.zeros(max_len)

        levels = {
            "kick": 1.0, "hat": 0.4, "hat_up": 0.25,
            "snare": 0.7, "clap": 0.5, "perc": 0.35,
            "bass": 0.6, "pad": 0.3, "arp": 0.25,
        }

        for name, stem in stems.items():
            level = 1.0
            for key, val in levels.items():
                if key in name.lower():
                    level = val
                    break
            mix[:len(stem)] += stem * level

        return mix

    def export_mix(self, result, path):
        """Export full mix as WAV file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        mix = result["mix"]
        maxv = np.max(np.abs(mix)) or 1.0
        sig16 = np.int16(mix / maxv * 32767)

        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(result["sample_rate"])
            wf.writeframes(sig16.tobytes())

        return path

    def export_stems(self, result, output_dir):
        """Export each stem as a separate WAV file."""
        os.makedirs(output_dir, exist_ok=True)

        paths = {}
        for name, stem in result["stems"].items():
            path = os.path.join(output_dir, f"{name}.wav")
            maxv = np.max(np.abs(stem)) or 1.0
            sig16 = np.int16(stem / maxv * 32767)

            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(result["sample_rate"])
                wf.writeframes(sig16.tobytes())

            paths[name] = path

        return paths

    def export_pro_wav(self, result, path, bit_depth=24, sample_rate=48000):
        """Export as professional WAV with configurable quality."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        mix = result["mix"]

        # Resample if needed
        if sample_rate != result["sample_rate"]:
            ratio = sample_rate / result["sample_rate"]
            new_len = int(len(mix) * ratio)
            x_old = np.linspace(0, 1, len(mix))
            x_new = np.linspace(0, 1, new_len)
            mix = np.interp(x_new, x_old, mix)

        # Normalize
        maxv = np.max(np.abs(mix)) or 1.0
        mix = mix / maxv * 0.98

        # Convert to appropriate bit depth
        if bit_depth == 16:
            data = np.int16(mix * 32767)
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(data.tobytes())

        elif bit_depth == 24:
            # 24-bit: convert to int32 then pack as 3 bytes per sample
            int32_data = np.int32(mix * 8388607)
            raw = b""
            for val in int32_data:
                raw += int(val).to_bytes(3, byteorder="little", signed=True)
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(3)
                wf.setframerate(sample_rate)
                wf.writeframes(raw)

        elif bit_depth == 32:
            data = np.float32(mix)
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(4)
                wf.setframerate(sample_rate)
                wf.writeframes(data.tobytes())

        else:
            data = np.int16(mix * 32767)
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(data.tobytes())

        return path

    def play(self, result):
        """Play the generated mix."""
        if not HAS_SOUND_DEVICE:
            raise RuntimeError("sounddevice not available")
        sd.play(result["mix"], result["sample_rate"])
        sd.wait()

    def preview(self, result, wait=False):
        """Play generated mix without blocking the caller (background thread)."""
        if not HAS_SOUND_DEVICE:
            return False
        import threading
        mix = result["mix"].astype(np.float32)
        sr = result["sample_rate"]

        def _play():
            try:
                sd.stop()
                sd.play(mix, sr)
                if wait:
                    sd.wait()
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()
        return True

    # ============================================================
    # REAL-TIME STREAMING ENGINE
    # ============================================================

    def generate_stream(self, command: str, chunk_size: int = 1024) -> Generator[np.ndarray, None, None]:
        """
        Generate infinite audio stream from command.
        Yields audio chunks for real-time playback.

        Usage:
            for chunk in studio.generate_stream("128 BPM tech house"):
                output_stream.write(chunk)
        """
        # Parse initial command
        result = self.generate(command)
        bpm = result["bpm"]
        genre = result["genre"]
        pattern = result["pattern"]  # This is already the patterns dict

        sample_rate = self.sample_rate
        samples_per_beat = int(60 * sample_rate / bpm)
        samples_per_bar = samples_per_beat * 4
        step_samples = samples_per_beat // 4  # 16th notes

        # Pre-generate one-shot samples for each instrument
        samples_cache = self._build_sample_cache({"patterns": pattern}, bpm)

        # Live parameters (stored on instance for external control)
        self._live_params = {
            "bpm": bpm,
            "swing": 0.1,
            "channel_levels": {k: 1.0 for k in samples_cache.keys()},
            "channel_filters": {k: {"cutoff": 20000, "resonance": 1.0} for k in samples_cache.keys()},
            "channel_pitch": {k: 1.0 for k in samples_cache.keys()},
            "channel_decay": {k: 1.0 for k in samples_cache.keys()},
            "mute": {k: False for k in samples_cache.keys()},
            "solo": {k: False for k in samples_cache.keys()},
            "global_filter": {"cutoff": 20000, "resonance": 1.0},
            "master_volume": 1.0,
        }

        # State
        position = 0
        bar_count = 0
        running = True

        def apply_params(audio: np.ndarray, channel: str) -> np.ndarray:
            """Apply live parameters to audio chunk."""
            # Handle global channel
            if channel == "_global":
                # Only apply master volume and global filter
                # Global filter
                cutoff = self._live_params["global_filter"]["cutoff"]
                if cutoff < 18000:
                    rc = 1.0 / (2 * math.pi * cutoff)
                    dt = 1.0 / sample_rate
                    alpha = dt / (rc + dt)
                    y = np.zeros_like(audio)
                    y[0] = audio[0]
                    for i in range(1, len(audio)):
                        y[i] = y[i-1] + alpha * (audio[i] - y[i-1])
                    audio = y
                return audio

            if self._live_params["mute"][channel] or (any(self._live_params["solo"].values()) and not self._live_params["solo"][channel]):
                return np.zeros_like(audio)

            # Level
            audio = audio * self._live_params["channel_levels"].get(channel, 1.0)

            # Pitch (simple resample)
            pitch = self._live_params["channel_pitch"].get(channel, 1.0)
            if pitch != 1.0:
                new_len = int(len(audio) / pitch)
                if new_len > 0:
                    x_old = np.linspace(0, 1, len(audio))
                    x_new = np.linspace(0, 1, new_len)
                    audio = np.interp(x_new, x_old, audio)

            # Decay (exponential envelope)
            decay = self._live_params["channel_decay"].get(channel, 1.0)
            if decay != 1.0:
                t = np.linspace(0, len(audio) / sample_rate, len(audio))
                audio = audio * np.exp(-t * decay * 10)

            # Filter (simple one-pole lowpass)
            cutoff = self._live_params["channel_filters"][channel]["cutoff"]
            if cutoff < 18000:
                # Very simple lowpass: moving average approximation
                rc = 1.0 / (2 * math.pi * cutoff)
                dt = 1.0 / sample_rate
                alpha = dt / (rc + dt)
                y = np.zeros_like(audio)
                y[0] = audio[0]
                for i in range(1, len(audio)):
                    y[i] = y[i-1] + alpha * (audio[i] - y[i-1])
                audio = y

            return audio

        while running:
            # Generate one bar
            bar_audio = np.zeros(samples_per_bar)

            for channel_name, channel_samples in samples_cache.items():
                # Place hits according to pattern
                pattern_hits = pattern.get(channel_name, [])
                if not pattern_hits:
                    continue

                steps = len(pattern_hits)
                for step_idx, hit in enumerate(pattern_hits):
                    if hit == 0:
                        continue

                    # Calculate position with swing
                    swing = self._live_params["swing"]
                    if step_idx % 2 == 1:  # Off-beat
                        step_pos = step_idx * step_samples + int(step_samples * swing)
                    else:
                        step_pos = step_idx * step_samples

                    # Copy sample
                    end_pos = min(step_pos + len(channel_samples), samples_per_bar)
                    sample_len = end_pos - step_pos
                    if sample_len > 0:
                        applied = apply_params(channel_samples[:sample_len], channel_name)
                        bar_audio[step_pos:end_pos] += applied

            # Apply global filter and master volume
            bar_audio = apply_params(bar_audio, "_global")
            bar_audio = bar_audio * self._live_params["master_volume"]

            # Yield in chunks
            for i in range(0, len(bar_audio), chunk_size):
                chunk = bar_audio[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
                yield chunk

            position += samples_per_bar
            bar_count += 1

            # Check for external stop signal
            if hasattr(self, '_stream_stop') and self._stream_stop:
                running = False
                self._stream_stop = False

    def _build_sample_cache(self, pattern: Dict, bpm: int) -> Dict[str, np.ndarray]:
        """Pre-generate one-shot samples for all channels."""
        cache = {}
        for channel_name in pattern["patterns"].keys():
            # Determine base frequency/characteristics per channel
            if "kick" in channel_name:
                cache[channel_name] = self.synth.make_kick(freq=55, length_s=0.7)
            elif "hat" in channel_name and "up" in channel_name:
                cache[channel_name] = self.synth.make_hat(length_s=0.08) * 0.6
            elif "hat" in channel_name:
                cache[channel_name] = self.synth.make_hat(length_s=0.12)
            elif "snare" in channel_name:
                cache[channel_name] = self.synth.make_snare(length_s=0.3)
            elif "clap" in channel_name:
                cache[channel_name] = self.synth.make_snare(length_s=0.2) * 0.7
            elif "perc" in channel_name:
                cache[channel_name] = self.synth.make_hat(length_s=0.06) * 0.5
            elif "bass" in channel_name:
                cache[channel_name] = self.synth.make_kick(freq=80, length_s=0.2) * 0.4
            else:
                cache[channel_name] = self.synth.make_hat(length_s=0.1) * 0.3
        return cache

    # Live parameter control methods
    def set_channel_level(self, channel: str, level: float):
        """Set channel volume (0.0 - 2.0)."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"channel_levels": {}}
        self._live_params["channel_levels"][channel] = max(0.0, min(2.0, level))

    def set_channel_mute(self, channel: str, mute: bool):
        """Mute/unmute channel."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"mute": {}}
        self._live_params["mute"][channel] = mute

    def set_channel_solo(self, channel: str, solo: bool):
        """Solo channel."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"solo": {}}
        self._live_params["solo"][channel] = solo

    def set_channel_filter(self, channel: str, cutoff: float, resonance: float = 1.0):
        """Set channel filter cutoff (Hz) and resonance."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"channel_filters": {}}
        if channel not in self._live_params["channel_filters"]:
            self._live_params["channel_filters"][channel] = {}
        self._live_params["channel_filters"][channel]["cutoff"] = max(20, min(20000, cutoff))
        self._live_params["channel_filters"][channel]["resonance"] = max(0.1, min(10.0, resonance))

    def set_channel_pitch(self, channel: str, pitch: float):
        """Set channel pitch ratio (0.5 - 2.0)."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"channel_pitch": {}}
        self._live_params["channel_pitch"][channel] = max(0.25, min(4.0, pitch))

    def set_channel_decay(self, channel: str, decay: float):
        """Set channel decay multiplier (0.1 - 5.0)."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"channel_decay": {}}
        self._live_params["channel_decay"][channel] = max(0.1, min(5.0, decay))

    def set_global_filter(self, cutoff: float, resonance: float = 1.0):
        """Set global filter."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"global_filter": {}}
        self._live_params["global_filter"]["cutoff"] = max(20, min(20000, cutoff))
        self._live_params["global_filter"]["resonance"] = max(0.1, min(10.0, resonance))

    def set_master_volume(self, volume: float):
        """Set master volume (0.0 - 2.0)."""
        if not hasattr(self, '_live_params'):
            self._live_params = {"master_volume": 1.0}
        self._live_params["master_volume"] = max(0.0, min(2.0, volume))

    def set_bpm(self, bpm: int):
        """Change BPM live."""
        if not hasattr(self, '_live_params'):
            self._live_params = {}
        self._live_params["bpm"] = max(60, min(200, bpm))

    def set_swing(self, swing: float):
        """Set swing amount (0.0 - 0.5)."""
        if not hasattr(self, '_live_params'):
            self._live_params = {}
        self._live_params["swing"] = max(0.0, min(0.5, swing))

    def stop_stream(self):
        """Signal the stream generator to stop."""
        self._stream_stop = True

    # ============================================================
    # MIDI CONTROL
    # ============================================================

    def start_midi_listener(self, port_name: Optional[str] = None):
        """Start listening for MIDI CC messages to control parameters."""
        if not HAS_RTMIDI and not HAS_MIDO:
            raise RuntimeError("rtmidi or mido not available")

        self._midi_running = True

        def midi_loop():
            if HAS_MIDO:
                try:
                    if port_name:
                        port = mido.open_input(port_name)
                    else:
                        # Try to find a suitable port
                        ports = mido.get_input_names()
                        if not ports:
                            return
                        port = mido.open_input(ports[0])

                    for msg in port:
                        if not self._midi_running:
                            break
                        self._handle_midi_message(msg)
                except Exception as e:
                    print(f"MIDI error: {e}")
            elif HAS_RTMIDI:
                # rtmidi implementation
                pass

        import threading
        self._midi_thread = threading.Thread(target=midi_loop, daemon=True)
        self._midi_thread.start()

    def stop_midi_listener(self):
        """Stop MIDI listener."""
        self._midi_running = False

    def _handle_midi_message(self, msg):
        """Map MIDI CC to parameters."""
        if msg.type == 'control_change':
            cc = msg.control
            value = msg.value / 127.0

            # Default mapping (customizable)
            # CC 1-8: Channel levels
            if 1 <= cc <= 8:
                channels = list(self._live_params.get("channel_levels", {}).keys())
                if cc - 1 < len(channels):
                    self.set_channel_level(channels[cc - 1], value * 2.0)
            # CC 9-16: Channel mutes
            elif 9 <= cc <= 16:
                channels = list(self._live_params.get("mute", {}).keys())
                if cc - 9 < len(channels):
                    self.set_channel_mute(channels[cc - 9], value > 0.5)
            # CC 17-24: Channel filters
            elif 17 <= cc <= 24:
                channels = list(self._live_params.get("channel_filters", {}).keys())
                if cc - 17 < len(channels):
                    self.set_channel_filter(channels[cc - 17], 20000 * value + 20)
            # CC 25: Master volume
            elif cc == 25:
                self.set_master_volume(value * 2.0)
            # CC 26: Global filter
            elif cc == 26:
                self.set_global_filter(20000 * value + 20)
            # CC 27: BPM
            elif cc == 27:
                self.set_bpm(int(60 + value * 140))
            # CC 28: Swing
            elif cc == 28:
                self.set_swing(value * 0.5)

    # ============================================================
    # ABLETON LINK SYNC
    # ============================================================

    def start_ableton_link(self, bpm: int = 120):
        """Start Ableton Link session for sync with FL Studio/Ableton."""
        if not HAS_LINK:
            raise RuntimeError("linkables not available (pip install linkables)")

        self._link = AbletonLink()
        self._link.connect()
        self._link.set_tempo(bpm)
        self._link.start()

        # Start beat callback
        import threading
        self._link_running = True

        def link_loop():
            while self._link_running:
                beat = self._link.beat_at_time(time.time(), quantum=4.0)
                phase = self._link.phase_at_time(time.time(), quantum=4.0)
                # Could use this for quantization
                time.sleep(0.01)

        self._link_thread = threading.Thread(target=link_loop, daemon=True)
        self._link_thread.start()

    def stop_ableton_link(self):
        """Stop Ableton Link."""
        if hasattr(self, '_link'):
            self._link_running = False
            self._link.disconnect()

    def get_pattern_library(self):
        """List all available genres and their info."""
        lib = {}
        for name, data in GENRE_PATTERNS.items():
            lib[name] = {
                "bpm_range": data["bpm_range"],
                "instruments": list(data["patterns"].keys()),
                "swing": data.get("swing", 0),
            }
        return lib

    def describe(self, result):
        """Human-readable description of generated beat."""
        return (
            f"Genre: {result['genre'].replace('_', ' ').title()} | "
            f"BPM: {result['bpm']} | "
            f"Bars: {result['bars']} | "
            f"Duration: {result['duration']:.1f}s | "
            f"Instruments: {len(result['stems'])}"
        )

    # ============================================================
    # ARRANGEMENT BLUEPRINTS (absorbed from RemixLab)
    # ============================================================

    ARRANGEMENT_BLUEPRINTS = {
        "afro_house": {
            "bpm": 122,
            "drum_feel": "organik perkisyon, sicak alt frekans, akici groove",
            "bass": "yuvarlak sub bass, az ama etkili senkop",
            "arrangement": [
                ("GIRIS", 32, "perkisyon ve atmosfer"),
                ("VOKAL IPUCU", 16, "tek cumlelik vokal kesiti"),
                ("GROOVE KILIDI", 32, "tam davul ve bass"),
                ("ARA BOLUM", 16, "vokal cumle ve pad"),
                ("ANA DROP", 64, "ana groove, her 8 barda vokal cevap"),
                ("CIKIS", 32, "DJ mix cikisi icin sade davul"),
            ],
        },
        "tech_house": {
            "bpm": 126,
            "drum_feel": "siki kick, tok clap, kuru hi-hat",
            "bass": "kisa ve yuruyen bassline",
            "arrangement": [
                ("GIRIS", 16, "kick ve hi-hat"),
                ("HOOK KESITI", 16, "vokal hook ritmi"),
                ("ANA DROP", 64, "bassline ve hook kesiti"),
                ("ARA BOLUM", 16, "filtrelenmis vokal"),
                ("IKINCI DROP", 64, "tam groove"),
                ("CIKIS", 16, "DJ dostu davul cikisi"),
            ],
        },
        "melodic_house": {
            "bpm": 123,
            "drum_feel": "yumusa kick, shaker, genis atmosfer",
            "bass": "sicak ve uzayan bass",
            "arrangement": [
                ("GIRIS", 32, "doku ve nabiz"),
                ("TEMA", 32, "melodi motifi"),
                ("VOKAL ARA", 32, "ana vokal cumlesi"),
                ("ANA DROP", 64, "melodi ve groove"),
                ("SON YUKSELIS", 32, "vokal ve melodi varyasyonu"),
                ("CIKIS", 32, "mix cikisi icin atmosfer"),
            ],
        },
        "reggaeton": {
            "bpm": 96,
            "drum_feel": "dembow groove, net snare, latin perkisyon",
            "bass": "dembow vurgularini takip eden sade sub",
            "arrangement": [
                ("GIRIS", 8, "dembow ipucu"),
                ("VERSE", 32, "ana vokal"),
                ("HOOK", 32, "tam ritim"),
                ("ARA BOLUM", 8, "vokal durusu"),
                ("IKINCI HOOK", 32, "ritim ve adlib"),
                ("CIKIS", 16, "DJ mix icin davul"),
            ],
        },
        "hip_hop": {
            "bpm": 92,
            "drum_feel": "boom bap groove, heavy snare, swung hat",
            "bass": "derin 808 sub bass",
            "arrangement": [
                ("GIRIS", 8, "atmosfer ve sample"),
                ("VERSE 1", 32, "ana vokal"),
                ("HOOK", 16, "tekrarlanan motif"),
                ("VERSE 2", 32, "ana vokal varyasyonu"),
                ("HOOK", 16, "tekrar"),
                ("CIKIS", 16, "outro"),
            ],
        },
    }

    def build_arrangement(self, genre: str, bars: int = 64) -> List[Dict]:
        """Build an arrangement plan from genre blueprint."""
        blueprint = self.ARRANGEMENT_BLUEPRINTS.get(genre.lower(), self.ARRANGEMENT_BLUEPRINTS.get("tech_house", {}))
        if not blueprint:
            return []

        arrangement = []
        total_bars = 0
        for section, section_bars, instruction in blueprint.get("arrangement", []):
            if total_bars >= bars:
                break
            actual_bars = min(section_bars, bars - total_bars)
            arrangement.append({
                "section": section,
                "bars": actual_bars,
                "instruction": instruction,
                "start_bar": total_bars,
                "start_time": total_bars * (60.0 / blueprint.get("bpm", 126)) * 4,
            })
            total_bars += actual_bars

        return arrangement

    def build_remix_blueprint(self, track: Dict, target_style: str = "tech_house") -> Dict:
        """Build a remix blueprint for a track."""
        style = target_style.lower()
        blueprint = self.ARRANGEMENT_BLUEPRINTS.get(style, self.ARRANGEMENT_BLUEPRINTS["tech_house"])

        source_bpm = float(track.get("bpm", 0) or 0)
        target_bpm = blueprint.get("bpm", 126)
        pitch_percent = round(((target_bpm - source_bpm) / source_bpm) * 100, 2) if source_bpm else 0

        return {
            "track": track.get("name", "UNKNOWN"),
            "source_bpm": source_bpm,
            "target_bpm": target_bpm,
            "tempo_change_percent": pitch_percent,
            "key": track.get("camelot", track.get("key", "")),
            "drum_feel": blueprint.get("drum_feel", ""),
            "bass": blueprint.get("bass", ""),
            "arrangement": self.build_arrangement(style, bars=64),
            "stem_plan": [
                "Vokal: ayir, temizle",
                "Davul: hedef tarza uygun groove ile degistir",
                "Bass: hedef tarza ve tona gore yeniden yaz",
                "Diger: sadece remixe hizmet eden dokulari kullan",
            ],
        }
