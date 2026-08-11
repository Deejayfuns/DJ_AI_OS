"""
DJ AI OS — Audio Quality Analyzer

Professional audio quality analysis:
- Clipping detection
- Dynamic range measurement
- Spectral analysis
- Phase correlation
- Loudness (LUFS approximation)
- Frequency balance
"""

import numpy as np
from typing import Dict, Any

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


class AudioQuality:
    """
    Professional audio quality analysis.
    Detects issues that would affect DJ mixing.
    """

    def analyze(self, y: np.ndarray, sr: int = 22050) -> Dict[str, Any]:
        """
        Comprehensive audio quality analysis.

        Returns quality score + issues list.
        """
        if y is None or len(y) == 0:
            return {"score": 0, "issues": ["Empty audio"], "details": {}}

        issues = []
        details = {}

        # 1. Clipping detection
        clipping = self._detect_clipping(y)
        details["clipping"] = clipping
        if clipping["detected"]:
            issues.append(f"Clipping detected: {clipping['percent']:.1f}% of samples")

        # 2. Dynamic range
        dynamic = self._measure_dynamic_range(y)
        details["dynamic_range"] = dynamic
        if dynamic["range_db"] < 6:
            issues.append(f"Low dynamic range: {dynamic['range_db']:.1f} dB (compressed)")
        elif dynamic["range_db"] > 20:
            issues.append(f"High dynamic range: {dynamic['range_db']:.1f} dB (may clip in mix)")

        # 3. Loudness
        loudness = self._measure_loudness(y)
        details["loudness"] = loudness
        if loudness["peak_db"] > -1:
            issues.append(f"Peak too hot: {loudness['peak_db']:.1f} dBFS (clipping risk)")
        if loudness["rms_db"] < -20:
            issues.append(f"Too quiet: {loudness['rms_db']:.1f} dBFS")

        # 4. Frequency balance
        freq_balance = self._analyze_frequency_balance(y, sr)
        details["frequency_balance"] = freq_balance
        if freq_balance["bass_heavy"]:
            issues.append("Bass-heavy mix (may muddy the low end)")
        if freq_balance["bright"]:
            issues.append("Bright/harsh high end")

        # 5. Phase correlation (if stereo)
        if y.ndim > 1 and y.shape[1] >= 2:
            phase = self._measure_phase(y)
            details["phase"] = phase
            if phase["correlation"] < 0.3:
                issues.append(f"Low phase correlation: {phase['correlation']:.2f} (mono compatibility issue)")

        # 6. Silence detection
        silence = self._detect_silence(y)
        details["silence"] = silence
        if silence["intro_seconds"] > 5:
            issues.append(f"Long intro silence: {silence['intro_seconds']:.1f}s")
        if silence["outro_seconds"] > 5:
            issues.append(f"Long outro silence: {silence['outro_seconds']:.1f}s")

        # 7. Spectral analysis
        spectral = self._spectral_analysis(y, sr)
        details["spectral"] = spectral

        # Calculate overall score
        score = self._calculate_score(issues, dynamic, loudness, freq_balance)

        return {
            "score": score,
            "issues": issues,
            "details": details,
            "grade": self._score_to_grade(score),
        }

    def _detect_clipping(self, y: np.ndarray) -> Dict[str, Any]:
        """Detect digital clipping."""
        threshold = 0.99
        clipped = np.sum(np.abs(y) >= threshold)
        total = len(y)
        percent = (clipped / total) * 100 if total > 0 else 0

        return {
            "detected": percent > 0.01,
            "percent": percent,
            "clipped_samples": int(clipped),
        }

    def _measure_dynamic_range(self, y: np.ndarray) -> Dict[str, Any]:
        """Measure dynamic range."""
        rms = np.sqrt(np.mean(y ** 2))
        peak = np.max(np.abs(y))

        if rms > 0:
            dr = 20 * np.log10(peak / rms)
        else:
            dr = 0

        # Crest factor
        crest = peak / (rms + 1e-9)

        return {
            "range_db": round(dr, 1),
            "crest_factor": round(crest, 2),
            "rms": round(float(rms), 4),
            "peak": round(float(peak), 4),
        }

    def _measure_loudness(self, y: np.ndarray) -> Dict[str, Any]:
        """Measure loudness (approximation of LUFS)."""
        rms = np.sqrt(np.mean(y ** 2))
        peak = np.max(np.abs(y))

        if rms > 0:
            rms_db = 20 * np.log10(rms)
        else:
            rms_db = -100

        if peak > 0:
            peak_db = 20 * np.log10(peak)
        else:
            peak_db = -100

        # Approximation of integrated loudness
        loudness = rms_db

        return {
            "loudness_lufs": round(loudness, 1),
            "rms_db": round(rms_db, 1),
            "peak_db": round(peak_db, 1),
        }

    def _analyze_frequency_balance(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Analyze frequency balance."""
        if not HAS_LIBROSA:
            return {"bass_heavy": False, "bright": False, "balanced": True}

        S = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)

        # Bass (20-250 Hz)
        bass_mask = (freqs >= 20) & (freqs <= 250)
        bass_energy = np.mean(S[bass_mask, :]) if np.any(bass_mask) else 0

        # Mid (250-4000 Hz)
        mid_mask = (freqs >= 250) & (freqs <= 4000)
        mid_energy = np.mean(S[mid_mask, :]) if np.any(mid_mask) else 0

        # High (4000-16000 Hz)
        high_mask = (freqs >= 4000) & (freqs <= 16000)
        high_energy = np.mean(S[high_mask, :]) if np.any(high_mask) else 0

        total = bass_energy + mid_energy + high_energy + 1e-9
        bass_ratio = bass_energy / total
        high_ratio = high_energy / total

        return {
            "bass_ratio": round(bass_ratio, 3),
            "mid_ratio": round(mid_energy / total, 3),
            "high_ratio": round(high_ratio, 3),
            "bass_heavy": bass_ratio > 0.5,
            "bright": high_ratio > 0.4,
            "balanced": 0.2 < bass_ratio < 0.4 and 0.2 < high_ratio < 0.4,
        }

    def _measure_phase(self, y: np.ndarray) -> Dict[str, Any]:
        """Measure stereo phase correlation."""
        if y.ndim < 2 or y.shape[1] < 2:
            return {"correlation": 1.0, "mono_safe": True}

        left = y[:, 0]
        right = y[:, 1]

        correlation = np.corrcoef(left, right)[0, 1]
        mono_safe = abs(correlation) > 0.3

        return {
            "correlation": round(float(correlation), 3),
            "mono_safe": mono_safe,
        }

    def _detect_silence(self, y: np.ndarray) -> Dict[str, Any]:
        """Detect silence at intro/outro."""
        threshold = 0.01
        sr = 22050

        # Intro silence
        intro_samples = 0
        for i in range(len(y)):
            if abs(y[i]) > threshold:
                break
            intro_samples += 1

        # Outro silence
        outro_samples = 0
        for i in range(len(y) - 1, -1, -1):
            if abs(y[i]) > threshold:
                break
            outro_samples += 1

        return {
            "intro_seconds": round(intro_samples / sr, 1),
            "outro_seconds": round(outro_samples / sr, 1),
        }

    def _spectral_analysis(self, y: np.ndarray, sr: int) -> Dict[str, Any]:
        """Basic spectral analysis."""
        if not HAS_LIBROSA:
            return {}

        S = np.abs(librosa.stft(y))
        centroid = np.mean(librosa.feature.spectral_centroid(S=S, sr=sr))
        rolloff = np.mean(librosa.feature.spectral_rolloff(S=S, sr=sr))
        flatness = np.mean(librosa.feature.spectral_flatness(S=S))

        return {
            "centroid_hz": round(float(centroid), 0),
            "rolloff_hz": round(float(rolloff), 0),
            "flatness": round(float(flatness), 4),
        }

    def _calculate_score(self, issues, dynamic, loudness, freq_balance) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100

        # Penalty for issues
        for issue in issues:
            if "clipping" in issue.lower():
                score -= 25
            elif "dynamic range" in issue.lower():
                score -= 15
            elif "loud" in issue.lower():
                score -= 15
            elif "quiet" in issue.lower():
                score -= 10
            elif "bass" in issue.lower():
                score -= 5
            elif "bright" in issue.lower():
                score -= 5
            elif "phase" in issue.lower():
                score -= 10
            elif "silence" in issue.lower():
                score -= 5

        return max(0, min(100, score))

    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade."""
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
