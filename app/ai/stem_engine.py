"""
DJ AI OS — Stem Engine

Real-time audio stem separation:
- Primary: demucs (Facebook's state-of-the-art)
- Fallback: spectral band filtering (no deps)
- Live separation mode (for DJ performance)
- Stem mixing with volume/pan controls
"""

import os
import numpy as np
from typing import Dict, List, Any, Optional

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

try:
    import demucs.api
    HAS_DEMUCS = True
except ImportError:
    HAS_DEMUCS = False


class StemEngine:
    """
    Audio stem separation engine.
    Separates vocals, drums, bass, other from any audio track.
    """

    def __init__(self, cache_dir: str = "data/stem_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._separator = None

    def separate(self, audio_path: str, stems: List[str] = None) -> Dict[str, Any]:
        """
        Separate an audio file into stems.

        stems: list of stem names (default: all 4)
               Options: 'vocals', 'drums', 'bass', 'other'

        Returns: dict with stem data + metadata
        """
        stems = stems or ["vocals", "drums", "bass", "other"]

        if not os.path.exists(audio_path):
            return {"error": f"File not found: {audio_path}"}

        # Check cache
        cache_key = self._cache_key(audio_path)
        cached = self._load_cache(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        # Try demucs first
        if HAS_DEMUCS:
            result = self._separate_demucs(audio_path, stems)
        else:
            result = self._separate_spectral(audio_path, stems)

        # Cache result
        if "error" not in result:
            self._save_cache(cache_key, result)

        return result

    def separate_live(self, y: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """
        Live separation from numpy array (for real-time DJ use).
        Uses spectral filtering for speed.
        """
        if y.ndim > 1:
            y = y.mean(axis=1)

        n = len(y)
        fft = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(n, d=1.0/sr)

        bands = {
            "bass": (20, 250),
            "other": (250, 2000),
            "drums": (2000, 8000),
            "vocals": (200, 8000),
        }

        result = {}
        for name, (low, high) in bands.items():
            mask = np.zeros_like(freqs)
            mask[(freqs >= low) & (freqs <= high)] = 1.0
            stem_fft = fft * mask
            stem_audio = np.fft.irfft(stem_fft, n=n)
            result[name] = stem_audio.astype(np.float32)

        result["sr"] = sr
        return result

    def _separate_demucs(self, audio_path: str, stems: List[str]) -> Dict[str, Any]:
        """Use demucs for high-quality separation."""
        try:
            separator = demucs.api.Separator(model="htdemucs")
            origin, separated = separator.separate_audio_file(audio_path)

            result = {}
            for stem_name in stems:
                if stem_name in separated:
                    audio = separated[stem_name].cpu().numpy()
                    if audio.ndim > 1:
                        audio = audio.mean(axis=0)
                    result[stem_name] = audio.astype(np.float32)

            result["engine"] = "demucs"
            result["sr"] = 44100
            return result

        except Exception as e:
            return {"error": f"Demucs failed: {e}"}

    def _separate_spectral(self, audio_path: str, stems: List[str]) -> Dict[str, Any]:
        """Spectral band filtering (no external deps)."""
        try:
            if HAS_SOUNDFILE:
                y, sr = sf.read(audio_path)
                if y.ndim > 1:
                    y = y.mean(axis=1)
                y = y.astype(np.float32)
            else:
                y, sr = self._load_wav(audio_path)

            n = len(y)
            fft = np.fft.rfft(y)
            freqs = np.fft.rfftfreq(n, d=1.0/sr)

            bands = {
                "bass": (20, 250),
                "other": (250, 2000),
                "drums": (2000, 8000),
                "vocals": (200, 8000),
            }

            result = {}
            for stem_name in stems:
                low, high = bands.get(stem_name, (20, 8000))
                mask = np.zeros_like(freqs)
                mask[(freqs >= low) & (freqs <= high)] = 1.0
                stem_fft = fft * mask
                stem_audio = np.fft.irfft(stem_fft, n=n)
                result[stem_name] = stem_audio.astype(np.float32)

            result["engine"] = "spectral"
            result["sr"] = sr
            return result

        except Exception as e:
            return {"error": f"Spectral separation failed: {e}"}

    def _load_wav(self, path: str):
        """Load WAV without soundfile."""
        import wave
        with wave.open(path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sw = wf.getsampwidth()
            ch = wf.getnchannels()
            sr = wf.getframerate()

            if sw == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            if ch > 1:
                audio = audio.reshape(-1, ch).mean(axis=1)

            return audio, sr

    def export_stems(self, stems: Dict, output_dir: str) -> Dict[str, str]:
        """Export separated stems as WAV files."""
        os.makedirs(output_dir, exist_ok=True)
        paths = {}
        sr = stems.get("sr", 44100)

        for name, audio in stems.items():
            if name in ("engine", "sr", "error", "from_cache"):
                continue

            path = os.path.join(output_dir, f"{name}.wav")
            if HAS_SOUNDFILE:
                sf.write(path, audio, sr)
            else:
                audio_16 = (audio * 32767).astype(np.int16)
                import wave
                with wave.open(path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(audio_16.tobytes())

            paths[name] = path

        return paths

    def mix_stems(self, stems: Dict[str, np.ndarray], levels: Dict[str, float] = None) -> np.ndarray:
        """Mix stems together with volume levels."""
        default_levels = {"vocals": 0.8, "drums": 1.0, "bass": 0.9, "other": 0.7}
        levels = levels or default_levels

        max_len = max(len(s) for name, s in stems.items() if isinstance(s, np.ndarray))
        mix = np.zeros(max_len)

        for name, audio in stems.items():
            if not isinstance(audio, np.ndarray):
                continue
            level = levels.get(name, 0.7)
            mix[:len(audio)] += audio * level

        # Normalize
        maxv = np.max(np.abs(mix)) or 1.0
        mix = mix / maxv * 0.95

        return mix

    def get_available_engines(self) -> Dict[str, bool]:
        """Check which separation engines are available."""
        return {
            "demucs": HAS_DEMUCS,
            "spectral": True,  # Always available
        }

    def _cache_key(self, path: str) -> str:
        """Generate cache key."""
        import hashlib
        stat = os.stat(path)
        return hashlib.md5(f"{path}_{stat.st_size}_{int(stat.st_mtime)}".encode()).hexdigest()

    def _load_cache(self, key: str) -> Optional[Dict]:
        """Load from cache."""
        cache_path = os.path.join(self.cache_dir, f"{key}.npz")
        if os.path.exists(cache_path):
            try:
                data = np.load(cache_path, allow_pickle=True)
                result = {}
                for k in data.files:
                    if k.startswith("stem_"):
                        result[k[5:]] = data[k]
                    elif k == "metadata":
                        meta = data[k].item()
                        result.update(meta)
                return result
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, stems: Dict):
        """Save to cache."""
        try:
            cache_path = os.path.join(self.cache_dir, f"{key}.npz")
            save_dict = {}
            metadata = {}
            for name, audio in stems.items():
                if isinstance(audio, np.ndarray):
                    save_dict[f"stem_{name}"] = audio
                else:
                    metadata[name] = audio
            save_dict["metadata"] = metadata
            np.savez_compressed(cache_path, **save_dict)
        except Exception:
            pass
