"""
DJ AI OS — Real-time AI Ear (Streaming Audio Analysis)

Analyzes live audio stream in real-time:
- Onset/beat detection
- Spectral features (brightness, energy)
- Vocal detection
- Key/chroma tracking
- Dynamic range monitoring
- Auto-mix suggestions based on live analysis
"""

import numpy as np
import threading
import time
from collections import deque
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

try:
    import librosa
    HAS_LIBROSA = True
except Exception:
    HAS_LIBROSA = False

try:
    import crepe
    HAS_CREPE = True
except Exception:
    HAS_CREPE = False

try:
    import aubio
    HAS_AUBIO = True
except Exception:
    HAS_AUBIO = False


@dataclass
class RealtimeAnalysis:
    """Real-time analysis results."""
    # Beat tracking
    bpm: float = 0.0
    beat_confidence: float = 0.0
    beat_phase: float = 0.0  # 0-1 position in bar

    # Spectral
    spectral_centroid: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_flux: float = 0.0
    rms_energy: float = 0.0

    # Vocal
    vocal_probability: float = 0.0
    vocal_present: bool = False

    # Harmonic
    key: str = "Unknown"
    key_confidence: float = 0.0
    chroma: np.ndarray = field(default_factory=lambda: np.zeros(12))

    # Dynamics
    dynamic_range: float = 0.0
    peak_level: float = 0.0
    crest_factor: float = 0.0

    # Mix suggestions
    suggested_eq: Dict[str, float] = field(default_factory=dict)
    suggested_compression: Dict[str, float] = field(default_factory=dict)

    # Timestamp
    timestamp: float = 0.0
    frame_count: int = 0


