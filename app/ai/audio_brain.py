import math
import random

from app.ai.music_genome import MusicGenome


class AudioBrain:

    def __init__(self):

        # =====================================================
        # GENOME AI
        # =====================================================
        self.genome = MusicGenome()

        # =====================================================
        # LEARNING MEMORY
        # =====================================================
        self.learned_transitions = {}

    # =====================================================
    # MAIN ANALYSIS
    # =====================================================

    def analyze(self, track: dict) -> dict:

        bpm = track.get("bpm", 0)

        energy = track.get("energy", 0.5)

        genre = (
            track.get("genre") or ""
        ).lower()

        name = (
            track.get("name") or ""
        ).lower()

        # =====================================================
        # CORE ANALYSIS
        # =====================================================

        mood = self.detect_mood(
            bpm,
            energy
        )

        genre_cluster = self.detect_genre_cluster(
            bpm,
            genre,
            name
        )

        energy_profile = self.energy_profile(
            bpm,
            energy
        )

        # =====================================================
        # MUSIC GENOME
        # =====================================================

        genome = self.genome.analyze(track)

        # =====================================================
        # DJ SCORE
        # =====================================================

        dj_score = self.calculate_dj_score(
            bpm,
            energy,
            mood,
            genre_cluster,
            genome
        )

        # =====================================================
        # FINAL TRACK
        # =====================================================

        analyzed = {

            **track,

            "mood": mood,

            "genre_cluster": genre_cluster,

            "energy_profile": energy_profile,

            "genome": genome,

            "dj_score": round(dj_score, 3)
        }

        return analyzed

    # =====================================================
    # MOOD ENGINE
    # =====================================================

    def detect_mood(
        self,
        bpm,
        energy
    ):

        if energy < 0.35:
            return "warmup"

        elif energy < 0.6:
            return "groove"

        elif energy < 0.8:
            return "drive"

        return "peak"

    # =====================================================
    # GENRE CLUSTER AI
    # =====================================================

    def detect_genre_cluster(
        self,
        bpm,
        genre,
        name
    ):

        text = genre + " " + name

        # -------------------------------------------------
        # HOUSE
        # -------------------------------------------------

        if "afro" in text:
            return "afro_house"

        if "deep" in text:
            return "deep_house"

        if "organic" in text:
            return "organic_house"

        if "melodic" in text:
            return "melodic_house"

        if "minimal" in text:
            return "minimal_house"

        # -------------------------------------------------
        # TECHNO
        # -------------------------------------------------

        if "techno" in text:
            return "techno"

        if "hard techno" in text:
            return "hard_techno"

        if "industrial" in text:
            return "industrial_techno"

        if "acid" in text:
            return "acid_techno"

        # -------------------------------------------------
        # BPM DETECTION
        # -------------------------------------------------

        if bpm >= 128:
            return "tech_house"

        if bpm <= 118:
            return "chill_house"

        return "unknown"

    # =====================================================
    # ENERGY PROFILE
    # =====================================================

    def energy_profile(
        self,
        bpm,
        energy
    ):

        return {

            "intensity":
                energy,

            "bpm_zone":
                self.bpm_zone(bpm),

            "club_readiness":
                self.club_score(
                    bpm,
                    energy
                )
        }

    # =====================================================
    # BPM ZONE
    # =====================================================

    def bpm_zone(self, bpm):

        if bpm < 115:
            return "slow"

        elif bpm < 123:
            return "mid"

        elif bpm < 128:
            return "club"

        return "peak"

    # =====================================================
    # CLUB SCORE
    # =====================================================

    def club_score(
        self,
        bpm,
        energy
    ):

        score = 0

        if 120 <= bpm <= 128:
            score += 0.6

        else:
            score += 0.3

        score += energy * 0.4

        return min(score, 1.0)

    # =====================================================
    # DJ SCORE
    # =====================================================

    def calculate_dj_score(
        self,
        bpm,
        energy,
        mood,
        genre_cluster,
        genome
    ):

        score = 0

        # -------------------------------------------------
        # BPM
        # -------------------------------------------------

        if 120 <= bpm <= 128:
            score += 0.2

        # -------------------------------------------------
        # ENERGY
        # -------------------------------------------------

        score += energy * 0.2

        # -------------------------------------------------
        # MOOD
        # -------------------------------------------------

        if mood == "peak":
            score += 0.15

        elif mood == "groove":
            score += 0.1

        # -------------------------------------------------
        # GENRE
        # -------------------------------------------------

        if genre_cluster != "unknown":
            score += 0.15

        # -------------------------------------------------
        # GENOME AI
        # -------------------------------------------------

        score += genome.get(
            "dancefloor_score",
            0
        ) * 0.1

        score += genome.get(
            "transition_stability",
            0
        ) * 0.1

        score += genome.get(
            "festival_score",
            0
        ) * 0.05

        score += genome.get(
            "club_destroyer",
            0
        ) * 0.05

        return round(min(score, 1.0), 3)

    # =====================================================
    # AI TRANSITION SCORE
    # =====================================================

    def transition_score(
        self,
        current,
        candidate
    ):

        current_genome = current.get(
            "genome",
            {}
        )

        next_genome = candidate.get(
            "genome",
            {}
        )

        score = 0

        # -------------------------------------------------
        # ENERGY FLOW
        # -------------------------------------------------

        energy_diff = abs(
            current.get("energy", 0)
            -
            candidate.get("energy", 0)
        )

        score += max(
            0,
            1 - energy_diff
        ) * 0.3

        # -------------------------------------------------
        # BPM FLOW
        # -------------------------------------------------

        bpm_diff = abs(
            current.get("bpm", 0)
            -
            candidate.get("bpm", 0)
        )

        score += max(
            0,
            1 - (bpm_diff / 10)
        ) * 0.2

        # -------------------------------------------------
        # GENOME MATCH
        # -------------------------------------------------

        genome_keys = [

            "groove_level",

            "dancefloor_score",

            "hypnotic_score",

            "tribal_score",

            "transition_stability",

            "festival_score"
        ]

        matches = []

        for key in genome_keys:

            a = current_genome.get(key, 0)

            b = next_genome.get(key, 0)

            diff = abs(a - b)

            matches.append(
                max(0, 1 - diff)
            )

        if matches:
            score += (
                sum(matches)
                /
                len(matches)
            ) * 0.5

        return round(min(score, 1.0), 3)

    # =====================================================
    # LEARNING SYSTEM
    # =====================================================

    def learn_transition(
        self,
        track_a,
        track_b,
        score
    ):

        key = (
            track_a.get("id"),
            track_b.get("id")
        )

        self.learned_transitions[key] = score

    # =====================================================
    # PREDICT TRANSITION
    # =====================================================

    def predict_transition(
        self,
        track_a,
        track_b
    ):

        key = (
            track_a.get("id"),
            track_b.get("id")
        )

        if key in self.learned_transitions:

            return self.learned_transitions[key]

        return self.transition_score(
            track_a,
            track_b
        )
