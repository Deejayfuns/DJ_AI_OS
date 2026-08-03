import librosa
import numpy as np


class KeyEngine:

    NOTE_NAMES = [
        "C", "C#", "D", "D#", "E", "F",
        "F#", "G", "G#", "A", "A#", "B"
    ]

    CAMELOT_MAJOR = [
        "8B","3B","10B","5B","12B","7B",
        "2B","9B","4B","11B","6B","1B"
    ]

    CAMELOT_MINOR = [
        "5A","12A","7A","2A","9A","4A",
        "11A","6A","1A","8A","3A","10A"
    ]

    def analyze(self, file_path):

        try:
            y, sr = librosa.load(file_path, duration=30)

            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)

            note_index = int(np.argmax(chroma_mean))
            note = self.NOTE_NAMES[note_index]

            # basit maj/min ayrımı
            mode = "A" if chroma_mean.min() > 0.3 else "B"

            if mode == "A":
                camelot = self.CAMELOT_MINOR[note_index]
            else:
                camelot = self.CAMELOT_MAJOR[note_index]

            return {
                "key": note,
                "camelot": camelot
            }

        except:
            return {
                "key": "UNKNOWN",
                "camelot": "0A"
            }