class RealtimeAIEar:
    """
    Real-time audio analysis for live performance.

    Processes audio in chunks, maintains rolling buffers for analysis.
    Designed to run in a separate thread with low latency.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        chunk_size: int = 1024,
        analysis_interval: int = 4,  # Analyze every N chunks
        buffer_seconds: float = 4.0
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.analysis_interval = analysis_interval

        # Rolling buffer for analysis
        buffer_samples = int(buffer_seconds * sample_rate)
        self._buffer = np.zeros(buffer_samples)
        self._buffer_pos = 0
        self._buffer_filled = False

        # Analysis state
        self._current = RealtimeAnalysis()
        self._history = deque(maxlen=100)  # Keep last 100 analyses
        self._chunk_counter = 0

        # Beat detection (using aubio if available)
        self._tempo_detector = None
        self._onset_detector = None
        if HAS_AUBIO:
            buffer_size = 1024
            hop_size = 512
            self._tempo_detector = aubio.tempo("default", buffer_size, hop_size, sample_rate)
            self._onset_detector = aubio.onset("default", buffer_size, hop_size, sample_rate)

        # Callbacks
        self.on_beat: Optional[Callable[[float], None]] = None
        self.on_analysis: Optional[Callable[[RealtimeAnalysis], None]] = None
        self.on_vocal_change: Optional[Callable[[bool], None]] = None

        # Thread control
        self._running = False
        self._analysis_thread = None

        # Auto-mix state
        self._target_bpm = 120
        self._target_key = "8A"

    def start(self):
        """Start analysis thread."""
        if self._running:
            return
        self._running = True
        self._analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._analysis_thread.start()

    def stop(self):
        """Stop analysis thread."""
        self._running = False
        if self._analysis_thread:
            self._analysis_thread.join(timeout=1.0)

    def process_chunk(self, chunk: np.ndarray):
        """Feed audio chunk to analyzer (call from audio thread)."""
        # Write to rolling buffer
        chunk = chunk.astype(np.float32)
        if chunk.ndim > 1:
            chunk = chunk.mean(axis=1)  # Mono

        end = self._buffer_pos + len(chunk)
        if end <= len(self._buffer):
            self._buffer[self._buffer_pos:end] = chunk
        else:
            # Wrap around
            first = len(self._buffer) - self._buffer_pos
            self._buffer[self._buffer_pos:] = chunk[:first]
            self._buffer[:end - len(self._buffer)] = chunk[first:]

        self._buffer_pos = end % len(self._buffer)
        # Buffer is filled once we've written at least one full buffer worth
        if not self._buffer_filled and end >= len(self._buffer):
            self._buffer_filled = True

        self._chunk_counter += 1

    def _analysis_loop(self):
        """Background analysis loop."""
        while self._running:
            # Sleep for the duration of analysis_interval chunks
            time.sleep(self.chunk_size * self.analysis_interval / self.sample_rate)

            if not self._buffer_filled:
                continue

            try:
                self._analyze_buffer()
            except Exception as exc:
                # Never let the analysis thread die silently
                import traceback
                traceback.print_exc()

    def _analyze_buffer(self):
        """Analyze current buffer."""
        # Get contiguous buffer
        if self._buffer_pos == 0:
            audio = self._buffer.copy()
        else:
            audio = np.concatenate([self._buffer[self._buffer_pos:], self._buffer[:self._buffer_pos]])

        # Ensure mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # --- RMS Energy ---
        rms = np.sqrt(np.mean(audio**2))
        peak = np.max(np.abs(audio))
        crest = peak / (rms + 1e-9)

        # --- Spectral Features (using FFT) ---
        n_fft = min(2048, len(audio))
        hop = n_fft // 4
        stft = np.abs(np.fft.rfft(audio[:n_fft]))
        freqs = np.fft.rfftfreq(n_fft, 1/self.sample_rate)

        if np.sum(stft) > 0:
            # Spectral centroid
            centroid = np.sum(freqs * stft) / np.sum(stft)
            # Spectral rolloff (85%)
            cumsum = np.cumsum(stft)
            rolloff_idx = np.where(cumsum >= 0.85 * cumsum[-1])[0]
            rolloff = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 0
            # Spectral flux (simplified)
            flux = np.mean(np.diff(stft)**2) if len(stft) > 1 else 0
        else:
            centroid = rolloff = flux = 0

        # --- Beat Detection ---
        bpm = 0
        beat_confidence = 0
        beat_phase = 0

        if self._tempo_detector and HAS_AUBIO:
            # Process in hop-sized chunks
            for i in range(0, len(audio) - hop, hop):
                chunk = audio[i:i+hop].astype(np.float32)
                if self._tempo_detector(chunk):
                    bpm = self._tempo_detector.get_bpm()
                    beat_confidence = self._tempo_detector.get_confidence()
                    # Calculate phase
                    beat_phase = (self._tempo_detector.get_last() % hop) / hop
        else:
            # Lightweight BPM fallback: autocorrelation of the energy envelope.
            # No extra dependencies — safe for real-time.
            try:
                bpm, beat_confidence = self._estimate_bpm(audio)
            except Exception:
                bpm, beat_confidence = 0.0, 0.0

        # --- Key/Chroma Detection (fast FFT-based, no librosa) ---
        key = "Unknown"
        key_conf = 0
        chroma = self._fast_chroma(stft, freqs)

        if np.sum(chroma) > 0:
            key_idx = int(np.argmax(chroma))
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key = keys[key_idx]
            key_conf = float(chroma[key_idx] / (np.sum(chroma) + 1e-9))

        # --- Vocal Detection (simplified) ---
        vocal_prob = 0.0
        # High spectral flux in vocal range (200-4000 Hz) + formants
        vocal_mask = (freqs >= 200) & (freqs <= 4000)
        if np.any(vocal_mask):
            vocal_energy = np.sum(stft[vocal_mask])
            total_energy = np.sum(stft)
            vocal_prob = vocal_energy / (total_energy + 1e-9)

        vocal_present = vocal_prob > 0.3

        # --- Dynamic Range ---
        dynamic_range = 20 * np.log10(peak / (rms + 1e-9))

        # --- Build Analysis ---
        analysis = RealtimeAnalysis(
            bpm=bpm,
            beat_confidence=beat_confidence,
            beat_phase=beat_phase,
            spectral_centroid=float(centroid),
            spectral_rolloff=float(rolloff),
            spectral_flux=float(flux),
            rms_energy=float(rms),
            vocal_probability=float(vocal_prob),
            vocal_present=vocal_present,
            key=key,
            key_confidence=float(key_conf),
            chroma=chroma,
            dynamic_range=float(dynamic_range),
            peak_level=float(peak),
            crest_factor=float(crest),
            timestamp=time.time(),
            frame_count=self._chunk_counter,
        )

        # --- Auto-Mix Suggestions ---
        self._generate_mix_suggestions(analysis)

        # Update state
        self._current = analysis
        self._history.append(analysis)

        # Callbacks
        if self.on_beat and bpm > 0 and beat_confidence > 0.5:
            self.on_beat(bpm)
        if self.on_analysis:
            self.on_analysis(analysis)
        if self.on_vocal_change:
            self.on_vocal_change(vocal_present)

    @staticmethod
    def _estimate_bpm(audio: np.ndarray, sr: int = 44100) -> tuple:
        """
        Estimate BPM via autocorrelation of the short-time energy envelope.
        Returns (bpm, confidence) — both 0.0 if no clear beat found.
        Lightweight (numpy only), fast enough for real-time use.
        """
        if audio is None or len(audio) < sr // 4:
            return 0.0, 0.0

        # Downmix + normalize
        y = audio.astype(np.float32)
        if y.ndim > 1:
            y = y.mean(axis=1)
        peak = np.max(np.abs(y)) or 1.0
        y = y / peak

        # Short-time RMS energy envelope
        frame = 512
        hop = 256
        n_frames = (len(y) - frame) // hop
        if n_frames < 16:
            return 0.0, 0.0
        frames = y[:n_frames * hop + frame].reshape(-1, hop)[:n_frames]
        env = np.sqrt(np.mean(frames ** 2, axis=1))

        # Remove DC
        env = env - env.mean()

        # Autocorrelation
        corr = np.correlate(env, env, mode="full")
        corr = corr[len(corr) // 2:]

        # Search lags (in env-frame units) corresponding to 40-200 BPM
        # period_frames = 60 * sr / (bpm * hop)
        min_lag = int(60 * sr / (200 * hop))            # ~200 BPM max
        max_lag = int(60 * sr / (40 * hop))             # ~40 BPM min
        min_lag = max(2, min_lag)
        max_lag = min(len(corr) - 1, max_lag)
        if max_lag <= min_lag:
            return 0.0, 0.0

        region = corr[min_lag:max_lag]
        if len(region) == 0 or np.max(region) <= 0:
            return 0.0, 0.0

        lag = int(np.argmax(region)) + min_lag
        bpm = 60.0 * sr / (hop * lag)

        # Confidence: peak prominence vs mean
        mean_corr = np.mean(region)
        confidence = float(np.clip((np.max(region) - mean_corr) / (np.max(region) + 1e-9), 0, 1))

        # Clamp to musical range
        if not (40.0 <= bpm <= 200.0):
            return 0.0, 0.0

        return float(bpm), confidence

    @staticmethod
    def _fast_chroma(stft: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        """
        Fast chromagram from an FFT frame.
        Maps each frequency bin to its pitch class (12 bins, A=0 ... G#=11).
        A4 = 440 Hz reference. Runs in microseconds — safe for real-time.
        """
        chroma = np.zeros(12)
        if stft is None or len(stft) == 0:
            return chroma

        # Avoid the DC bin and above ~8kHz (beyond musical range)
        valid = (freqs >= 30) & (freqs <= 8000)
        if not np.any(valid):
            return chroma

        f = freqs[valid]
        mag = stft[valid]

        # MIDI note number for each bin: 69 + 12*log2(f/440)
        midi = 69 + 12 * np.log2(np.maximum(f, 1e-9) / 440.0)
        # Clamp to a reasonable note range
        midi = np.clip(midi, 12, 108)
        pc = np.round(midi).astype(int) % 12

        np.add.at(chroma, pc, mag)
        return chroma

    def _generate_mix_suggestions(self, analysis: RealtimeAnalysis):
        """Generate EQ/Compression suggestions based on analysis."""
        suggestions_eq = {}
        suggestions_comp = {}

        # Brightness issues
        if analysis.spectral_centroid > 8000:
            suggestions_eq["high_shelf"] = -3.0  # Reduce harshness
        elif analysis.spectral_centroid < 2000:
            suggestions_eq["high_shelf"] = +2.0  # Add brightness

        # Low-end issues
        if analysis.rms_energy > 0.3 and analysis.spectral_centroid < 300:
            suggestions_eq["low_cut"] = 80  # High-pass
            suggestions_eq["low_shelf"] = -2.0

        # Dynamic range
        if analysis.dynamic_range < 6:
            suggestions_comp["ratio"] = 4.0
            suggestions_comp["threshold"] = -12.0
        elif analysis.dynamic_range > 20:
            suggestions_comp["ratio"] = 2.0
            suggestions_comp["threshold"] = -6.0

        # Vocal processing
        if analysis.vocal_present:
            suggestions_eq["vocal_presence"] = +3.0  # 3-5kHz boost
            suggestions_comp["vocal_ratio"] = 3.0

        # BPM mismatch warning
        if self._target_bpm > 0 and analysis.bpm > 0:
            diff = abs(analysis.bpm - self._target_bpm) / self._target_bpm
            if diff > 0.03:
                suggestions_comp["bpm_warning"] = f"BPM drift: {analysis.bpm:.1f} vs {self._target_bpm}"

        analysis.suggested_eq = suggestions_eq
        analysis.suggested_compression = suggestions_comp

    def get_current(self) -> RealtimeAnalysis:
        """Get latest analysis."""
        return self._current

    def get_history(self) -> list:
        """Get analysis history."""
        return list(self._history)

    def set_target_bpm(self, bpm: float):
        """Set target BPM for mix suggestions."""
        self._target_bpm = bpm

    def set_target_key(self, key: str):
        """Set target key for harmonic mixing."""
        self._target_key = key

    def is_beat(self, tolerance: float = 0.1) -> bool:
        """Check if we're currently on a beat."""
        return self._current.beat_confidence > 0.5 and self._current.beat_phase < tolerance


# Convenience function for standalone use
def create_realtime_ear(sample_rate=44100, chunk_size=1024) -> RealtimeAIEar:
    """Create and start a realtime AI ear."""
    ear = RealtimeAIEar(sample_rate=sample_rate, chunk_size=chunk_size)
    ear.start()
    return ear


# Demo / test
if __name__ == "__main__":
    import sounddevice as sd

    ear = create_realtime_ear()

    def audio_callback(indata, frames, time_info, status):
        ear.process_chunk(indata[:, 0])

    def on_analysis(a):
        print(f"BPM: {a.bpm:.1f} | Centroid: {a.spectral_centroid:.0f}Hz | "
              f"Energy: {a.rms_energy:.3f} | Vocal: {a.vocal_present} | "
              f"Key: {a.key} ({a.key_confidence:.2f})")
        if a.suggested_eq:
            print(f"  EQ: {a.suggested_eq}")
        if a.suggested_compression:
            print(f"  Comp: {a.suggested_compression}")

    ear.on_analysis = on_analysis

    print("Listening... Press Ctrl+C to stop")
    try:
        with sd.InputStream(callback=audio_callback, channels=1,
                           samplerate=44100, blocksize=1024):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        ear.stop()