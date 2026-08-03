class HarmonicEngine:

    def __init__(self):

        # ---------------------------------
        # CAMELOT COMPATIBILITY
        # ---------------------------------

        self.camelot_map = {

            "1A": ["1A", "12A", "2A"],
            "2A": ["2A", "1A", "3A"],
            "3A": ["3A", "2A", "4A"],
            "4A": ["4A", "3A", "5A"],
            "5A": ["5A", "4A", "6A"],
            "6A": ["6A", "5A", "7A"],
            "7A": ["7A", "6A", "8A"],
            "8A": ["8A", "7A", "9A"],
            "9A": ["9A", "8A", "10A"],
            "10A": ["10A", "9A", "11A"],
            "11A": ["11A", "10A", "12A"],
            "12A": ["12A", "11A", "1A"],

            "1B": ["1B", "12B", "2B"],
            "2B": ["2B", "1B", "3B"],
            "3B": ["3B", "2B", "4B"],
            "4B": ["4B", "3B", "5B"],
            "5B": ["5B", "4B", "6B"],
            "6B": ["6B", "5B", "7B"],
            "7B": ["7B", "6B", "8B"],
            "8B": ["8B", "7B", "9B"],
            "9B": ["9B", "8B", "10B"],
            "10B": ["10B", "9B", "11B"],
            "11B": ["11B", "10B", "12B"],
            "12B": ["12B", "11B", "1B"],
        }

    # ---------------------------------
    # MAIN MATCH ENGINE
    # ---------------------------------

    def match_score(self, a, b):

        score = 0

        # ---------------------------------
        # BPM MATCH
        # ---------------------------------

        bpm_a = a.get("bpm", 120)
        bpm_b = b.get("bpm", 120)

        bpm_diff = abs(bpm_a - bpm_b)

        if bpm_diff <= 1:
            score += 40

        elif bpm_diff <= 3:
            score += 30

        elif bpm_diff <= 6:
            score += 15

        else:
            score -= 10

        # ---------------------------------
        # ENERGY FLOW
        # ---------------------------------

        energy_a = a.get("energy", 0.5)
        energy_b = b.get("energy", 0.5)

        energy_diff = abs(energy_a - energy_b)

        score += max(0, 35 - (energy_diff * 70))

        # smooth build-up bonus
        if energy_b >= energy_a:
            score += 10

        # ---------------------------------
        # HARMONIC MATCH
        # ---------------------------------

        key_a = a.get("camelot", "")
        key_b = b.get("camelot", "")

        if key_a and key_b:

            allowed = self.camelot_map.get(key_a, [])

            if key_b in allowed:
                score += 25

            else:
                score -= 10

        # ---------------------------------
        # GENRE MATCH
        # ---------------------------------

        genre_a = str(a.get("genre", "")).lower()
        genre_b = str(b.get("genre", "")).lower()

        if genre_a and genre_b:

            if genre_a == genre_b:
                score += 20

            elif genre_a in genre_b or genre_b in genre_a:
                score += 10

        # ---------------------------------
        # QUALITY LABEL
        # ---------------------------------

        quality = self.get_quality(score)

        # ---------------------------------
        # CONFIDENCE
        # ---------------------------------

        confidence = min(100, max(0, int(score)))

        return {
            "score": score,
            "quality": quality,
            "confidence": confidence
        }

    # ---------------------------------
    # QUALITY CLASSIFIER
    # ---------------------------------

    def get_quality(self, score):

        if score >= 90:
            return "PERFECT_TRANSITION"

        elif score >= 75:
            return "STRONG_TRANSITION"

        elif score >= 55:
            return "GOOD_TRANSITION"

        elif score >= 35:
            return "RISKY_TRANSITION"

        return "BAD_TRANSITION"
