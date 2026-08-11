"""
DJ AI OS — Live Performance Engine

The heart of the live beat production system. Routes instrument plugins
through a real-time scheduler that generates bars on demand.

Features:
- Plugin-based channels (any registered instrument)
- 16-step patterns per channel (on/off + velocity + variation)
- Live BPM / swing / bar-length control
- Melodic note generators (scale-driven basslines & arps)
- Per-channel live parameters (automation target)
- Scene switching (pattern banks) — A/B style
- Render-to-file for offline export
"""

import time
import numpy as np

from .instruments import get_instrument, has_instrument, list_instruments

# Common scale intervals (semitones from root), Camelot-ish
SCALES = {
    "minor":    [0, 2, 3, 5, 7, 8, 10],
    "major":    [0, 2, 4, 5, 7, 9, 11],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
    "dorian":   [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "aeolian":  [0, 2, 3, 5, 7, 8, 10],
}


class Channel:
    """One instrument lane with its 16-step pattern and live params."""

    def __init__(self, instrument_name, sample_rate=44100):
        if not has_instrument(instrument_name):
            raise KeyError(f"Unknown instrument: {instrument_name}")
        self.instrument_name = instrument_name
        self.inst = get_instrument(instrument_name, sample_rate=sample_rate)
        # 16 steps: {0|1|velocity 0-1}
        self.steps = [0] * 16
        self.velocities = [1.0] * 16
        self.muted = False
        self.solo = False
        self.level = 1.0
        # melodic: note root + octave (bass/arp/lead)
        self.note_root = 36  # C2
        self.note_octave = 1

    def set_pattern(self, hits):
        """Set the 16-step on/off pattern."""
        if len(hits) != 16:
            raise ValueError("Pattern must be 16 steps")
        self.steps = [int(bool(h)) for h in hits]

    def set_step(self, idx, on, velocity=1.0):
        self.steps[idx] = int(bool(on))
        self.velocities[idx] = velocity

    def toggle_step(self, idx):
        self.steps[idx] = 1 - self.steps[idx]
        return self.steps[idx]

    def set_param(self, key, value):
        self.inst.set_param(key, value)

    def render_note(self, note_idx, bpm, samples_per_beat):
        """Render one step's sound with melodic note (for melodic channels)."""
        vel = self.velocities[note_idx] * self.level
        # melodic channels get a note from their scale sequence
        if self.inst.category == "melodic":
            note = self._scale_note(note_idx)
            return self.inst.hit(note=note, velocity=vel)
        return self.inst.hit(velocity=vel)

    def _scale_note(self, step_idx):
        """Pick a note from the scale for this step (bassline/arp pattern)."""
        scale = SCALES.get("minor", [0, 2, 3, 5, 7, 8, 10])
        degree = step_idx // 2 % len(scale)   # quarter-note movement
        octave = step_idx // (2 * len(scale))
        return self.note_root + scale[degree] + octave * 12 + self.note_octave * 12


class LivePerformanceEngine:
    """
    Real-time beat engine. Usage:

        engine = LivePerformanceEngine(bpm=128)
        engine.add_channel('kick', [1,0,0,0]*4)
        engine.add_channel('bass_saw', [1,0,0,1]*4, note_root=36)
        engine.add_channel('hat', [0,0,1,0]*4)
        engine.set_bpm(130)
        engine.set_channel_param('kick', 'punch', 3.0)
        bar = engine.render_bar()
        # stream: engine.iter_stream(chunk_size=1024)
    """

    def __init__(self, bpm=128, swing=0.0, sample_rate=44100):
        self.bpm = bpm
        self.swing = swing
        self.sr = sample_rate
        self.channels = {}   # name -> Channel
        self.order = []      # channel names in add order
        self._scenes = {}    # scene name -> {channel: (steps, params)}
        self._current_scene = None

    # ============================================================
    # CHANNEL MANAGEMENT
    # ============================================================

    def add_channel(self, name, pattern=None, **kwargs):
        """Add an instrument channel. pattern = 16-step list."""
        ch = Channel(name, sample_rate=self.sr)
        for key in ("note_root", "note_octave", "level"):
            if key in kwargs:
                setattr(ch, key, kwargs[key])
        if pattern:
            ch.set_pattern(pattern)
        self.channels[name] = ch
        if name not in self.order:
            self.order.append(name)
        return ch

    def remove_channel(self, name):
        if name in self.channels:
            del self.channels[name]
            if name in self.order:
                self.order.remove(name)

    def channel_names(self):
        return list(self.order)

    def set_channel_param(self, channel, key, value):
        if channel in self.channels:
            self.channels[channel].set_param(key, value)

    def set_channel_mute(self, channel, muted):
        if channel in self.channels:
            self.channels[channel].muted = bool(muted)

    def set_channel_solo(self, channel, solo):
        if channel in self.channels:
            self.channels[channel].solo = bool(solo)

    def set_channel_pattern(self, channel, pattern):
        if channel in self.channels:
            self.channels[channel].set_pattern(pattern)

    def toggle_step(self, channel, idx):
        if channel in self.channels:
            return self.channels[channel].toggle_step(idx)
        return 0

    # ============================================================
    # GLOBAL
    # ============================================================

    def set_bpm(self, bpm):
        self.bpm = max(60, min(200, int(bpm)))

    def set_swing(self, swing):
        self.swing = max(0.0, min(0.5, float(swing)))

    # ============================================================
    # SCENES (pattern banks)
    # ============================================================

    def capture_scene(self, name):
        """Snapshot current patterns/params into a scene (A/B style)."""
        snap = {}
        for name_ch, ch in self.channels.items():
            snap[name_ch] = (list(ch.steps), ch.get_params() if hasattr(ch, 'get_params') else {})
        self._scenes[name] = snap
        return name

    def recall_scene(self, name):
        """Recall a captured scene."""
        if name not in self._scenes:
            return False
        snap = self._scenes[name]
        for channel, (steps, params) in snap.items():
            if channel in self.channels:
                self.channels[channel].set_pattern(steps)
        self._current_scene = name
        return True

    def scenes(self):
        return list(self._scenes.keys())

    # ============================================================
    # RENDERING
    # ============================================================

    def _timing(self):
        beat_s = 60.0 / self.bpm
        samples_per_beat = int(self.sr * beat_s)
        samples_per_bar = samples_per_beat * 4
        step_samples = samples_per_beat // 4
        return samples_per_bar, step_samples, samples_per_beat

    def _active_channels(self):
        any_solo = any(ch.solo for ch in self.channels.values())
        return [
            name for name, ch in self.channels.items()
            if not ch.muted and (not any_solo or ch.solo)
        ]

    def render_bar(self):
        """
        Render one full bar (4 beats / 16 steps) as a float32 mix.
        Returns (mix, per_channel_stems).
        """
        samples_per_bar, step_samples, _ = self._timing()
        bar = np.zeros(samples_per_bar, dtype=np.float32)
        stems = {}

        for name in self._active_channels():
            ch = self.channels[name]
            stem = np.zeros(samples_per_bar, dtype=np.float32)

            for step_idx, on in enumerate(ch.steps):
                if not on:
                    continue
                # Swing: odd steps (off-beats) shift later
                pos = step_idx * step_samples
                if step_idx % 2 == 1:
                    pos += int(step_samples * self.swing)

                if pos >= samples_per_bar:
                    continue

                sample = ch.render_note(step_idx, self.bpm, step_samples)
                n = min(len(sample), samples_per_bar - pos)
                if n > 0:
                    stem[pos:pos + n] += sample[:n]

            bar += stem
            stems[name] = stem

        # Peak-normalize to avoid clipping
        peak = np.max(np.abs(bar)) or 1.0
        bar = (bar / peak * 0.9).astype(np.float32)
        return bar, stems

    def iter_stream(self, chunk_size=1024):
        """Infinite bar generator — yields float32 chunks for real-time out."""
        while True:
            bar, _ = self.render_bar()
            for i in range(0, len(bar), chunk_size):
                chunk = bar[i:i + chunk_size]
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
                yield chunk

    # ============================================================
    # OFFLINE
    # ============================================================

    def render_track(self, bars=4):
        """Render N bars into a single mix array."""
        chunks = []
        for _ in range(bars):
            bar, _ = self.render_bar()
            chunks.append(bar)
        return np.concatenate(chunks)

    def export_wav(self, path, bars=4, bit_depth=16):
        """Render and export a WAV file."""
        import wave
        mix = self.render_track(bars)
        peak = np.max(np.abs(mix)) or 1.0
        if bit_depth == 16:
            data = np.int16(mix / peak * 32767)
            sw = 2
        else:
            data = np.int32(mix / peak * 8388607)
            sw = 3
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(sw)
            wf.setframerate(self.sr)
            wf.writeframes(data.tobytes())
        return path

    def export_stems(self, out_dir, bars=4, bit_depth=16):
        """Export per-channel stems + a mix into out_dir. Returns paths."""
        import wave
        import os
        os.makedirs(out_dir, exist_ok=True)
        stems = {name: np.zeros(0, dtype=np.float32) for name in self._active_channels()}
        for _ in range(bars):
            _, bar_stems = self.render_bar()
            for name, stem in bar_stems.items():
                stems[name] = np.concatenate([stems[name], stem])

        def _write(arr, path):
            peak = np.max(np.abs(arr)) or 1.0
            if bit_depth == 16:
                data = np.int16(arr / peak * 32767)
                sw = 2
            else:
                data = np.int32(arr / peak * 8388607)
                sw = 3
            with wave.open(path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(sw)
                wf.setframerate(self.sr)
                wf.writeframes(data.tobytes())

        paths = {}
        for name, stem in stems.items():
            p = os.path.join(out_dir, f"{name}.wav")
            _write(stem, p)
            paths[name] = p
        mix = sum(stems.values())
        mix_path = os.path.join(out_dir, "_mix.wav")
        _write(mix, mix_path)
        paths["_mix"] = mix_path
        return paths

    # ============================================================
    # GENRE PRESETS (quick start)
    # ============================================================

    def load_genre(self, genre):
        """Load a genre preset — returns channel count."""
        self.channels = {}
        self.order = []
        presets = {
            "house": {
                "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                "clap":  [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                "hat":   [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
                "bass_saw": [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
            },
            "tech_house": {
                "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                "hat":   [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
                "hat_open": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                "bass_sub": [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1],
            },
            "techno": {
                "kick":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                "hat":   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "rim":   [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                "bass_saw": [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0],
            },
            "trap": {
                "kick_808": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                "snare": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                "hat":  [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                "hat_open": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                "pluck": [1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
            },
            "mars": {
                "kick":  [1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0],
                "hat":   [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                "shaker":[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                "bass_saw": [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 1],
                "pad":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
            },
            "melodic_techno": {
                "kick_tech": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                "hat_tech":  [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
                "bass_roll": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                "tick":      [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
                "arp_pluck": [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                "pad_tech":  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                "riser":     [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            },
        }
        preset = presets.get(genre, presets["house"])
        for name, pattern in preset.items():
            self.add_channel(name, pattern)
        self._genre = genre
        return len(preset)

    def genre(self):
        return getattr(self, "_genre", None)
