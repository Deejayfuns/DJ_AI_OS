import librosa
import numpy as np


class AudioEngine:

    def analyze(self, path):

        try:

            # LOAD AUDIO
            y, sr = librosa.load(
                path,
                mono=True,
                duration=120
            )

            # BPM
            tempo, _ = librosa.beat.beat_track(
                y=y,
                sr=sr
            )

            bpm = int(tempo)

            # RMS ENERGY
            rms = librosa.feature.rms(y=y)[0]
            energy = float(np.mean(rms))

            # SPECTRAL CENTROID
            centroid = librosa.feature.spectral_centroid(
                y=y,
                sr=sr
            )[0]

            brightness = float(np.mean(centroid))

            # ZERO CROSSING
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            rhythm_density = float(np.mean(zcr))

            return {

                "bpm": bpm,

                "energy_raw": energy,

                "brightness": brightness,

                "rhythm_density": rhythm_density,

                "success": True
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }
