"""
DJ AI OS — DJ Brain (Consolidated Intelligence)

Merges: DJHeart + ClubIntelligence + DJCoach + FeedbackLearner
Single class that handles ALL DJ intelligence:
- Track emotional analysis
- Club/venue intelligence
- Set coaching & feedback
- BPM correction & style windows
- Energy arc analysis
"""

import math
from collections import Counter
from typing import Dict, List, Any, Optional


class DJBrain:
    """
    Central DJ intelligence — the brain behind every recommendation.
    """

    # ============================================================
    # STYLE WINDOWS (from ClubIntelligence)
    # ============================================================

    STYLE_WINDOWS = {
        "HOUSE": (115, 130),
        "AFRO HOUSE": (115, 130),
        "ORGANIC HOUSE": (112, 126),
        "DEEP HOUSE": (112, 126),
        "TECH HOUSE": (122, 130),
        "MELODIC HOUSE": (118, 128),
        "TECHNO": (124, 150),
        "MELODIC TECHNO": (120, 132),
        "TRANCE": (128, 145),
        "HIP HOP": (70, 110),
        "TRAP": (70, 110),
        "RNB": (70, 105),
        "AFROBEATS": (90, 116),
        "REGGAETON": (88, 106),
        "LATIN": (85, 130),
        "BAILE FUNK": (125, 135),
        "COMMERCIAL": (95, 135),
        "WEDDING & EVENT": (70, 150),
    }

    # ============================================================
    # TRACK ANALYSIS (from DJHeart)
    # ============================================================

    def analyze_track(self, track: Dict) -> Dict:
        """Full track analysis — emotional, crowd, heart score."""
        energy = self._num(track.get("energy"), 0.5)
        brightness = self._num(track.get("brightness"), 0.5)
        vocal_risk = self._num(track.get("vocal_risk"), 0.35)
        mixability = self._num(track.get("intro_outro_mixability"), 0.5)
        ai_ear = self._num(track.get("ai_ear_score"), 0.5)
        role = str(track.get("role", "")).upper()
        genre = str(track.get("genre", "")).upper()

        emotional_color = self._emotional_color(energy, brightness, vocal_risk, genre)
        crowd_moment = self._crowd_moment(energy, vocal_risk, role)
        heart_score = round(
            energy * 0.28 + brightness * 0.16 + (1 - vocal_risk) * 0.18 +
            mixability * 0.18 + ai_ear * 0.20, 3
        )

        return {
            "heart_score": heart_score,
            "emotional_color": emotional_color,
            "crowd_moment": crowd_moment,
            "heart_advice": self._heart_advice(emotional_color, crowd_moment, heart_score, vocal_risk),
        }

    def build_heart_map(self, tracks: List[Dict]) -> Dict:
        """Build emotional map of a set."""
        if not tracks:
            return {"pulse": 0, "shape": "EMPTY", "moments": [], "advice": "Analiz edilmis parca gerekli."}

        enriched = [{**t, **self.analyze_track(t)} for t in tracks]
        pulse = round(sum(i["heart_score"] for i in enriched) / len(enriched), 3)
        energies = [self._num(i.get("energy"), 0.5) for i in enriched]
        shape = self._arc_shape(energies)

        moments = [
            {
                "position": idx + 1,
                "name": item.get("name", "UNKNOWN"),
                "heart_score": item["heart_score"],
                "color": item["emotional_color"],
                "moment": item["crowd_moment"],
                "advice": item["heart_advice"],
            }
            for idx, item in enumerate(enriched[:24])
        ]

        return {"pulse": pulse, "shape": shape, "moments": moments, "advice": self._map_advice(pulse, shape)}

    # ============================================================
    # BPM CORRECTION (from ClubIntelligence)
    # ============================================================

    def normalize_tempo(self, track: Dict) -> Dict:
        """Normalize BPM with style window detection and half/double correction."""
        original = self._num(track.get("bpm"), 0)
        if original <= 0:
            return {"bpm": 0, "correction": "NO_TEMPO", "confidence": 0.0, "warning": "BPM bulunamadi"}

        text = self._track_text(track)
        filename_bpm = self._extract_filename_bpm(text)
        low, high = self._style_window(track, text)
        candidates = self._tempo_candidates(original, filename_bpm)
        best = sorted(candidates, key=lambda v: self._tempo_score(v, low, high, filename_bpm), reverse=True)[0]

        correction = "UNCHANGED"
        if abs(best - original) >= 0.5:
            correction = "DOUBLE_TIME" if best > original else "HALF_TIME"

        confidence = self._tempo_confidence(best, low, high, filename_bpm, correction)

        return {
            "bpm": round(best, 2), "bpm_original": round(original, 2),
            "correction": correction, "confidence": round(confidence, 2),
            "warning": "" if (low <= best <= high) else f"BPM {best:.0f} tarz penceresi disinda ({low}-{high})",
        }

    # ============================================================
    # SET COACHING (from DJCoach)
    # ============================================================

    def analyze_set(self, tracks: List[Dict], venue: str = "CLUB", hours: float = 4) -> Dict:
        """Full set analysis with coaching feedback."""
        if not tracks:
            return {"score": 0, "issues": [], "advice": "Set bos"}

        energies = [self._num(t.get("energy"), 0.5) for t in tracks]
        bpms = [self._num(t.get("bpm"), 120) for t in tracks]
        genres = [str(t.get("genre", "unknown")).lower() for t in tracks]

        # Energy arc
        arc = self._analyze_energy_arc(energies)
        bpm_flow = self._analyze_bpm_flow(bpms)
        genre_diversity = len(set(genres)) / max(1, len(genres))

        # Score
        score = int(
            arc["score"] * 0.35 +
            bpm_flow["score"] * 0.25 +
            genre_diversity * 100 * 0.20 +
            min(100, len(tracks) / max(1, hours * 10) * 100) * 0.20
        )

        issues = []
        if arc["issue"]:
            issues.append(arc["issue"])
        if bpm_flow["issue"]:
            issues.append(bpm_flow["issue"])
        if genre_diversity < 0.3:
            issues.append(f"Tur cesitliligi dusuk: {genre_diversity:.0%}")

        advice = self._set_advice(score, arc, bpm_flow, venue)

        return {
            "score": score, "issues": issues, "advice": advice,
            "energy_arc": arc, "bpm_flow": bpm_flow,
            "genre_diversity": genre_diversity,
            "track_count": len(tracks), "avg_bpm": round(sum(bpms) / len(bpms), 1),
        }

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _emotional_color(self, energy, brightness, vocal_risk, genre):
        if "AFRO" in genre or "ORGANIC" in genre:
            return "TRIBAL_LIFT" if energy >= 0.62 else "EARTHY_WARMTH"
        if energy >= 0.82 and brightness >= 0.58:
            return "EUPHORIC_FIRE"
        if energy >= 0.65:
            return "DRIVING_CONFIDENCE"
        if vocal_risk >= 0.58:
            return "LYRIC_MEMORY"
        if brightness <= 0.38:
            return "DEEP_SHADOW"
        return "SOFT_CONNECTION"

    def _crowd_moment(self, energy, vocal_risk, role):
        if role == "OPENING" or energy < 0.42:
            return "INVITE"
        if role == "PEAK TIME" or energy >= 0.82:
            return "RELEASE"
        if vocal_risk >= 0.62:
            return "SING_ALONG"
        if energy >= 0.62:
            return "LOCK_IN"
        return "TRUST_BUILD"

    def _heart_advice(self, color, moment, score, vocal_risk):
        if moment == "INVITE":
            return "Kalabaligi zorlamadan iceri al."
        if moment == "RELEASE":
            return "Bu parca an yaratir; 1-2 parca once zemini hazirla."
        if moment == "SING_ALONG":
            return "Vokal hafizasi guclu; ustuste bindirme yapma."
        if score < 0.52:
            return "Duygusal bag zayif; utility olarak kullan."
        if color in {"EARTHY_WARMTH", "SOFT_CONNECTION"}:
            return "Baslangic/reset icin guvenli; uzun blend iyi calisir."
        return "Groove kilitlenince 16-32 bar kontrollu yukselis ver."

    def _arc_shape(self, energies):
        if len(energies) < 3:
            return "SHORT_PULSE"
        n = len(energies)
        first = sum(energies[:n // 3]) / max(1, n // 3)
        last = sum(energies[-n // 3:]) / max(1, n // 3)
        peak = max(energies)
        if peak - first > 0.25 and peak - last > 0.12:
            return "CLASSIC_CLIMB_AND_RELEASE"
        if last - first > 0.18:
            return "RISING_PRESSURE"
        if first - last > 0.18:
            return "COOLDOWN_STORY"
        return "STEADY_GROOVE"

    def _map_advice(self, pulse, shape):
        if pulse < 0.52:
            return "Setin kalbi zayif; daha guvenli groove ekle."
        if shape == "RISING_PRESSURE":
            return "Enerji surekli yukseliyor; araya reset koy."
        if shape == "COOLDOWN_STORY":
            return "Akis yumusuyor; kapanis icin iyi."
        if shape == "CLASSIC_CLIMB_AND_RELEASE":
            return "Dramaturji guclu; peak anini erken harcama."
        return "Kalp stabil; crowd okumaya gore lift veya reset sec."

    def _style_window(self, track, text):
        fields = [str(track.get("genre", "")), str(track.get("parent_genre", "")), text]
        haystack = " ".join(fields).upper()
        for style, window in self.STYLE_WINDOWS.items():
            if style in haystack:
                return window
        return (90, 132)

    def _tempo_candidates(self, original, filename_bpm):
        seeds = [original] + ([filename_bpm] if filename_bpm else [])
        candidates = set()
        for seed in seeds:
            for mult in (0.25, 0.5, 1, 2, 4):
                val = seed * mult
                if 55 <= val <= 205:
                    candidates.add(round(val, 2))
        return list(candidates) or [original]

    def _tempo_score(self, bpm, low, high, filename_bpm):
        style = 1.0 if low <= bpm <= high else max(0.0, 1 - min(abs(bpm - low), abs(bpm - high)) / 48)
        fname = max(0.0, 1 - abs(bpm - filename_bpm) / 8) if filename_bpm else 0
        center = max(0.0, 1 - abs(bpm - (low + high) / 2) / 60)
        return style * 0.58 + fname * 0.30 + center * 0.12

    def _tempo_confidence(self, bpm, low, high, filename_bpm, correction):
        c = 0.45
        if low <= bpm <= high:
            c += 0.28
        if filename_bpm and abs(bpm - filename_bpm) <= 2:
            c += 0.18
        if correction != "UNCHANGED":
            c += 0.09
        return max(0.0, min(1.0, c))

    def _extract_filename_bpm(self, text):
        import re, os
        matches = re.findall(r"(?<!\d)(\d{2,3})(?:\s|-)*(?:bpm)(?![a-z])", text)
        if not matches:
            matches = re.findall(r"(?<!\d)(\d{2,3})(?!\d)", os.path.basename(text))
        vals = [self._num(m, 0) for m in matches]
        vals = [v for v in vals if 55 <= v <= 205]
        return vals[-1] if vals else 0

    def _track_text(self, track):
        return " ".join([str(track.get(k, "")) for k in ("name", "path", "artist", "genre")]).lower()

    def _analyze_energy_arc(self, energies):
        n = len(energies)
        if n < 3:
            return {"score": 50, "issue": "Cok az parca", "shape": "UNKNOWN"}
        first_avg = sum(energies[:n // 3]) / (n // 3)
        last_avg = sum(energies[-n // 3:]) / (n // 3)
        peak = max(energies)
        peak_idx = energies.index(peak)

        if peak_idx < n // 4:
            shape, issue = "EARLY_PEAK", "Peak cok erken geldi; crowd yorulabilir"
        elif peak_idx > 3 * n // 4:
            shape, issue = "LATE_PEAK", "Peak cok gec; crowd sogumus olabilir"
        elif last_avg < first_avg - 0.15:
            shape, issue = "GOOD_ARC", ""
        else:
            shape, issue = "FLAT", ""

        score = 80 if not issue else 50
        return {"score": score, "shape": shape, "issue": issue}

    def _analyze_bpm_flow(self, bpms):
        n = len(bpms)
        if n < 2:
            return {"score": 50, "issue": ""}
        jumps = [abs(bpms[i] - bpms[i - 1]) for i in range(1, n)]
        max_jump = max(jumps)
        avg_jump = sum(jumps) / len(jumps)

        if max_jump > 15:
            return {"score": 40, "issue": f"BPM cok buyuk atlama: {max_jump:.0f}"}
        if avg_jump > 8:
            return {"score": 60, "issue": "BPM akisi dalgalanmis"}
        return {"score": 90, "issue": ""}

    def _set_advice(self, score, arc, bpm_flow, venue):
        tips = []
        if score < 60:
            tips.append("Seti basindan sonuna gozden gecir.")
        if arc.get("issue"):
            tips.append(arc["issue"])
        if bpm_flow.get("issue"):
            tips.append(bpm_flow["issue"])
        if venue == "WEDDING":
            tips.append("Dugun icin daha genis tur yelpazesi ve yavas baslangic onerilir.")
        elif venue == "FESTIVAL":
            tips.append("Festival icin yuksek enerji ve buyuk anlar yarat.")
        return " ".join(tips) if tips else "Set saglikli gorunuyor; crowd okumaya devam et."

    def _num(self, value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
