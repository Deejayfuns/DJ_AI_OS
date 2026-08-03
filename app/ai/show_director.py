class ShowDirector:

    ARC = [
        {
            "name": "DOORS_OPEN",
            "energy": (0.25, 0.45),
            "purpose": "Odayi doldur, konusmalari ezmeden groove kur.",
            "duration_ratio": 0.12,
        },
        {
            "name": "WARMUP_LOCK",
            "energy": (0.40, 0.58),
            "purpose": "Ritmi sabitle, dans pistine ilk guveni ver.",
            "duration_ratio": 0.18,
        },
        {
            "name": "FIRST_LIFT",
            "energy": (0.55, 0.72),
            "purpose": "Kalabaliga gecenin yonunu goster.",
            "duration_ratio": 0.20,
        },
        {
            "name": "RESET_BREATH",
            "energy": (0.45, 0.62),
            "purpose": "Yorgunlugu al, vokal ya da melodik nefes ver.",
            "duration_ratio": 0.12,
        },
        {
            "name": "MAIN_PEAK",
            "energy": (0.72, 0.95),
            "purpose": "Gecenin imza anini yarat.",
            "duration_ratio": 0.25,
        },
        {
            "name": "CLOSING_MEMORY",
            "energy": (0.45, 0.70),
            "purpose": "Insanlarin aklinda kalacak final hissini kur.",
            "duration_ratio": 0.13,
        },
    ]

    def build_show(self, tracks, style="AFRO HOUSE", hours=4):

        if not tracks:
            return {
                "style": style,
                "hours": hours,
                "segments": [],
                "rescue_tracks": [],
                "director_note": "Arsiv bos; show kurmak icin analiz edilmis parca gerekli.",
            }

        segment_count = max(1, int(hours * 16))
        selected = set()
        segments = []

        for arc in self.ARC:
            target_count = max(1, int(segment_count * arc["duration_ratio"]))
            picks = self.pick_segment_tracks(
                tracks,
                arc,
                style,
                target_count,
                selected
            )
            selected.update(track.get("id") for track in picks)
            segments.append({
                "name": arc["name"],
                "purpose": arc["purpose"],
                "target_energy": arc["energy"],
                "tracks": picks,
                "risk": self.segment_risk(picks),
                "instruction": self.segment_instruction(arc, picks),
            })

        rescue_tracks = self.pick_rescue_tracks(tracks, selected)

        return {
            "style": style,
            "hours": hours,
            "segments": segments,
            "rescue_tracks": rescue_tracks,
            "director_note": self.director_note(segments, rescue_tracks),
        }

    def pick_segment_tracks(self, tracks, arc, style, limit, selected):

        low, high = arc["energy"]
        candidates = []

        for track in tracks:
            if track.get("id") in selected:
                continue

            score = self.track_score(track, low, high, style)

            if score <= 0:
                continue

            item = dict(track)
            item["show_segment"] = arc["name"]
            item["show_score"] = round(score, 2)
            item["director_cue"] = self.track_cue(item, arc)
            candidates.append(item)

        return sorted(
            candidates,
            key=lambda item: item["show_score"],
            reverse=True
        )[:limit]

    def track_score(self, track, low, high, style):

        energy = self.number(track.get("energy"), 0.5)
        bpm = self.number(track.get("bpm"), 0)
        ear = self.number(track.get("ai_ear_score"), 0.5)
        mixability = self.number(track.get("intro_outro_mixability"), 0.5)
        vocal_risk = self.number(track.get("vocal_risk"), 0.35)
        genre = str(track.get("genre", "")).upper()
        parent = str(track.get("parent_genre", "")).upper()
        score = 0

        if low <= energy <= high:
            score += 35
        else:
            score += max(0, 20 - abs(energy - ((low + high) / 2)) * 50)

        if self.style_matches(style, genre, parent):
            score += 20

        score += ear * 18
        score += mixability * 14
        score += (1 - vocal_risk) * 8

        if bpm:
            score += 5

        if track.get("duplicate_status") == "POSSIBLE_DUPLICATE":
            score -= 20

        if track.get("analysis_status") == "FALLBACK":
            score -= 15

        return score

    def pick_rescue_tracks(self, tracks, used):

        rescue = []

        for track in self.rescue_pool(tracks, used):
            if (
                track.get("id") in used and
                len(tracks) > len(used)
            ):
                continue

            energy = self.number(track.get("energy"), 0.5)
            mixability = self.number(track.get("intro_outro_mixability"), 0.5)
            vocal_risk = self.number(track.get("vocal_risk"), 0.35)
            score = mixability * 45 + (1 - vocal_risk) * 25

            if 0.52 <= energy <= 0.74:
                score += 20

            if track.get("crowd_energy_role") in {"DRIVE_BUILDER", "GROOVE_CONNECTOR"}:
                score += 10

            item = dict(track)
            item["rescue_score"] = round(score, 2)
            item["director_cue"] = (
                "Floor duserse bunu 16 bar filtreyle sok; "
                "bass swap sonrasi guveni geri al."
            )
            rescue.append(item)

        return sorted(
            rescue,
            key=lambda item: item["rescue_score"],
            reverse=True
        )[:5]

    def rescue_pool(self, tracks, used):

        unused = [
            track for track in tracks
            if track.get("id") not in used
        ]

        if unused:
            return unused

        return tracks

    def segment_risk(self, tracks):

        if not tracks:
            return "NO_TRACKS"

        avg_vocal = sum(
            self.number(track.get("vocal_risk"), 0.35)
            for track in tracks
        ) / len(tracks)
        avg_mix = sum(
            self.number(track.get("intro_outro_mixability"), 0.5)
            for track in tracks
        ) / len(tracks)

        if avg_vocal >= 0.65:
            return "VOCAL_OVERLOAD"

        if avg_mix < 0.45:
            return "HARD_TO_MIX"

        return "CONTROLLED"

    def segment_instruction(self, arc, tracks):

        if not tracks:
            return "Bu bolum icin yeterli guvenli parca yok."

        first = tracks[0].get("name", "ilk parca")

        if arc["name"] == "MAIN_PEAK":
            return f"{first} ile ana imza anini kur; 2 parca once enerjiyi hazirla."

        if arc["name"] == "RESET_BREATH":
            return f"{first} ile nefes aldir; vokal varsa bass'i sade tut."

        if arc["name"] == "CLOSING_MEMORY":
            return f"{first} ile kapanisi akilda kalir yap; ani tempo ziplama yapma."

        return f"{first} ile bolumu baslat; 16-32 bar kontrollu gecis kullan."

    def track_cue(self, track, arc):

        phrase = track.get("phrase_points") or []
        start = self.find_phrase(phrase, "START")
        build = self.find_phrase(phrase, "BUILD")

        return (
            f"{arc['name']}: START {start:.2f}, BUILD {build:.2f}. "
            f"Amac: {arc['purpose']}"
        )

    def director_note(self, segments, rescue_tracks):

        risks = [
            segment["risk"]
            for segment in segments
            if segment["risk"] != "CONTROLLED"
        ]

        if risks:
            return (
                "Show hazir ama risk var: "
                f"{', '.join(risks)}. Rescue crate'i elinin altinda tut."
            )

        if rescue_tracks:
            return (
                "Show kontrollu. Rescue crate hazir; floor duserse ilk "
                f"kurtarma: {rescue_tracks[0].get('name')}."
            )

        return "Show kontrollu. Arsiv daha da buyudukce kurtarma secenekleri guclenir."

    def style_matches(self, style, genre, parent):

        style = str(style or "").upper()

        if style in genre or style in parent:
            return True

        if style == "AFRO HOUSE":
            return genre in {"AFRO HOUSE", "ORGANIC HOUSE", "DEEP HOUSE"}

        if style == "MELODIC":
            return genre in {"MELODIC HOUSE", "MELODIC TECHNO", "ORGANIC HOUSE"}

        return False

    def find_phrase(self, phrase_points, label):

        for point in phrase_points:
            if point.get("label") == label:
                return self.number(point.get("position"), 0)

        return 0

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
