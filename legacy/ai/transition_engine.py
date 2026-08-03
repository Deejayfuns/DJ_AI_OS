class TransitionEngine:

    def __init__(self, harmonic_engine):

        self.harmonic = harmonic_engine

    def best_next(self, current, candidates):

        best = None
        best_score = -1

        for c in candidates:

            score = self.transition_score(current, c)

            if score > best_score:

                best_score = score
                best = c

        return best

    def transition_score(self, a, b):

        score = 0

        # ---------------------
        # BPM FLOW
        # ---------------------

        bpm_a = a.get("bpm", 120)
        bpm_b = b.get("bpm", 120)

        bpm_diff = abs(bpm_a - bpm_b)

        if bpm_diff <= 2:
            score += 40
        elif bpm_diff <= 5:
            score += 25
        elif bpm_diff <= 8:
            score += 10

        # ---------------------
        # ENERGY FLOW
        # ---------------------

        energy_diff = b.get("energy", 0.5) - a.get("energy", 0.5)

        # DJ mantığı: hafif artış iyi, çok düşüş kötü
        if 0 <= energy_diff <= 0.2:
            score += 30
        elif -0.2 <= energy_diff < 0:
            score += 15
        else:
            score -= 20

        # ---------------------
        # KEY MATCH (Camelot)
        # ---------------------

        key_a = a.get("camelot")
        key_b = b.get("camelot")

        if key_a and key_b:

            allowed = self.harmonic.camelot_map.get(key_a, [])

            if key_b == key_a:
                score += 30
            elif key_b in allowed:
                score += 20

        return score
