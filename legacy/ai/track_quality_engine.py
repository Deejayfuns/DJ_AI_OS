class TrackQualityEngine:

    def analyze(self, track):

        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0)
        genre = track.get("genre", "").upper()

        tags = []

        score = 0.5

        # ---------------------------------
        # BPM ANALYSIS
        # ---------------------------------

        if 120 <= bpm <= 128:
            score += 0.15
            tags.append("CLUB_RANGE")

        if bpm >= 126:
            tags.append("PEAK_TIME")

        if bpm <= 115:
            tags.append("WARMUP")

        # ---------------------------------
        # ENERGY ANALYSIS
        # ---------------------------------

        if energy >= 0.8:
            score += 0.2
            tags.append("HIGH_ENERGY")

        elif energy <= 0.4:
            tags.append("LOW_ENERGY")

        # ---------------------------------
        # GENRE ANALYSIS
        # ---------------------------------

        if "TECHNO" in genre:
            score += 0.1

        if "HOUSE" in genre:
            score += 0.1

        if "POP" in genre:
            score -= 0.05

        # ---------------------------------
        # FINAL CLASSIFICATION
        # ---------------------------------

        if score >= 0.85:
            quality = "PEAK_WEAPON"

        elif score >= 0.7:
            quality = "STRONG_TRACK"

        elif score >= 0.55:
            quality = "UTILITY_TRACK"

        else:
            quality = "FILLER"

        return {
            "score": round(min(score, 1.0), 2),
            "quality": quality,
            "tags": tags
        }
