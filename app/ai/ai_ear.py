import re


class AIEar:

    def analyze(self, track):

        bpm = self.number(track.get("bpm"), 0)
        energy = self.number(track.get("energy"), 0.5)
        brightness = self.number(track.get("brightness"), 0.5)
        roughness = self.number(track.get("roughness"), 0)
        danceability = self.number(track.get("danceability"), 0)
        drop_strength = self.number(track.get("drop_strength"), 0)
        duration = self.number(track.get("duration"), 0)
        waveform = track.get("waveform") or []
        name = str(track.get("name", ""))
        genre = str(track.get("genre", ""))

        rhythmic_density = self.rhythmic_density(
            bpm,
            danceability,
            roughness,
            drop_strength
        )
        vocal_risk = self.vocal_risk(name, genre)
        intro_outro_mixability = self.intro_outro_mixability(
            duration,
            waveform,
            danceability,
            vocal_risk
        )
        crowd_energy_role = self.crowd_energy_role(
            energy,
            drop_strength,
            rhythmic_density
        )
        arrangement_score = self.arrangement_score(
            duration,
            drop_strength,
            waveform
        )

        ai_ear_score = round(
            rhythmic_density * 0.25 +
            intro_outro_mixability * 0.25 +
            (1 - vocal_risk) * 0.15 +
            arrangement_score * 0.20 +
            energy * 0.15,
            3
        )

        return {
            "ai_ear_score": ai_ear_score,
            "rhythmic_density": rhythmic_density,
            "vocal_risk": vocal_risk,
            "intro_outro_mixability": intro_outro_mixability,
            "arrangement_score": arrangement_score,
            "crowd_energy_role": crowd_energy_role,
            "ai_ear_summary": self.summary(
                ai_ear_score,
                rhythmic_density,
                vocal_risk,
                intro_outro_mixability,
                crowd_energy_role
            )
        }

    def rhythmic_density(self, bpm, danceability, roughness, drop_strength):

        bpm_drive = min(1.0, max(0.0, (bpm - 95) / 40)) if bpm else 0.45

        score = (
            bpm_drive * 0.35 +
            danceability * 0.35 +
            min(1.0, roughness * 8) * 0.10 +
            drop_strength * 0.20
        )

        return round(max(0.0, min(1.0, score)), 3)

    def vocal_risk(self, name, genre):

        text = f"{name} {genre}".lower()
        risk = 0.2

        high_risk_tokens = [
            "vocal",
            "acapella",
            "lyrics",
            "feat",
            "ft.",
            "live",
            "karaoke",
            "sing"
        ]

        low_risk_tokens = [
            "instrumental",
            "dub",
            "tool",
            "intro",
            "drum",
            "percussion"
        ]

        if any(token in text for token in high_risk_tokens):
            risk += 0.45

        if any(token in text for token in low_risk_tokens):
            risk -= 0.25

        if re.search(r"\b(remix|edit|mix)\b", text):
            risk -= 0.05

        return round(max(0.0, min(1.0, risk)), 3)

    def intro_outro_mixability(self, duration, waveform, danceability, vocal_risk):

        duration_score = 0.55

        if duration >= 300:
            duration_score = 0.9
        elif duration >= 240:
            duration_score = 0.75
        elif duration < 150 and duration > 0:
            duration_score = 0.35

        edge_score = self.waveform_edge_stability(waveform)

        score = (
            duration_score * 0.35 +
            edge_score * 0.30 +
            danceability * 0.20 +
            (1 - vocal_risk) * 0.15
        )

        return round(max(0.0, min(1.0, score)), 3)

    def waveform_edge_stability(self, waveform):

        if not waveform or len(waveform) < 24:
            return 0.5

        size = max(8, int(len(waveform) * 0.12))
        intro = [abs(float(v or 0)) for v in waveform[:size]]
        outro = [abs(float(v or 0)) for v in waveform[-size:]]

        intro_level = sum(intro) / len(intro)
        outro_level = sum(outro) / len(outro)
        balance = 1 - min(1.0, abs(intro_level - outro_level))

        return round(max(0.0, min(1.0, balance)), 3)

    def crowd_energy_role(self, energy, drop_strength, rhythmic_density):

        if energy >= 0.82 and drop_strength >= 0.35:
            return "PEAK_WEAPON"

        if energy >= 0.68 and rhythmic_density >= 0.6:
            return "DRIVE_BUILDER"

        if energy <= 0.42:
            return "WARMUP_CONTROL"

        return "GROOVE_CONNECTOR"

    def arrangement_score(self, duration, drop_strength, waveform):

        duration_score = 0.6

        if 210 <= duration <= 480:
            duration_score = 0.85
        elif duration and duration < 120:
            duration_score = 0.3

        wave_score = self.waveform_edge_stability(waveform)

        score = duration_score * 0.45 + drop_strength * 0.25 + wave_score * 0.30

        return round(max(0.0, min(1.0, score)), 3)

    def summary(
        self,
        score,
        rhythmic_density,
        vocal_risk,
        intro_outro_mixability,
        crowd_energy_role
    ):

        if score >= 0.78:
            level = "PRO_READY"
        elif score >= 0.62:
            level = "USABLE"
        else:
            level = "NEEDS_DJ_REVIEW"

        return (
            f"{level}: role={crowd_energy_role}, "
            f"rhythm={rhythmic_density:.2f}, "
            f"vocal_risk={vocal_risk:.2f}, "
            f"mixability={intro_outro_mixability:.2f}"
        )

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
