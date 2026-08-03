import os
import re


class ClubIntelligence:

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

    def normalize_track_tempo(self, track):

        original = self.number(track.get("bpm"), 0)

        if original <= 0:
            return {
                "bpm": original,
                "bpm_original": original,
                "bpm_correction": "NO_TEMPO",
                "tempo_confidence": 0.0,
                "tempo_warning": "BPM bulunamadi; set oncesi manuel kontrol gerekir.",
            }

        text = self.track_text(track)
        filename_bpm = self.extract_filename_bpm(text)
        low, high = self.style_window(track, text)
        candidates = self.tempo_candidates(original, filename_bpm)

        best = sorted(
            candidates,
            key=lambda value: self.tempo_score(value, low, high, filename_bpm),
            reverse=True
        )[0]

        correction = "UNCHANGED"

        if abs(best - original) >= 0.5:
            if best > original:
                correction = "DOUBLE_TIME_CORRECTED"
            else:
                correction = "HALF_TIME_CORRECTED"

        confidence = self.tempo_confidence(best, low, high, filename_bpm, correction)
        warning = ""

        if correction != "UNCHANGED":
            warning = (
                f"BPM {original:g} -> {best:g} duzeltildi; "
                "yarim/cift tempo ihtimali yakalandi."
            )
        elif not (low <= best <= high):
            warning = (
                f"BPM {best:g} tarz penceresinin disinda "
                f"({low}-{high}); DJ kontrolu onerilir."
            )

        return {
            "bpm": round(best, 2),
            "bpm_original": round(original, 2),
            "bpm_correction": correction,
            "tempo_confidence": round(confidence, 2),
            "tempo_warning": warning,
        }

    def tempo_candidates(self, original, filename_bpm):

        seeds = [original]

        if filename_bpm:
            seeds.append(filename_bpm)

        candidates = set()

        for seed in seeds:
            for multiplier in (0.25, 0.5, 1, 2, 4):
                value = seed * multiplier

                if 55 <= value <= 205:
                    candidates.add(round(value, 2))

        return list(candidates) or [original]

    def tempo_score(self, bpm, low, high, filename_bpm):

        center = (low + high) / 2

        if low <= bpm <= high:
            style_score = 1.0
        else:
            distance = min(abs(bpm - low), abs(bpm - high))
            style_score = max(0.0, 1 - (distance / 48))

        filename_score = 0

        if filename_bpm:
            filename_score = max(0.0, 1 - (abs(bpm - filename_bpm) / 8))

        center_score = max(0.0, 1 - (abs(bpm - center) / 60))

        return style_score * 0.58 + filename_score * 0.30 + center_score * 0.12

    def tempo_confidence(self, bpm, low, high, filename_bpm, correction):

        confidence = 0.45

        if low <= bpm <= high:
            confidence += 0.28

        if filename_bpm and abs(bpm - filename_bpm) <= 2:
            confidence += 0.18

        if correction != "UNCHANGED":
            confidence += 0.09

        return max(0.0, min(1.0, confidence))

    def style_window(self, track, text):

        fields = [
            str(track.get("genre", "")),
            str(track.get("parent_genre", "")),
            str(track.get("subgenre", "")),
            text,
        ]
        haystack = " ".join(fields).upper()

        for style, window in self.STYLE_WINDOWS.items():
            if style in haystack:
                return window

        return (90, 132)

    def extract_filename_bpm(self, text):

        matches = re.findall(r"(?<!\d)(\d{2,3})(?:\s|-)*(?:bpm|b p m)(?![a-z])", text)

        if not matches:
            matches = re.findall(r"(?<!\d)(\d{2,3})(?!\d)", os.path.basename(text))

        candidates = [
            self.number(match, 0)
            for match in matches
        ]
        candidates = [
            value
            for value in candidates
            if 55 <= value <= 205
        ]

        if not candidates:
            return 0

        return candidates[-1]

    def track_text(self, track):

        return " ".join([
            str(track.get("name", "")),
            str(track.get("path", "")),
            str(track.get("artist", "")),
            str(track.get("genre", "")),
        ]).lower()

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
