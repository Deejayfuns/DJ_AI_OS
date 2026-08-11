"""
DJ AI OS — Music Intelligence Engine

The BRAIN that understands music.
Uses librosa + numpy for real audio analysis:
- BPM detection (onset strength + autocorrelation)
- Key detection (chromagram + Krumhansl-Schmuckler)
- Energy classification (RMS + spectral centroid)
- Mood mapping (multi-feature classification)
- Track fingerprinting (for similarity)

This is NOT algorithmic guessing — it's real audio signal processing.
"""

import os
import math
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

# ============================================================
# CAMELOT WHEEL (real music theory)
# ============================================================

CAMELOT_WHEEL = {
    "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B",
    "B": "1B", "F#": "2B", "Db": "3B", "Ab": "4B", "Eb": "5B",
    "Bb": "6B", "F": "7B",
    "Am": "8A", "Em": "9A", "Bm": "10A", "F#m": "11A", "C#m": "12A",
    "G#m": "1A", "D#m": "2A", "Bbm": "3A", "Fm": "4A", "Cm": "5A",
    "Gm": "6A", "Dm": "7A",
}

KEY_COMPAT = {
    "8A": ["8A", "7A", "9A", "8B"], "9A": ["9A", "8A", "10A", "9B"],
    "10A": ["10A", "9A", "11A", "10B"], "11A": ["11A", "10A", "12A", "11B"],
    "12A": ["12A", "11A", "1A", "12B"], "1A": ["1A", "12A", "2A", "1B"],
    "2A": ["2A", "1A", "3A", "2B"], "3A": ["3A", "2A", "4A", "3B"],
    "4A": ["4A", "3A", "5A", "4B"], "5A": ["5A", "4A", "6A", "5B"],
    "6A": ["6A", "5A", "7A", "6B"], "7A": ["7A", "6A", "8A", "7B"],
    "8B": ["8B", "7B", "9B", "8A"], "9B": ["9B", "8B", "10B", "9A"],
    "10B": ["10B", "9B", "11B", "10A"], "11B": ["11B", "10B", "12B", "11A"],
    "12B": ["12B", "11B", "1B", "12A"], "1B": ["1B", "12B", "2B", "1A"],
    "2B": ["2B", "1B", "3B", "2A"], "3B": ["3B", "2B", "4B", "3A"],
    "4B": ["4B", "3B", "5B", "4A"], "5B": ["5B", "4B", "6B", "5A"],
    "6B": ["6B", "5B", "7B", "6A"], "7B": ["7B", "6B", "8B", "7A"],
}

