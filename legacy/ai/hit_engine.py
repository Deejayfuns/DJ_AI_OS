class HitEngine:

    def score(self, track):

        score = 0.5

        # BPM ideal zone
        if 122 <= track["bpm"] <= 128:
            score += 0.2

        # Energy zone
        score += track["energy"] * 0.2

        # Genre boost
        if "HOUSE" in track["genre"].upper():
            score += 0.1

        # Camelot validity
        if track["camelot"] != "0A":
            score += 0.1

        return round(min(score, 1.0), 2)
