from app.ai.keyword_engine import KeywordEngine
from app.ai.bpm_engine import BPMEngine
from app.ai.memory_engine import MemoryEngine
from app.ai.audio_engine import AudioEngine
from app.ai.dj_memory import DJMemory

class AIClassifier:

    def __init__(self):

        self.keyword_engine = KeywordEngine()
        self.bpm_engine = BPMEngine()
        self.memory = MemoryEngine()
        self.audio_engine = AudioEngine()
        self.dj_memory = DJMemory()

    def predict(self, features, filename):
        # ---------------------------
        # AUDIO ANALYSIS
        # ---------------------------

        audio = self.audio_engine.analyze(
            features.get("path", filename)
        )

        # ---------------------------
        # KEYWORD ANALYSIS
        # ---------------------------

        keyword_result = self.keyword_engine.detect(
            filename
        )

        genre = keyword_result["genre"]

        # ---------------------------
        # BPM ANALYSIS
        # ---------------------------

        bpm = audio.get("bpm") or features.get("bpm")

        bpm_role, bpm_energy = self.bpm_engine.detect_role(
            bpm
        )

        # ---------------------------
        # ENERGY LOGIC UPDATE
        # ---------------------------

        audio_energy = audio.get(
            "energy_raw",
            0.5
        )

        brightness = audio.get(
            "brightness",
            1000
        )

        rhythm_density = audio.get(
            "rhythm_density",
            0.05
        )

        # NORMALIZE ENERGY
        energy = min(audio_energy * 10, 1.0)

        # ROLE DETECTION
        if brightness > 3500 and rhythm_density > 0.08:

            role = "PEAK TIME"

        elif brightness > 2200:

            role = "GROOVE"

        elif brightness > 1500:

            role = "WARMUP"

        else:

            role = "OPENING"

        # ---------------------------
        # MEMORY BOOST
        # ---------------------------

        memory_boost = self.memory.genre_weight(
            genre
        )

        # ---------------------------
        # CONFIDENCE
        # ---------------------------

        confidence = min(
            keyword_result["confidence"] +
            memory_boost,
            1.0
        )

        # ---------------------------
        # LEARN
        # ---------------------------

        self.memory.learn(genre)

        # ---------------------------
        # HIT SCORE
        # ---------------------------

        hit_score = (
            energy * 0.4 +
            confidence * 0.3 +
            bpm_energy * 0.2 +
            memory_boost * 0.1
        )

        return {

            "genre": genre,

            "role": role,

            "energy": round(energy, 2),

            "confidence": round(confidence, 2),

            "hit_score": round(hit_score, 2),

            "bpm": bpm,

            "brightness": round(brightness, 2),

            "rhythm_density": round(
                rhythm_density,
                3
            )
        }
