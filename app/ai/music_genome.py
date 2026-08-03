import math
import random


class MusicGenome:

    def __init__(self):

        # future learning db
        self.learned_patterns = {}

    # =====================================================
    # MAIN ANALYSIS
    # =====================================================

    def analyze(self, track):

        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0.5)

        genre = (
            track.get("genre", "") or ""
        ).lower()

        name = (
            track.get("name", "") or ""
        ).lower()

        genome = {

            # ---------------------------------------------
            # CORE DNA
            # ---------------------------------------------
            "groove_level":
                self.groove_level(
                    bpm,
                    energy
                ),

            "dancefloor_score":
                self.dancefloor_score(
                    bpm,
                    energy
                ),

            "peak_time_index":
                self.peak_time_index(
                    bpm,
                    energy
                ),

            "afterhour_score":
                self.afterhour_score(
                    bpm,
                    energy
                ),

            "festival_score":
                self.festival_score(
                    bpm,
                    energy
                ),

            # ---------------------------------------------
            # MOOD DNA
            # ---------------------------------------------
            "darkness":
                self.darkness(
                    genre,
                    name
                ),

            "emotional_intensity":
                self.emotional_intensity(
                    energy
                ),

            "hypnotic_score":
                self.hypnotic_score(
                    bpm,
                    genre
                ),

            "tribal_score":
                self.tribal_score(
                    genre,
                    name
                ),

            # ---------------------------------------------
            # TRANSITION DNA
            # ---------------------------------------------
            "transition_stability":
                self.transition_stability(
                    bpm,
                    energy
                ),

            "warmup_index":
                self.warmup_index(
                    bpm,
                    energy
                ),

            "sunrise_vibe":
                self.sunrise_vibe(
                    genre,
                    energy
                ),

            # ---------------------------------------------
            # ADVANCED
            # ---------------------------------------------
            "club_destroyer":
                self.club_destroyer(
                    bpm,
                    energy,
                    genre
                ),

            "ai_confidence":
                self.ai_confidence(
                    track
                )
        }

        return genome

    # =====================================================
    # GROOVE
    # =====================================================

    def groove_level(self, bpm, energy):

        groove = 0.5

        if 118 <= bpm <= 126:
            groove += 0.3

        groove += energy * 0.2

        return round(min(groove, 1.0), 3)

    # =====================================================
    # DANCEFLOOR
    # =====================================================

    def dancefloor_score(self, bpm, energy):

        score = 0

        if 120 <= bpm <= 128:
            score += 0.5

        score += energy * 0.5

        return round(min(score, 1.0), 3)

    # =====================================================
    # PEAK TIME
    # =====================================================

    def peak_time_index(self, bpm, energy):

        score = 0

        if bpm >= 126:
            score += 0.4

        if energy >= 0.75:
            score += 0.6

        return round(min(score, 1.0), 3)

    # =====================================================
    # AFTERHOUR
    # =====================================================

    def afterhour_score(self, bpm, energy):

        score = 0.2

        if bpm <= 122:
            score += 0.4

        if energy < 0.65:
            score += 0.4

        return round(min(score, 1.0), 3)

    # =====================================================
    # FESTIVAL
    # =====================================================

    def festival_score(self, bpm, energy):

        score = 0

        if bpm >= 128:
            score += 0.5

        if energy >= 0.8:
            score += 0.5

        return round(min(score, 1.0), 3)

    # =====================================================
    # DARKNESS
    # =====================================================

    def darkness(self, genre, name):

        text = genre + " " + name

        dark_words = [
            "dark",
            "acid",
            "industrial",
            "melodic",
            "hard",
            "techno"
        ]

        value = 0.2

        for w in dark_words:

            if w in text:
                value += 0.15

        return round(min(value, 1.0), 3)

    # =====================================================
    # EMOTION
    # =====================================================

    def emotional_intensity(self, energy):

        return round(min(
            0.3 + (energy * 0.7),
            1.0
        ), 3)

    # =====================================================
    # HYPNOTIC
    # =====================================================

    def hypnotic_score(self, bpm, genre):

        score = 0.3

        if "minimal" in genre:
            score += 0.4

        if 120 <= bpm <= 124:
            score += 0.3

        return round(min(score, 1.0), 3)

    # =====================================================
    # TRIBAL
    # =====================================================

    def tribal_score(self, genre, name):

        text = genre + " " + name

        score = 0.1

        tribal_words = [
            "tribal",
            "afro",
            "organic",
            "ethnic",
            "drum"
        ]

        for w in tribal_words:

            if w in text:
                score += 0.2

        return round(min(score, 1.0), 3)

    # =====================================================
    # TRANSITION
    # =====================================================

    def transition_stability(self, bpm, energy):

        score = 0.5

        if 118 <= bpm <= 126:
            score += 0.3

        if 0.4 <= energy <= 0.8:
            score += 0.2

        return round(min(score, 1.0), 3)

    # =====================================================
    # WARMUP
    # =====================================================

    def warmup_index(self, bpm, energy):

        score = 0

        if bpm <= 120:
            score += 0.5

        if energy <= 0.5:
            score += 0.5

        return round(min(score, 1.0), 3)

    # =====================================================
    # SUNRISE
    # =====================================================

    def sunrise_vibe(self, genre, energy):

        score = 0.2

        if "melodic" in genre:
            score += 0.3

        if "deep" in genre:
            score += 0.2

        if energy <= 0.7:
            score += 0.3

        return round(min(score, 1.0), 3)

    # =====================================================
    # CLUB DESTROYER
    # =====================================================

    def club_destroyer(
        self,
        bpm,
        energy,
        genre
    ):

        score = 0

        if bpm >= 128:
            score += 0.4

        if energy >= 0.85:
            score += 0.4

        if "techno" in genre:
            score += 0.2

        return round(min(score, 1.0), 3)

    # =====================================================
    # AI CONFIDENCE
    # =====================================================

    def ai_confidence(self, track):

        confidence = 0.5

        if track.get("bpm"):
            confidence += 0.2

        if track.get("genre"):
            confidence += 0.2

        if track.get("energy") is not None:
            confidence += 0.1

        return round(min(confidence, 1.0), 3)
