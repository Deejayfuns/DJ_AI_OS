"""
DJ AI OS — DAW Engine (playback)

Renders a DAWProject into audio bar-by-bar. Two block types:

    pattern  -> the track's step sequencer (16 steps = 1 bar), looped
    midi     -> the track's piano-roll notes (times/durations in bars)

The arrangement decides which blocks are active at each bar. Output is
stereo (pan per track). Renders through the instrument plugin registry,
so every plugin (kick, bass_roll, synth_patch, ...) plays in the DAW.

Streaming: DAWEngine.iter_stream(bar_chunks) yields float32 blocks for
sounddevice, like LivePerformanceEngine.iter_stream.
"""

import threading
import time

import numpy as np

from .instruments import get_instrument, has_instrument
from .daw_project import DAWProject

SCALE_MINOR = [0, 2, 3, 5, 7, 8, 10]


def bpm_to_bar_seconds(bpm, beats_per_bar=4):
    return 60.0 / bpm * beats_per_bar


class DAWEngine:
    def __init__(self, project=None, sample_rate=44100):
        self.project = project or DAWProject()
        self.sr = sample_rate
        self._insts = {}
        self._dirty = True
        self._pattern_cache = {}   # (track_name, bar_in_clip) -> mono np
        self._note_cache = {}      # (track_name, bar_in_clip) -> mono np
        self.playhead = 0.0        # seconds
        self.playing = False
        self.master_volume = 1.0

    # ---- project changes ----
    def mark_dirty(self):
        self._dirty = True
        self._pattern_cache.clear()
        self._note_cache.clear()

    # ---- instrument access ----
    def _inst(self, track):
        name = track.instrument
        if name not in self._insts:
            if not has_instrument(name):
                name = "bass_roll"
            self._insts[name] = get_instrument(name, sample_rate=self.sr)
        return self._insts[name]

    # ============================================================
    # PER-TRACK RENDER
    # ============================================================
    def _bar_samples(self):
        return int(bpm_to_bar_seconds(self.project.bpm) * self.sr)

    def _step_seconds(self):
        # 16th note
        return 60.0 / self.project.bpm / 4.0

    def _render_pattern_bar(self, track, bar_in_clip):
        """One bar of the track's step pattern (16 steps)."""
        inst = self._inst(track)
        bar_n = self._bar_samples()
        out = np.zeros(bar_n, dtype=np.float32)
        step_dur = self._step_seconds()
        step_n = int(step_dur * self.sr)
        scale = SCALE_MINOR
        for i, hit in enumerate(track.steps[:16]):
            if not hit:
                continue
            vel = track.velocities[i] if i < len(track.velocities) else 1.0
            # bassline walk: move on quarter notes through the scale
            deg = (i // 4) % len(scale)
            note = track.note_root + scale[deg] + track.note_octave * 12
            sig = inst.hit(note=note, velocity=vel)
            pos = int(i * step_n)
            seg = min(len(sig), bar_n - pos)
            if seg > 0:
                out[pos:pos + seg] += sig[:seg]
        return out

    def _render_midi_bar(self, track, bar_in_clip, bar_start, block_start, block_length):
        """One bar of the track's piano-roll notes within this block."""
        inst = self._inst(track)
        bar_n = self._bar_samples()
        out = np.zeros(bar_n, dtype=np.float32)
        # notes whose start falls in this bar (absolute bar time)
        abs_start = bar_start
        abs_end = bar_start + 1.0
        for nt in track.notes:
            nt_abs = block_start + nt["start"]
            if nt_abs < abs_end and nt_abs + nt["dur"] > abs_start:
                frac = nt_abs - abs_start  # 0..1 position in this bar
                sig = inst.hit(note=nt["pitch"], velocity=nt.get("vel", 0.9))
                pos = int(frac * bar_n)
                seg = min(len(sig), bar_n - pos)
                if seg > 0:
                    out[pos:pos + seg] += sig[:seg]
        return out

    # ============================================================
    # BAR MIX
    # ============================================================
    def render_bar(self, bar_index, stems=False):
        """
        Render bar `bar_index` (0-based) -> stereo np.float32.
        If stems=True, return (mix, {track_name: mono}).
        """
        self._ensure_cached_insts()
        bar_n = self._bar_samples()
        mix = np.zeros((2, bar_n), dtype=np.float32)
        # every track always present in stems (muted = zeros) so exports align
        stem_map = {t.name: np.zeros(bar_n, dtype=np.float32)
                    for t in self.project.tracks}

        solo = [t for t in self.project.tracks if t.solo]
        active_ok = (lambda t: not solo or t in solo)

        for blk in self.project.blocks_in_range(bar_index, bar_index + 1):
            track = self.project.get_track(blk["track"])
            if track is None or track.muted or not active_ok(track):
                continue
            bar_in_clip = int(bar_index - blk["start"])
            key = (track.name, blk["type"], bar_in_clip)
            if blk["type"] == "pattern":
                if key not in self._pattern_cache or self._dirty:
                    self._pattern_cache[key] = self._render_pattern_bar(track, bar_in_clip)
                mono = self._pattern_cache[key]
            else:
                if key not in self._note_cache or self._dirty:
                    self._note_cache[key] = self._render_midi_bar(
                        track, bar_in_clip, bar_index, blk["start"], blk["length"])
                mono = self._note_cache[key]

            mono = mono * float(track.volume)
            stem_map.setdefault(track.name, np.zeros(bar_n, dtype=np.float32))
            stem_map[track.name] += mono
            # pan: simple equal-power
            p = float(track.pan)  # -1..1
            gl, gr = 0.707 * (1 - p), 0.707 * (1 + p)
            mix[0] += mono * gl
            mix[1] += mono * gr

        mix *= float(self.project.master.get("volume", 0.9)) * self.master_volume
        if self.project.master.get("limiter", True):
            peak = float(np.max(np.abs(mix)))
            if peak > 0.95:
                mix *= 0.95 / (peak + 1e-9)

        if stems:
            return mix, stem_map
        return mix

    def bounce_mix(self, bars=None, fx=None):
        """Render the whole arrangement to one stereo buffer `(2, N)`.

        `bars`: number of bars (default: whole arrangement). `fx`: an
        optional FXRack — applied per channel, so the DJ AI FX engine can
        sit on top of the real DAW mix (this is how the Pioneer Link panel
        plays "live FX over the set")."""
        total = bars if bars is not None else max(1, self.project.arrangement_length())
        total = max(1, int(total))
        self._ensure_cached_insts()
        parts = [self.render_bar(i) for i in range(total)]
        mix = np.concatenate(parts, axis=1).astype(np.float32)
        if fx is not None:
            from .pioneer_fx import _as_mono
            bpm = self.project.bpm
            L = fx.apply(_as_mono(mix[0]), bpm=bpm)
            R = fx.apply(_as_mono(mix[1]), bpm=bpm)
            mix = np.stack([L, R]).astype(np.float32)
        return mix

    def _ensure_cached_insts(self):
        for t in self.project.tracks:
            self._inst(t)

    # ============================================================
    # STREAMING
    # ============================================================
    def iter_stream(self, chunk_size=1024):
        """Yield float32 blocks while playing (generator)."""
        total_bars = max(1, self.project.arrangement_length())
        bar_idx = 0
        buf = np.zeros((2, 0), dtype=np.float32)
        while self.playing:
            if buf.shape[1] < chunk_size:
                bar = self.render_bar(bar_idx % total_bars)
                buf = np.concatenate([buf, bar], axis=1)
                bar_idx += 1
            out, buf = buf[:, :chunk_size], buf[:, chunk_size:]
            # advance playhead (seconds) for the UI
            secs = chunk_size / self.sr
            self.playhead += secs
            if self.playhead > total_bars * bpm_to_bar_seconds(self.project.bpm):
                self.playhead = 0.0
            yield out.T

    # ---- transport ----
    def play(self):
        self.playing = True

    def stop(self):
        self.playing = False
        self.playhead = 0.0

    def set_bpm(self, bpm):
        self.project.bpm = max(60, min(180, bpm))
        self.mark_dirty()

    # ---- export ----
    def export_wav(self, path, bars=None, stems_dir=None):
        """Bounce the arrangement to a WAV (+ per-track stems if stems_dir)."""
        import scipy.io.wavfile as wav
        total = int(bars) if bars else int(self.project.arrangement_length())
        total = max(1, total)
        self.playing = False
        chunks = [self.render_bar(b) for b in range(total)]
        mix = np.concatenate(chunks, axis=1)
        mix16 = (np.clip(mix.T, -1, 1) * 32767).astype(np.int16)
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        wav.write(path, self.sr, mix16)

        stem_paths = {}
        if stems_dir:
            os.makedirs(stems_dir, exist_ok=True)
            track_names = set()
            for b in range(total):
                _, stems = self.render_bar(b, stems=True)
                track_names.update(stems.keys())
            for tn in track_names:
                acc = np.zeros(0, dtype=np.float32)
                for b in range(total):
                    _, stems = self.render_bar(b, stems=True)
                    seg = stems.get(tn, np.zeros(self._bar_samples(), dtype=np.float32))
                    acc = np.concatenate([acc, seg])
                acc16 = (np.clip(acc, -1, 1) * 32767).astype(np.int16)
                sp = os.path.join(stems_dir, f"{tn}.wav")
                wav.write(sp, self.sr, acc16)
                stem_paths[tn] = sp

        return {"mix": path, "stems": stem_paths, "bars": total, "sr": self.sr}
