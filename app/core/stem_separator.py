"""
DJ AI OS — Audio Stem Separation

Isolate vocals, drums, bass, other from any audio track.
Primary: demucs (state-of-the-art neural separation)
Fallback: spectral band filtering (no external deps)

Usage:
    sep = StemSeparator()
    stems = sep.separate("track.mp3")
    sep.export_stems(stems, "output/")
"""

import os
import wave
import subprocess
import tempfile
import numpy as np
from pathlib import Path

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except Exception:
    HAS_SOUNDFILE = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except Exception:
    HAS_SOUNDDEVICE = False


class StemSeparator:
    """
    Audio stem separator with demucs primary and spectral fallback.
    """

    def __init__(self, method="auto", cache_dir=None):
        """
        method: 'demucs', 'spectral', or 'auto' (try demucs first)
        cache_dir: where to cache separated stems
        """
        self.method = method
        self.cache_dir = cache_dir or os.path.join("data", "stem_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._demucs_available = None

    def is_demucs_available(self):
        """Check if demucs is installed."""
        if self._demucs_available is not None:
            return self._demucs_available

        try:
            result = subprocess.run(
                ["python", "-m", "demucs", "--help"],
                capture_output=True, timeout=10
            )
            self._demucs_available = result.returncode == 0
        except Exception:
            self._demucs_available = False

        return self._demucs_available

    def separate(self, audio_path, stems=None):
        """
        Separate an audio file into stems.

        stems: list of stem names to extract (default: all 4)
               Options: 'vocals', 'drums', 'bass', 'other'

        Returns: dict of {stem_name: np.array (mono, float32)}
        """
        audio_path = str(audio_path)
        if not os.path.exists(audio_path):
            return {"error": f"File not found: {audio_path}"}

        # Check cache
        cache_key = self._cache_key(audio_path)
        cached = self._load_cache(cache_key)
        if cached:
            return cached

        # Choose method
        use_demucs = (
            self.method in ("demucs", "auto") and
            self.is_demucs_available()
        )

        if use_demucs:
            result = self._separate_demucs(audio_path, stems)
        else:
            result = self._separate_spectral(audio_path, stems)

        # Cache result
        if "error" not in result:
            self._save_cache(cache_key, result)

        return result

    def _separate_demucs(self, audio_path, stems=None):
        """Use demucs for high-quality neural separation."""
        try:
            import demucs.api
            separator = demucs.api.Separator(model="htdemucs")
            origin, separated = separator.separate_audio_file(audio_path)

            result = {}
            target_stems = stems or ["vocals", "drums", "bass", "other"]
            for stem_name in target_stems:
                if stem_name in separated:
                    # Convert to mono float32
                    audio = separated[stem_name].cpu().numpy()
                    if audio.ndim > 1:
                        audio = audio.mean(axis=0)
                    result[stem_name] = audio.astype(np.float32)

            result["engine"] = "demucs"
            result["sample_rate"] = 44100
            return result

        except ImportError:
            # Try demucs CLI fallback
            return self._separate_demucs_cli(audio_path, stems)
        except Exception as e:
            return {"error": f"Demucs error: {e}"}

    def _separate_demucs_cli(self, audio_path, stems=None):
        """Use demucs CLI as fallback."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = [
                    "python", "-m", "demucs",
                    "--out", tmpdir,
                    audio_path
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=300)

                if result.returncode != 0:
                    return {"error": f"Demucs CLI failed: {result.stderr.decode()[:200]}"}

                # Find output files
                output_dir = Path(tmpdir) / "htdemucs" / Path(audio_path).stem
                result_stems = {}

                target_stems = stems or ["vocals", "drums", "bass", "other"]
                for stem_name in target_stems:
                    stem_path = output_dir / f"{stem_name}.wav"
                    if stem_path.exists():
                        audio, sr = sf.read(str(stem_path))
                        if audio.ndim > 1:
                            audio = audio.mean(axis=1)
                        result_stems[stem_name] = audio.astype(np.float32)

                result_stems["engine"] = "demucs_cli"
                result_stems["sample_rate"] = 44100
                return result_stems

        except Exception as e:
            return {"error": f"Demucs CLI error: {e}"}

    def _separate_spectral(self, audio_path, stems=None):
        """Spectral band filtering — no external dependencies."""
        try:
            # Load audio
            if HAS_SOUNDFILE:
                audio, sr = sf.read(audio_path)
            else:
                audio = self._load_audio_fallback(audio_path)
                sr = 44100

            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            audio = audio.astype(np.float32)

            # Simple frequency band separation
            # This is a basic approach — for production, use demucs
            n = len(audio)

            # Apply FFT
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(n, d=1.0/sr)

            # Define frequency bands (Hz)
            bands = {
                "bass": (20, 250),
                "other": (250, 2000),
                "drums": (2000, 8000),
                "vocals": (200, 8000),  # vocal range
            }

            result = {}
            target_stems = stems or ["vocals", "drums", "bass", "other"]

            for stem_name in target_stems:
                low, high = bands.get(stem_name, (20, 8000))

                # Create frequency mask
                mask = np.zeros_like(freqs)
                mask[(freqs >= low) & (freqs <= high)] = 1.0

                # Apply mask and inverse FFT
                stem_fft = fft * mask
                stem_audio = np.fft.irfft(stem_fft, n=n)

                result[stem_name] = stem_audio.astype(np.float32)

            result["engine"] = "spectral"
            result["sample_rate"] = sr
            return result

        except Exception as e:
            return {"error": f"Spectral separation error: {e}"}

    def _load_audio_fallback(self, path):
        """Load audio without soundfile using wave module."""
        with wave.open(path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sample_width = wf.getsampwidth()
            channels = wf.getnchannels()

            if sample_width == 2:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 4:
                audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
            else:
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            if channels > 1:
                audio = audio.reshape(-1, channels).mean(axis=1)

            return audio

    def export_stems(self, stems, output_dir, format="wav"):
        """Export separated stems as audio files."""
        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        sr = stems.get("sample_rate", 44100)

        for name, audio in stems.items():
            if name in ("engine", "sample_rate", "error"):
                continue

            path = os.path.join(output_dir, f"{name}.{format}")

            if HAS_SOUNDFILE:
                sf.write(path, audio, sr)
            else:
                # Fallback: write as 16-bit WAV
                audio_16 = (audio * 32767).astype(np.int16)
                with wave.open(path, "w") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(audio_16.tobytes())

            paths[name] = path

        return paths

    def _cache_key(self, audio_path):
        """Generate cache key from file path + size + mtime."""
        import hashlib
        stat = os.stat(audio_path)
        key = f"{audio_path}_{stat.st_size}_{int(stat.st_mtime)}"
        return hashlib.md5(key.encode()).hexdigest()

    def _load_cache(self, cache_key):
        """Load cached stems if available."""
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.npz")
        if os.path.exists(cache_path):
            try:
                data = np.load(cache_path, allow_pickle=True)
                result = {}
                for key in data.files:
                    if key.startswith("stem_"):
                        stem_name = key[5:]
                        result[stem_name] = data[key]
                    elif key == "metadata":
                        meta = data[key].item()
                        result.update(meta)
                return result
            except Exception:
                pass
        return None

    def _save_cache(self, cache_key, stems):
        """Save stems to cache."""
        try:
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.npz")
            save_dict = {}
            metadata = {}

            for name, audio in stems.items():
                if name in ("engine", "sample_rate", "error"):
                    metadata[name] = audio
                else:
                    save_dict[f"stem_{name}"] = audio

            save_dict["metadata"] = metadata
            np.savez_compressed(cache_path, **save_dict)
        except Exception:
            pass
