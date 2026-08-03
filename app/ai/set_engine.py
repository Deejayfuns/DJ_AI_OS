import numpy as np


class SetEngine:

    def __init__(self, brain):

        self.brain = brain

    # =====================================================
    # MAIN ENTRY
    # =====================================================
    def build_set(self, tracks, target_length=20):

        if not tracks:
            return []

        # 1. Analyze all tracks if needed
        enriched = self._ensure_features(tracks)

        # 2. Start from a "seed track"
        current = self._pick_seed(enriched)

        playlist = [current]
        current["set_position"] = 1
        current["mix_strategy"] = "OPENING"
        current["transition_score"] = 100
        current["compatibility_grade"] = "A"
        current["pitch_percent"] = 0
        current["cue_advice"] = "Introdan gir, kalabaligi okumak icin 32 bar bekle."
        current["transition_advice"] = (
            "Baslangic parcasi: orta enerjiyle seti guvenli acar."
        )
        used = set()
        used.add(current["id"])

        # 3. Build AI chain
        while len(playlist) < min(target_length, len(enriched)):

            next_track = self._find_best_next(current, enriched, used)

            if not next_track:
                break

            playlist.append(next_track)
            used.add(next_track["id"])
            current = next_track

        return playlist

    # =====================================================
    # SEED SELECTION
    # =====================================================
    def _pick_seed(self, tracks):

        # medium energy starting point (DJ logic)
        return sorted(
            tracks,
            key=lambda t: abs(t.get("energy", 0.5) - 0.6)
        )[0]

    # =====================================================
    # NEXT TRACK DECISION ENGINE
    # =====================================================
    def _find_best_next(self, current, tracks, used):

        best_score = -1
        best_track = None
        best_detail = None

        for t in tracks:

            if t["id"] in used:
                continue

            detail = self.transition_detail(current, t)
            score = detail["score"]

            if score > best_score:
                best_score = score
                best_track = t
                best_detail = detail

        if best_track and best_detail:
            best_track["set_position"] = len(used) + 1
            best_track["transition_from"] = current.get("id")
            best_track["transition_score"] = round(best_detail["score"] * 100)
            best_track["compatibility_grade"] = best_detail["grade"]
            best_track["pitch_percent"] = best_detail["pitch_percent"]
            best_track["mix_strategy"] = best_detail["strategy"]
            best_track["cue_advice"] = best_detail["cue_advice"]
            best_track["transition_advice"] = best_detail["advice"]

        return best_track

    # =====================================================
    # CORE AI SCORING ENGINE
    # =====================================================
    def _transition_score(self, a, b):

        return self.transition_detail(a, b)["score"]

    def transition_detail(self, a, b):

        # -------------------------
        # BPM compatibility
        # -------------------------
        bpm_a = self._number(a.get("bpm"), 120)
        bpm_b = self._number(b.get("bpm"), 120)
        bpm_diff = abs(bpm_a - bpm_b)
        bpm_score = max(0, 1 - (bpm_diff / 40))

        # -------------------------
        # Energy flow (VERY IMPORTANT)
        # -------------------------
        energy_a = self._number(a.get("energy"), 0.5)
        energy_b = self._number(b.get("energy"), 0.5)
        energy_diff = energy_b - energy_a

        # reward smooth rise or slight drop
        if -0.15 <= energy_diff <= 0.25:
            energy_score = 1.0
        else:
            energy_score = max(0, 1 - abs(energy_diff))

        # -------------------------
        # KEY compatibility (simple harmonic match)
        # -------------------------
        key_a = a.get("camelot") or a.get("key")
        key_b = b.get("camelot") or b.get("key")
        key_score = self._camelot_score(key_a, key_b)

        # -------------------------
        # MOOD continuity
        # -------------------------
        mood_score = self._mood_similarity(
            a.get("mood_vector", []),
            b.get("mood_vector", [])
        )

        # -------------------------
        # DROP CONTROL (DJ FLOW)
        # -------------------------
        drop_diff = abs(
            a.get("drop_strength", 0) - b.get("drop_strength", 0)
        )

        drop_score = max(0, 1 - drop_diff)

        ai_ear_score = self._number(b.get("ai_ear_score"), 0.6)
        vocal_risk = self._number(b.get("vocal_risk"), 0.2)
        mixability = self._number(b.get("intro_outro_mixability"), 0.6)
        ear_score = (
            ai_ear_score * 0.45 +
            mixability * 0.35 +
            (1 - vocal_risk) * 0.20
        )

        heart_score = self._heart_flow_score(a, b, energy_diff)

        # -------------------------
        # FINAL SCORE (AI WEIGHTED MODEL)
        # -------------------------
        final_score = (

            bpm_score * 0.22 +
            energy_score * 0.22 +
            key_score * 0.15 +
            mood_score * 0.15 +
            drop_score * 0.10 +
            ear_score * 0.09 +
            heart_score * 0.07

        )

        strategy = self._mix_strategy(bpm_diff, energy_diff, key_score)
        grade = self._grade(final_score)
        pitch_percent = self._pitch_percent(bpm_a, bpm_b)
        cue_advice = self._cue_advice(strategy, energy_diff)
        advice = self._build_advice(
            a,
            b,
            bpm_diff,
            energy_diff,
            key_score,
            strategy,
            pitch_percent,
            cue_advice
        )

        return {
            "score": final_score,
            "bpm_score": bpm_score,
            "energy_score": energy_score,
            "key_score": key_score,
            "mood_score": mood_score,
            "drop_score": drop_score,
            "heart_score": heart_score,
            "strategy": strategy,
            "grade": grade,
            "pitch_percent": pitch_percent,
            "cue_advice": cue_advice,
            "advice": advice,
        }

    def _camelot_score(self, key_a, key_b):

        if not key_a or not key_b:
            return 0.6

        if key_a == key_b:
            return 1.0

        parsed_a = self._parse_camelot(key_a)
        parsed_b = self._parse_camelot(key_b)

        if not parsed_a or not parsed_b:
            return 0.6

        number_a, letter_a = parsed_a
        number_b, letter_b = parsed_b

        if letter_a == letter_b and number_b in {
            ((number_a - 2) % 12) + 1,
            (number_a % 12) + 1
        }:
            return 0.9

        if number_a == number_b and letter_a != letter_b:
            return 0.8

        return 0.45

    def _parse_camelot(self, value):

        value = str(value or "").strip().upper()

        if len(value) < 2:
            return None

        try:
            number = int(value[:-1])
        except ValueError:
            return None

        letter = value[-1]

        if letter not in {"A", "B"}:
            return None

        number = ((number - 1) % 12) + 1

        return number, letter

    def _mix_strategy(self, bpm_diff, energy_diff, key_score):

        if bpm_diff <= 3 and key_score >= 0.9:
            return "LONG_BLEND"

        if energy_diff >= 0.18:
            return "ENERGY_LIFT"

        if energy_diff <= -0.18:
            return "RESET_OR_BREAK"

        if bpm_diff <= 6:
            return "SHORT_BLEND"

        return "CUT_OR_FILTER"

    def _grade(self, score):

        if score >= 0.86:
            return "A+"

        if score >= 0.78:
            return "A"

        if score >= 0.68:
            return "B"

        if score >= 0.58:
            return "C"

        return "RISK"

    def _pitch_percent(self, bpm_a, bpm_b):

        if bpm_b <= 0:
            return 0

        return round(((bpm_a - bpm_b) / bpm_b) * 100, 2)

    def _cue_advice(self, strategy, energy_diff):

        if strategy == "LONG_BLEND":
            return "32 bar uzun blend; low EQ ile gir, midleri yavas ac."

        if strategy == "ENERGY_LIFT":
            return "Drop oncesi 16 bar hazirla; yeni parcayi hook veya build-up ile sok."

        if strategy == "RESET_OR_BREAK":
            return "Breakdown ya da vokal boslugunda reset; kalabaliga nefes aldir."

        if strategy == "SHORT_BLEND":
            return "16 bar kisa blend; kickler cakismadan bass swap yap."

        if energy_diff < -0.1:
            return "Kisa echo/filter cikisi guvenli olur."

        return "8-16 bar filtreli gecis; groove bozulursa cut yap."

    def _build_advice(
        self,
        a,
        b,
        bpm_diff,
        energy_diff,
        key_score,
        strategy,
        pitch_percent,
        cue_advice
    ):

        name_a = a.get("name", "onceki parca")
        name_b = b.get("name", "siradaki parca")

        if key_score >= 0.9:
            key_text = "harmoni cok uyumlu"
        elif key_score >= 0.8:
            key_text = "paralel tonalite uygun"
        else:
            key_text = "harmoni zayif, kisa gecis daha guvenli"

        if energy_diff > 0.08:
            energy_text = "enerjiyi yukari tasir"
        elif energy_diff < -0.08:
            energy_text = "enerjiyi kontrollu dusurur"
        else:
            energy_text = "enerjiyi sabit tutar"

        return (
            f"{name_a} -> {name_b}: {strategy}. "
            f"BPM farki {bpm_diff:.1f}, pitch {pitch_percent:+.2f}%, "
            f"{key_text}, {energy_text}. {cue_advice}"
        )

    def _number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    # =====================================================
    # MOOD SIMILARITY (VECTOR DISTANCE)
    # =====================================================
    def _mood_similarity(self, a, b):

        if not a or not b:
            return 0.5

        a = np.array(a)
        b = np.array(b)

        dist = np.linalg.norm(a - b)

        return max(0, 1 - dist)

    def _heart_flow_score(self, a, b, energy_diff):

        heart_a = self._number(a.get("heart_score"), 0.55)
        heart_b = self._number(b.get("heart_score"), 0.55)
        moment_a = str(a.get("crowd_moment", "")).upper()
        moment_b = str(b.get("crowd_moment", "")).upper()
        color_a = str(a.get("emotional_color", "")).upper()
        color_b = str(b.get("emotional_color", "")).upper()

        score = 0.45 + (heart_b * 0.35)

        if color_a and color_a == color_b:
            score += 0.10

        if moment_a == "INVITE" and moment_b in {"TRUST_BUILD", "LOCK_IN"}:
            score += 0.12

        if moment_a == "LOCK_IN" and moment_b == "RELEASE":
            score += 0.12

        if moment_a == "RELEASE" and energy_diff > 0.12:
            score -= 0.18

        return max(0.0, min(1.0, score))

    # =====================================================
    # FEATURE SAFETY
    # =====================================================
    def _ensure_features(self, tracks):

        # if analyzer already enriched, just pass through
        return tracks
