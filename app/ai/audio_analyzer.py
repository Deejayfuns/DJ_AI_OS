try:
    import librosa
    import numpy as np
except Exception:
    librosa = None
    np = None


class AudioAnalyzer:

    def __init__(self):

        self.sample_rate = 22050
        self.max_duration = 180

    # =====================================================
    # MAIN ANALYSIS
    # =====================================================
    def analyze(self, path: str):

        try:
            if librosa is None or np is None:
                return self._empty("LIBROSA_NOT_AVAILABLE")

            y, sr = librosa.load(
                path,
                sr=self.sample_rate,
                mono=True,
                duration=self.max_duration
            )

            # -------------------------------
            # BASIC FEATURES
            # -------------------------------
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo = self._to_float(tempo)

            rms = librosa.feature.rms(y=y)[0]
            energy_raw = self._to_float(np.mean(rms))
            energy = self._normalize_energy(energy_raw)

            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            brightness_raw = self._to_float(np.mean(spectral_centroid))
            brightness = self._normalize_brightness(brightness_raw)

            zcr = librosa.feature.zero_crossing_rate(y)[0]
            roughness = self._to_float(np.mean(zcr))

            # -------------------------------
            # HARMONIC FEATURES
            # -------------------------------
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            key_profile = np.mean(chroma, axis=1)

            key_index = int(np.argmax(key_profile))
            key = self._key_from_index(key_index)

            # -------------------------------
            # ADVANCED AI FEATURES
            # -------------------------------
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)

            # danceability proxy
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            danceability_raw = self._to_float(np.mean(onset_env))
            danceability = self._normalize_danceability(danceability_raw)

            # drop strength (energy variance)
            energy_curve = librosa.feature.rms(y=y)[0]
            drop_strength_raw = self._to_float(np.std(energy_curve))
            drop_strength = self._normalize_drop_strength(drop_strength_raw)
            phrase_points = self._build_phrase_points(energy_curve)

            # mood vector (compressed emotional space)
            mood_vector = self._build_mood_vector(
                energy,
                brightness,
                roughness,
                danceability
            )

            # -------------------------------
            # RETURN AI TRACK DNA
            # -------------------------------
            return {

                "analysis_status": "FULL",

                "bpm": round(tempo, 2),

                "energy": float(energy),

                "brightness": float(brightness),

                "roughness": roughness,

                "key": key,
                "camelot": self._camelot_from_key(key),

                "key_index": key_index,

                "danceability": danceability,

                "drop_strength": drop_strength,
                "drop_strength_raw": drop_strength_raw,

                "mfcc": mfcc_mean.tolist(),

                "mood_vector": mood_vector,

                "waveform": self._build_waveform_preview(y)
                ,
                "phrase_points": phrase_points
            }

        except Exception as e:

            print("ANALYSIS ERROR:", e)

            return self._empty(str(e))

    # =====================================================
    # KEY MAP
    # =====================================================
    def _key_from_index(self, i):

        keys = [
            "C", "C#", "D", "D#", "E", "F",
            "F#", "G", "G#", "A", "A#", "B"
        ]

        return keys[i % 12]

    def _to_float(self, value, default=0.0):

        try:
            array = np.asarray(value)

            if array.size == 0:
                return default

            return float(array.reshape(-1)[0])
        except Exception:
            try:
                return float(value)
            except Exception:
                return default

    def _camelot_from_key(self, key):

        # Approximate Camelot mapping. Real key detection can improve later.
        mapping = {
            "C": "8B",
            "C#": "3B",
            "D": "10B",
            "D#": "5B",
            "E": "12B",
            "F": "7B",
            "F#": "2B",
            "G": "9B",
            "G#": "4B",
            "A": "11B",
            "A#": "6B",
            "B": "1B",
        }

        return mapping.get(key, "")

    def _normalize_energy(self, value):

        return max(0.0, min(1.0, value * 12))

    def _normalize_brightness(self, value):

        return max(0.0, min(1.0, value / 5000))

    def _normalize_danceability(self, value):

        return max(0.0, min(1.0, value / 4))

    def _normalize_drop_strength(self, value):

        return max(0.0, min(1.0, value * 20))

    def _build_waveform_preview(self, y, points=512):

        if y is None or len(y) == 0:
            return []

        indexes = np.linspace(0, len(y) - 1, points).astype(int)
        preview = y[indexes]
        peak = float(np.max(np.abs(preview)) or 1)

        return [
            round(float(v / peak), 4)
            for v in preview
        ]

    def _build_phrase_points(self, energy_curve):

        if energy_curve is None or len(energy_curve) == 0 or np is None:
            return []

        values = np.asarray(energy_curve, dtype=float)
        peak = float(np.max(values) or 1)
        normalized = values / peak
        length = len(normalized)

        start_index = self._first_index_above(normalized, 0.08)
        build_index = self._first_index_above(normalized, 0.45)
        peak_index = int(np.argmax(normalized))
        outro_index = self._last_index_above(normalized, 0.18)

        return [
            self._phrase_point("START", start_index, length),
            self._phrase_point("BUILD", build_index, length),
            self._phrase_point("PEAK", peak_index, length),
            self._phrase_point("OUTRO", outro_index, length),
        ]

    def _phrase_point(self, label, index, length):

        index = max(0, min(int(index or 0), max(length - 1, 0)))
        position = 0 if length <= 1 else index / (length - 1)

        return {
            "label": label,
            "position": round(float(position), 3)
        }

    def _first_index_above(self, values, threshold):

        for index, value in enumerate(values):
            if value >= threshold:
                return index

        return 0

    def _last_index_above(self, values, threshold):

        for index in range(len(values) - 1, -1, -1):
            if values[index] >= threshold:
                return index

        return len(values) - 1

    # =====================================================
    # MOOD ENGINE (CORE AI IDEA)
    # =====================================================
    def _build_mood_vector(self, energy, brightness, roughness, danceability):

        return [

            float(energy * 0.4),

            float(brightness * 0.3),

            float(danceability * 0.2),

            float(roughness * 0.1)

        ]

    # =====================================================
    # EMPTY SAFE RETURN
    # =====================================================
    def _empty(self, reason=""):

        return {

            "analysis_status": "FALLBACK",
            "analysis_error": reason,
            "bpm": 0,
            "energy": 0,
            "brightness": 0,
            "roughness": 0,
            "key": "Unknown",
            "camelot": "",
            "key_index": 0,
            "danceability": 0,
            "drop_strength": 0,
            "mfcc": [],
            "mood_vector": [0, 0, 0, 0],
            "waveform": [],
            "phrase_points": []
        }