# Krumhansl-Schmuckler key profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class MusicIntelligence:
    """
    Real music intelligence engine using librosa + numpy.
    Analyzes actual audio signal, not just metadata.
    """

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length

    def analyze_file(self, path: str) -> Dict[str, Any]:
        """
        Full analysis of an audio file.
        Returns comprehensive music intelligence data.
        """
        if not HAS_LIBROSA:
            return self._fallback_analysis(path)

        try:
            y, sr = librosa.load(path, sr=self.sr, mono=True, duration=180)
        except Exception as e:
            return {"error": f"Load failed: {e}"}

        if y is None or len(y) == 0:
            return {"error": "Empty audio"}

        duration = len(y) / sr

        # Core analysis
        bpm, beat_frames = self._detect_bpm(y, sr)
        key, key_confidence = self._detect_key(y, sr)
        energy = self._compute_energy(y)
        brightness = self._compute_brightness(y, sr)
        danceability = self._compute_danceability(y, sr, bpm)
        roughness = self._compute_roughness(y, sr)
        vocal_risk = self._compute_vocal_risk(y, sr)
        dynamic_range = self._compute_dynamic_range(y)

        # Beat grid
        beat_times = librosa.frames_to_time(beat_frames, sr=sr) if beat_frames is not None else []
        tempo_stability = self._compute_tempo_stability(y, sr)

        # Mood classification
        mood = self._classify_mood(energy, brightness, danceability, roughness, vocal_risk)

        # Fingerprint
        fingerprint = self._compute_fingerprint(y, sr)

        return {
            "duration": round(duration, 2),
            "bpm": round(bpm, 1),
            "key": key,
            "key_confidence": round(key_confidence, 3),
            "camelot": CAMELOT_WHEEL.get(key, ""),
            "energy": round(energy, 3),
            "brightness": round(brightness, 3),
            "danceability": round(danceability, 3),
            "roughness": round(roughness, 3),
            "vocal_risk": round(vocal_risk, 3),
            "dynamic_range": round(dynamic_range, 3),
            "tempo_stability": round(tempo_stability, 3),
            "mood": mood,
            "beat_count": len(beat_times),
            "beat_times": beat_times.tolist()[:100],  # First 100 beats
            "fingerprint": fingerprint,
            "engine": "librosa",
        }

    def analyze_array(self, y: np.ndarray, sr: int = None) -> Dict[str, Any]:
        """Analyze a numpy audio array directly."""
        sr = sr or self.sr
        duration = len(y) / sr

        bpm, beat_frames = self._detect_bpm(y, sr)
        key, key_confidence = self._detect_key(y, sr)
        energy = self._compute_energy(y)
        brightness = self._compute_brightness(y, sr)
        danceability = self._compute_danceability(y, sr, bpm)
        mood = self._classify_mood(energy, brightness, danceability, 0.3, 0.2)

        return {
            "duration": round(duration, 2),
            "bpm": round(bpm, 1),
            "key": key,
            "camelot": CAMELOT_WHEEL.get(key, ""),
            "energy": round(energy, 3),
            "brightness": round(brightness, 3),
            "danceability": round(danceability, 3),
            "mood": mood,
            "engine": "librosa_array",
        }

    # ============================================================
    # BPM DETECTION
    # ============================================================

    def _detect_bpm(self, y: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
        """Detect BPM using onset strength + autocorrelation."""
        # Onset strength envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=self.hop_length)

        # Tempo estimation via autocorrelation
        tempo, beat_frames = librosa.beat.beat_track(
            y=y, sr=sr, hop_length=self.hop_length, onset_envelope=onset_env
        )

        # Handle array vs scalar
        if hasattr(tempo, '__len__'):
            bpm = float(tempo[0]) if len(tempo) > 0 else 120.0
        else:
            bpm = float(tempo)

        return bpm, beat_frames

    def _compute_tempo_stability(self, y: np.ndarray, sr: int) -> float:
        """How stable is the tempo (0=erratic, 1=metronomic)."""
        try:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            if beat_frames is None or len(beat_frames) < 4:
                return 0.5

            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            intervals = np.diff(beat_times)

            if len(intervals) == 0:
                return 0.5

            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)

            if mean_interval == 0:
                return 0.5

            cv = std_interval / mean_interval
            stability = max(0.0, min(1.0, 1.0 - cv * 2))
            return stability
        except Exception:
            return 0.5

    # ============================================================
    # KEY DETECTION
    # ============================================================

    def _detect_key(self, y: np.ndarray, sr: int) -> Tuple[str, float]:
        """Detect musical key using chromagram + Krumhansl-Schmuckler."""
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=self.hop_length)
        chroma_mean = np.mean(chroma, axis=1)

        # Normalize
        if np.sum(chroma_mean) > 0:
            chroma_mean = chroma_mean / np.sum(chroma_mean) * 12

        best_key = "C"
        best_corr = -1
        is_minor = False

        # Test all 24 keys (12 major + 12 minor)
        for i in range(12):
            # Shift chroma to test each key
            shifted = np.roll(chroma_mean, -i)

            # Major correlation
            major_corr = np.corrcoef(shifted, MAJOR_PROFILE)[0, 1]
            if major_corr > best_corr:
                best_corr = major_corr
                best_key = KEY_NAMES[i]
                is_minor = False

            # Minor correlation
            minor_corr = np.corrcoef(shifted, MINOR_PROFILE)[0, 1]
            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = KEY_NAMES[i]
                is_minor = True

        # Format as note name
        if is_minor:
            key_name = best_key + "m"
        else:
            key_name = best_key

        confidence = max(0.0, min(1.0, (best_corr + 1) / 2))

        return key_name, confidence

    # ============================================================
    # AUDIO FEATURES
    # ============================================================

    def _compute_energy(self, y: np.ndarray) -> float:
        """Compute perceived energy (0-1)."""
        rms = np.sqrt(np.mean(y ** 2))
        energy = min(1.0, rms * 5)
        return energy

    def _compute_brightness(self, y: np.ndarray, sr: int) -> float:
        """Compute spectral brightness (0-1)."""
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        mean_centroid = np.mean(spectral_centroid)
        brightness = min(1.0, mean_centroid / 5000)
        return brightness

    def _compute_danceability(self, y: np.ndarray, sr: int, bpm: float) -> float:
        """Compute danceability (0-1) based on beat strength and tempo."""
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_mean = np.mean(onset_env)
        onset_std = np.std(onset_env)

        # Onset regularity
        if onset_mean > 0:
            regularity = 1.0 - (onset_std / (onset_mean + 1e-9))
        else:
            regularity = 0.5

        # Tempo bonus (120-130 BPM is most danceable)
        if 118 <= bpm <= 132:
            tempo_bonus = 0.2
        elif 110 <= bpm <= 140:
            tempo_bonus = 0.1
        else:
            tempo_bonus = 0.0

        danceability = min(1.0, max(0.0, regularity * 0.8 + tempo_bonus))
        return danceability

    def _compute_roughness(self, y: np.ndarray, sr: int) -> float:
        """Compute spectral roughness (0-1)."""
        S = np.abs(librosa.stft(y))
        spectral_roughness = np.mean(np.diff(S, axis=1) ** 2)
        roughness = min(1.0, spectral_roughness / 0.1)
        return roughness

    def _compute_vocal_risk(self, y: np.ndarray, sr: int) -> float:
        """Estimate vocal presence (0-1)."""
        # Vocal range: 300-3000 Hz
        S = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)

        vocal_mask = (freqs >= 300) & (freqs <= 3000)
        vocal_energy = np.mean(S[vocal_mask, :]) if np.any(vocal_mask) else 0
        total_energy = np.mean(S) + 1e-9

        vocal_ratio = vocal_energy / total_energy
        vocal_risk = min(1.0, vocal_ratio * 2)
        return vocal_risk

    def _compute_dynamic_range(self, y: np.ndarray) -> float:
        """Compute dynamic range (0-1)."""
        rms = np.sqrt(np.mean(y ** 2))
        peak = np.max(np.abs(y))

        if peak > 0:
            dr = 20 * np.log10(peak / (rms + 1e-9))
            dr_normalized = min(1.0, dr / 20)
        else:
            dr_normalized = 0.5

        return dr_normalized

    # ============================================================
    # MOOD CLASSIFICATION
    # ============================================================

    def _classify_mood(self, energy, brightness, danceability, roughness, vocal_risk) -> str:
        """Classify track mood from audio features."""
        if energy > 0.75 and brightness > 0.6:
            return "euphoric"
        if energy > 0.7 and roughness > 0.5:
            return "aggressive"
        if energy > 0.6 and danceability > 0.6:
            return "energetic"
        if energy < 0.4 and brightness < 0.4:
            return "dark"
        if vocal_risk > 0.6:
            return "vocal"
        if energy < 0.5 and brightness > 0.5:
            return "chill"
        if danceability > 0.7:
            return "groovy"
        return "neutral"

    # ============================================================
    # FINGERPRINT
    # ============================================================

    def _compute_fingerprint(self, y: np.ndarray, sr: int) -> str:
        """Compute a compact audio fingerprint for similarity matching."""
        # Use spectral centroid + zero crossing rate + RMS as fingerprint
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        zcr = np.mean(librosa.feature.zero_crossing_rate(y))
        rms = np.sqrt(np.mean(y ** 2))

        raw = f"{centroid:.0f}-{zcr:.4f}-{rms:.4f}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    # ============================================================
    # COMPATIBILITY
    # ============================================================

    def key_compatibility(self, key1: str, key2: str) -> Dict[str, Any]:
        """Check harmonic compatibility between two keys."""
        from app.ai.library_ai import LibraryAI
        compat_keys = LibraryAI.key_compatibility(None, key1)
        compatible = key2 in compat_keys

        # Distance on Camelot wheel
        try:
            num1 = int(key1[:-1])
            letter1 = key1[-1]
            num2 = int(key2[:-1])
            letter2 = key2[-1]

            pos1 = num1 - 1 if letter1 == "A" else num1 + 11
            pos2 = num2 - 1 if letter2 == "A" else num2 + 11

            distance = min(abs(pos1 - pos2), 24 - abs(pos1 - pos2))
        except (ValueError, IndexError):
            distance = 12

        return {
            "compatible": compatible,
            "distance": distance,
            "advice": "Harmonik uyumlu — güvenle gec" if compatible
                     else f"Uzak tonlar ({distance} adım) — yumusak gecis onerilir",
        }

    # ============================================================
    # FALLBACK (no librosa)
    # ============================================================

    def _fallback_analysis(self, path: str) -> Dict[str, Any]:
        """Basic analysis without librosa."""
        try:
            import wave
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                sr = wf.getframerate()
                duration = frames / sr
        except Exception:
            duration = 0

        return {
            "duration": round(duration, 2),
            "bpm": 0,
            "key": "",
            "camelot": "",
            "energy": 0.5,
            "brightness": 0.5,
            "danceability": 0.5,
            "roughness": 0.3,
            "vocal_risk": 0.3,
            "dynamic_range": 0.5,
            "tempo_stability": 0.5,
            "mood": "neutral",
            "beat_count": 0,
            "fingerprint": "",
            "engine": "fallback",
        }
