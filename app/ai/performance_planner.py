class PerformancePlanner:

    STYLE_PROFILES = {
        "AFRO HOUSE": {
            "genres": {"AFRO HOUSE", "ORGANIC HOUSE", "DEEP HOUSE"},
            "bpm": (118, 123),
            "max_vocal_risk": 0.45,
            "target_energy": 0.48,
            "opening_roles": {"OPENING", "WARMUP", "GROOVE"},
        },
        "HOUSE": {
            "genres": {"DEEP HOUSE", "HOUSE", "ORGANIC HOUSE", "TECH HOUSE"},
            "bpm": (120, 124),
            "max_vocal_risk": 0.5,
            "target_energy": 0.52,
            "opening_roles": {"OPENING", "WARMUP", "GROOVE"},
        },
        "TECH HOUSE": {
            "genres": {"TECH HOUSE", "HOUSE", "DEEP HOUSE"},
            "bpm": (122, 126),
            "max_vocal_risk": 0.45,
            "target_energy": 0.58,
            "opening_roles": {"WARMUP", "GROOVE"},
        },
        "MELODIC": {
            "genres": {"MELODIC HOUSE", "MELODIC TECHNO", "ORGANIC HOUSE"},
            "bpm": (120, 124),
            "max_vocal_risk": 0.55,
            "target_energy": 0.5,
            "opening_roles": {"OPENING", "WARMUP", "GROOVE"},
        },
        "WEDDING": {
            "genres": {"TURKCE POP", "KINA GECESI", "OYUN HAVASI", "HALAY"},
            "bpm": (90, 124),
            "max_vocal_risk": 0.8,
            "target_energy": 0.55,
            "opening_roles": {"EVENT_SUPPORT", "REQUEST_FRIENDLY"},
        },
    }

    def recommend_openers(self, tracks, style="AFRO HOUSE", limit=10):

        profile = self.profile(style)
        scored = []

        for track in tracks:
            score, reasons = self.opening_score(track, profile)

            if score <= 0:
                continue

            item = dict(track)
            item["opening_score"] = round(score, 2)
            item["opening_reason"] = ", ".join(reasons)
            scored.append(item)

        return sorted(
            scored,
            key=lambda item: item["opening_score"],
            reverse=True
        )[:limit]

    def build_performance(self, tracks, style="AFRO HOUSE", hours=4):

        target_tracks = max(12, int(hours * 16))
        openers = self.recommend_openers(tracks, style, limit=5)
        profile = self.profile(style)

        if not openers:
            return {
                "style": style,
                "hours": hours,
                "opening": None,
                "tracks": [],
                "message": "Bu tarza uygun guvenli acilis parcasi bulunamadi.",
            }

        selected = [openers[0]]
        used = {openers[0].get("id")}

        candidates = sorted(
            tracks,
            key=lambda track: self.flow_score(track, profile),
            reverse=True
        )

        for track in candidates:
            if len(selected) >= target_tracks:
                break

            track_id = track.get("id")

            if track_id in used:
                continue

            selected.append(track)
            used.add(track_id)

        return {
            "style": style,
            "hours": hours,
            "opening": selected[0],
            "tracks": selected,
            "message": (
                f"{style} icin {hours} saatlik akista "
                f"{len(selected)} parca onerildi."
            ),
        }

    def opening_score(self, track, profile):

        bpm = self.number(track.get("bpm"), 0)
        energy = self.number(track.get("energy"), 0.5)
        vocal_risk = self.number(track.get("vocal_risk"), 0.35)
        mixability = self.number(track.get("intro_outro_mixability"), 0.5)
        ai_ear = self.number(track.get("ai_ear_score"), 0.5)
        genre = str(track.get("genre", "")).upper()
        parent = str(track.get("parent_genre", "")).upper()
        role = str(track.get("role", "")).upper()
        low, high = profile["bpm"]
        reasons = []
        score = 0

        if genre in profile["genres"] or parent in profile["genres"]:
            score += 28
            reasons.append("tarza uyumlu")

        if low <= bpm <= high:
            score += 22
            reasons.append("acilis BPM araliginda")
        else:
            score += max(0, 16 - min(abs(bpm - low), abs(bpm - high)))

        energy_distance = abs(energy - profile["target_energy"])
        score += max(0, 18 - (energy_distance * 40))

        if vocal_risk <= profile["max_vocal_risk"]:
            score += 14
            reasons.append("vokal riski dusuk")

        if mixability >= 0.62:
            score += 10
            reasons.append("intro/outro mix uygun")

        if ai_ear >= 0.62:
            score += 8
            reasons.append("AI Ear guvenli")

        if role in profile["opening_roles"]:
            score += 8
            reasons.append("rol acilisa uygun")

        return score, reasons or ["genel acilis adayi"]

    def flow_score(self, track, profile):

        score, _ = self.opening_score(track, profile)
        energy = self.number(track.get("energy"), 0.5)
        hit = self.number(track.get("trend_score"), 0) / 100

        return score + (energy * 20) + (hit * 10)

    def profile(self, style):

        key = str(style or "AFRO HOUSE").upper()

        return self.STYLE_PROFILES.get(
            key,
            self.STYLE_PROFILES["AFRO HOUSE"]
        )

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
