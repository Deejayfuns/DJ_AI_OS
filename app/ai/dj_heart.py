class DJHeart:

    def analyze_track(self, track):

        energy = self.number(track.get("energy"), 0.5)
        brightness = self.number(track.get("brightness"), 0.5)
        vocal_risk = self.number(track.get("vocal_risk"), 0.35)
        mixability = self.number(track.get("intro_outro_mixability"), 0.5)
        ai_ear = self.number(track.get("ai_ear_score"), 0.5)
        role = str(track.get("role", "")).upper()
        genre = str(track.get("genre", "")).upper()

        emotional_color = self.emotional_color(energy, brightness, vocal_risk, genre)
        crowd_moment = self.crowd_moment(energy, vocal_risk, role)
        heart_score = round(
            energy * 0.28 +
            brightness * 0.16 +
            (1 - vocal_risk) * 0.18 +
            mixability * 0.18 +
            ai_ear * 0.20,
            3
        )

        return {
            "heart_score": heart_score,
            "emotional_color": emotional_color,
            "crowd_moment": crowd_moment,
            "heart_advice": self.heart_advice(
                emotional_color,
                crowd_moment,
                heart_score,
                vocal_risk
            ),
        }

    def build_heart_map(self, tracks):

        if not tracks:
            return {
                "pulse": 0,
                "shape": "EMPTY",
                "moments": [],
                "advice": "Kalp haritasi icin once analiz edilmis parca gerekli.",
            }

        enriched = [
            {**track, **self.analyze_track(track)}
            for track in tracks
        ]
        pulse = round(
            sum(item["heart_score"] for item in enriched) / len(enriched),
            3
        )
        energies = [
            self.number(item.get("energy"), 0.5)
            for item in enriched
        ]
        shape = self.arc_shape(energies)

        moments = []

        for index, item in enumerate(enriched[:24], start=1):
            moments.append({
                "position": index,
                "name": item.get("name", "UNKNOWN"),
                "heart_score": item["heart_score"],
                "color": item["emotional_color"],
                "moment": item["crowd_moment"],
                "advice": item["heart_advice"],
            })

        return {
            "pulse": pulse,
            "shape": shape,
            "moments": moments,
            "advice": self.map_advice(pulse, shape),
        }

    def emotional_color(self, energy, brightness, vocal_risk, genre):

        if "AFRO" in genre or "ORGANIC" in genre:
            if energy < 0.62:
                return "EARTHY_WARMTH"
            return "TRIBAL_LIFT"

        if energy >= 0.82 and brightness >= 0.58:
            return "EUPHORIC_FIRE"

        if energy >= 0.65:
            return "DRIVING_CONFIDENCE"

        if vocal_risk >= 0.58:
            return "LYRIC_MEMORY"

        if brightness <= 0.38:
            return "DEEP_SHADOW"

        return "SOFT_CONNECTION"

    def crowd_moment(self, energy, vocal_risk, role):

        if role == "OPENING" or energy < 0.42:
            return "INVITE"

        if role == "PEAK TIME" or energy >= 0.82:
            return "RELEASE"

        if vocal_risk >= 0.62:
            return "SING_ALONG"

        if energy >= 0.62:
            return "LOCK_IN"

        return "TRUST_BUILD"

    def heart_advice(self, color, moment, score, vocal_risk):

        if moment == "INVITE":
            return "Kalabaligi zorlamadan iceri al; kick temiz, vokal az olsun."

        if moment == "RELEASE":
            return "Bu parca an yaratir; 1-2 parca once zemini hazirla."

        if moment == "SING_ALONG":
            return "Vokal hafizasi guclu; ust uste vokal bindirme, nefes birak."

        if score < 0.52:
            return "Duygusal bag zayif; bunu utility veya gecis parcasi gibi kullan."

        if vocal_risk > 0.55:
            return "Vokal riski var; mixi kisa tut ve sozleri carpisma."

        if color in {"EARTHY_WARMTH", "SOFT_CONNECTION"}:
            return "Baslangic veya reset icin guvenli; uzun blend iyi calisir."

        return "Groove kilitlenince 16-32 bar kontrollu yukselis ver."

    def arc_shape(self, energies):

        if len(energies) < 3:
            return "SHORT_PULSE"

        first = sum(energies[: max(1, len(energies) // 3)]) / max(1, len(energies) // 3)
        last = sum(energies[-max(1, len(energies) // 3):]) / max(1, len(energies) // 3)
        peak = max(energies)

        if peak - first > 0.25 and peak - last > 0.12:
            return "CLASSIC_CLIMB_AND_RELEASE"

        if last - first > 0.18:
            return "RISING_PRESSURE"

        if first - last > 0.18:
            return "COOLDOWN_STORY"

        return "STEADY_GROOVE"

    def map_advice(self, pulse, shape):

        if pulse < 0.52:
            return "Setin kalbi zayif; daha guvenli groove veya vokal hafizasi ekle."

        if shape == "RISING_PRESSURE":
            return "Enerji surekli yukseliyor; araya reset parcasi koymazsan yorabilir."

        if shape == "COOLDOWN_STORY":
            return "Akis yumusuyor; kapanis icin iyi, peak hedefliyorsan lift ekle."

        if shape == "CLASSIC_CLIMB_AND_RELEASE":
            return "Dramaturji guclu; peak anini fazla erken harcama."

        return "Kalp stabil; crowd okumaya gore lift veya reset sec."

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
