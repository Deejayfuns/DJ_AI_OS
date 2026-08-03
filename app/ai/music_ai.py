import os

from app.ai.club_intelligence import ClubIntelligence
from app.ai.genre_knowledge_base import GenreKnowledgeBase
from app.ai.mfcc_classifier import MFCCClassifier


class MusicAI:

    def __init__(self):

        self.genres = GenreKnowledgeBase()
        self.club = ClubIntelligence()
        self.ml_classifier = MFCCClassifier()
        self.ml_classifier.load()  # Try loading pre-trained model

    def clean_tracks(self, raw):

        clean = []

        for t in raw:

            if not t:
                continue

            path = t.get("id")

            if not path or not os.path.exists(path):
                continue

            cleaned = dict(t)
            cleaned.setdefault("path", path)
            cleaned.setdefault("name", os.path.basename(path))
            cleaned.setdefault("artist", "UNKNOWN")
            cleaned.setdefault("genre", "UNKNOWN")
            cleaned.setdefault("mood", "neutral")
            cleaned.setdefault("bpm", 0)
            cleaned.setdefault("key", cleaned.get("camelot", ""))
            cleaned.setdefault("camelot", cleaned.get("key", ""))
            cleaned.setdefault("energy", 0.5)
            cleaned.setdefault("brightness", 0.5)
            cleaned.setdefault("quality", "UNRATED")
            cleaned.setdefault("role", self.role_from_energy(cleaned["energy"]))
            cleaned.setdefault("confidence", 0.0)

            clean.append(cleaned)

        return clean

    # =========================================
    # BASIC AUDIO INTELLIGENCE (REALISTIC SAFE)
    # =========================================
    def analyze(self, path, base_track=None):

        base_track = base_track or {}

        name = os.path.basename(path).lower()

        # deterministic AI (fake ML but stable)
        bpm = float(base_track.get("bpm", 0) or 0)

        if bpm <= 0 and "90" in name:
            bpm = 90
        elif bpm <= 0 and "100" in name:
            bpm = 100
        elif bpm <= 0 and "128" in name:
            bpm = 128
        elif bpm <= 0:
            bpm = 120

        tempo = self.club.normalize_track_tempo({
            **base_track,
            "name": base_track.get("name", os.path.basename(path)),
            "path": path,
            "bpm": bpm,
        })
        bpm = tempo["bpm"]

        genre_result = self.genres.classify({
            **base_track,
            "name": base_track.get("name", os.path.basename(path)),
            "path": path,
            "bpm": bpm,
        })

        genre = genre_result["genre"]

        # Try ML classifier for higher confidence
        audio_features = base_track.get("_audio_features")
        if audio_features and self.ml_classifier.is_available():
            ml_result = self.ml_classifier.predict(audio_features)
            if ml_result and ml_result.get("confidence", 0) > 0.6:
                genre = ml_result["genre"]
                genre_result["confidence"] = ml_result["confidence"]
                genre_result["classification_source"] = "MFCC_ML"

        mood = "neutral"

        if "sad" in name:
            mood = "sad"
        elif "happy" in name:
            mood = "happy"

        energy = float(base_track.get("energy", 0) or 0)

        if energy <= 0:
            energy = min(1.0, bpm / 140)

        role = self.role_from_context(
            genre_result,
            energy,
            bpm,
            name
        )
        quality = self.quality_from_track(
            bpm,
            energy,
            base_track.get("duration", 0),
            genre_result
        )
        confidence = max(
            self.confidence_from_track(genre, base_track, name),
            genre_result["confidence"]
        )

        return {
            "bpm": bpm,
            "genre": genre,
            "parent_genre": genre_result["parent_genre"],
            "subgenre": genre_result["subgenre"],
            "discovery_status": genre_result["discovery_status"],
            "matched_signals": genre_result["matched_signals"],
            "mood": mood,
            "energy": energy,
            "brightness": base_track.get("brightness", 0.5),
            "key": base_track.get("key", base_track.get("camelot", "")),
            "camelot": base_track.get("camelot", base_track.get("key", "")),
            "quality": quality,
            "role": role,
            "confidence": confidence,
            "assistant_message": self.build_assistant_message(
                genre_result,
                role,
                quality,
                confidence,
                bpm,
                energy
            ),
            "bpm_original": tempo["bpm_original"],
            "bpm_correction": tempo["bpm_correction"],
            "tempo_confidence": tempo["tempo_confidence"],
            "tempo_warning": tempo["tempo_warning"],
        }

    def role_from_context(self, genre_result, energy, bpm, name=""):

        if genre_result.get("parent_genre") == "WEDDING & EVENT":
            subgenre = genre_result.get("subgenre", "")

            if subgenre in ("ILK DANS", "GELIN CIKIS"):
                return "CEREMONY_MOMENT"

            if subgenre in ("KINA GECESI",):
                return "KINA_RITUAL"

            if subgenre in (
                "HALAY",
                "OYUN HAVASI",
                "CIFTETELLI",
                "ROMAN HAVASI",
                "ANKARA HAVASI",
                "HORON"
            ):
                return "DANCE_FLOOR_STARTER"

            if subgenre in ("ARABESK", "TURKCE POP"):
                return "REQUEST_FRIENDLY"

            return "EVENT_SUPPORT"

        confidence = float(genre_result.get("confidence", 0) or 0)

        if genre_result.get("discovery_status") == "DISCOVERED":
            if energy >= 0.78 and bpm >= 124 and confidence >= 0.45:
                return "GROOVE"

            if energy >= 0.55:
                return "WARMUP"

            return "OPENING"

        return self.role_from_energy(energy, bpm, confidence)

    def role_from_energy(self, energy, bpm=0, confidence=1.0):

        energy = float(energy or 0)
        bpm = float(bpm or 0)
        confidence = float(confidence or 0)

        if energy >= 0.84 and bpm >= 124 and confidence >= 0.55:
            return "PEAK TIME"

        if energy >= 0.62:
            return "GROOVE"

        if energy >= 0.38:
            return "WARMUP"

        return "OPENING"

    def quality_from_track(self, bpm, energy, duration, genre_result=None):

        if duration and duration < 90:
            return "SHORT_TRACK"

        if (
            genre_result and
            genre_result.get("parent_genre") == "WEDDING & EVENT"
        ):
            if energy >= 0.65:
                return "EVENT_DANCEFLOOR_TRACK"

            return "EVENT_UTILITY_TRACK"

        confidence = 1.0

        if genre_result:
            confidence = float(genre_result.get("confidence", 0) or 0)

        if bpm >= 124 and energy >= 0.82 and confidence >= 0.55:
            return "PEAK_TIME_TRACK"
        if energy >= 0.65:
            return "STRONG_TRACK"
        if energy <= 0.35:
            return "WARMUP_TRACK"

        return "UTILITY_TRACK"

    def confidence_from_track(self, genre, track, name):

        confidence = 0.35

        if genre and genre.lower() not in ("unknown", "none"):
            confidence += 0.35
        if track.get("bpm"):
            confidence += 0.15
        if any(word in name for word in ("house", "techno", "afro", "deep")):
            confidence += 0.15

        return min(1.0, confidence)

    def build_assistant_message(
        self,
        genre_result,
        role,
        quality,
        confidence,
        bpm,
        energy
    ):

        genre = genre_result["genre"]

        if genre_result["discovery_status"] == "DISCOVERED":
            return (
                f"Yeni veya belirsiz bir stil yakaladim: {genre}. "
                "Bunu kesif listesine aldım; birkaç örnek daha görünce "
                "senden tür adını onaylamanı isteyebilirim."
            )

        if confidence < 0.5:
            return (
                f"{genre} olabilir ama emin değilim. "
                f"BPM {round(bpm, 1)}, enerji {round(energy, 2)}. "
                "Canlı set için kullanmadan önce kontrol öneririm."
            )

        return (
            f"{genre} olarak sınıflandırdım. "
            f"DJ rolü: {role}, kalite etiketi: {quality}."
        )
