class MixMasterDoctor:

    def diagnose(self, track):

        profile = self.profile(track)
        issues = self.issue_list(profile)
        score = self.professional_score(profile, issues)

        return {
            "track": track.get("name", "UNKNOWN"),
            "score": score,
            "verdict": self.verdict(score),
            "profile": profile,
            "issues": issues,
            "urgent_fixes": self.urgent_fixes(issues),
            "suno_rescue_chain": self.suno_rescue_chain(profile, issues),
            "mix_chain": self.mix_chain(profile, issues),
            "mastering_chain": self.mastering_chain(profile, score),
            "stem_strategy": self.stem_strategy(profile),
            "reference_targets": self.reference_targets(profile),
            "doctor_note": self.doctor_note(score, issues),
        }

    def profile(self, track):

        genre = str(track.get("genre") or "UNKNOWN").upper()
        role = str(track.get("role") or "").upper()
        name = str(track.get("name") or track.get("path") or "").lower()

        return {
            "genre": genre,
            "role": role,
            "energy": self.number(track.get("energy"), 0.5),
            "brightness": self.number(track.get("brightness"), 0.5),
            "roughness": self.number(track.get("roughness"), 0.12),
            "danceability": self.number(track.get("danceability"), 0.6),
            "drop_strength": self.number(track.get("drop_strength"), 0.2),
            "vocal_risk": self.number(track.get("vocal_risk"), 0.35),
            "mixability": self.number(track.get("intro_outro_mixability"), 0.55),
            "stereo_width": self.number(track.get("stereo_width"), 0.5),
            "phase_correlation": self.number(track.get("phase_correlation"), 0.6),
            "bpm": self.number(track.get("bpm"), 0),
            "ai_source_likely": any(token in name for token in ("suno", "udio", "ai output", "generated")),
        }

    def issue_list(self, profile):

        issues = []

        if profile["ai_source_likely"]:
            issues.append(self.issue(
                "AI_SOURCE_ARTIFACTS",
                "MEDIUM",
                "AI uretimlerde transient bulanmasi, plastik tiz ve kontrolsuz low-end riski var.",
                "Stem ayirma, transient yenileme ve referans eslestirme ile kurtar."
            ))

        if profile["energy"] > 0.78 and profile["drop_strength"] < 0.18:
            issues.append(self.issue(
                "KICK_PUNCH_BLURRED",
                "HIGH",
                "Enerji yuksek ama kick vurusu yeterince ayri hissedilmiyor.",
                "Kick bandini 50-90 Hz govde, 2-5 kHz click olarak ayir; bass ile sidechain kur."
            ))

        if profile["roughness"] > 0.32 or profile["brightness"] > 0.78:
            issues.append(self.issue(
                "HARSH_TOP_END",
                "HIGH" if profile["roughness"] > 0.38 else "MEDIUM",
                "Ust-orta/tiz bolge yorucu veya dijital sertlik tasiyor.",
                "Dinamik EQ ile 2.5-5 kHz ve 8-12 kHz bolgelerini sadece sorun aninda indir."
            ))

        if profile["brightness"] < 0.34 and profile["energy"] > 0.45:
            issues.append(self.issue(
                "MUDDY_MIX",
                "MEDIUM",
                "Parca kapali duyuluyor; mid/low-mid bolgesi mix'i perdeleyebilir.",
                "180-450 Hz bolgesini temizle, presence'i sertlestirmeden ac."
            ))

        if profile["vocal_risk"] > 0.62:
            issues.append(self.issue(
                "VOCAL_MASKING",
                "MEDIUM",
                "Vokal veya lead fazla baskin; DJ mixte gecis alanini daraltabilir.",
                "Vokal bolgelerinde otomasyon ve mid-side EQ ile alan ac."
            ))

        if profile["stereo_width"] > 0.78 or profile["phase_correlation"] < 0.35:
            issues.append(self.issue(
                "MONO_COMPATIBILITY_RISK",
                "HIGH",
                "Stereo genislik mono sistemlerde low-end ve lead kaybi yaratabilir.",
                "120 Hz alti mono, yan kanalda agresif low-mid temizligi uygula."
            ))

        if profile["mixability"] < 0.48:
            issues.append(self.issue(
                "DJ_INTRO_OUTRO_WEAK",
                "MEDIUM",
                "Intro/outro DJ miks icin yeterince temiz degil.",
                "8-16 bar clean intro/outro edit hazirla; vokal ve crash kalabaligini azalt."
            ))

        return issues

    def professional_score(self, profile, issues):

        penalty = 0

        for item in issues:
            penalty += {"LOW": 5, "MEDIUM": 10, "HIGH": 17}.get(item["severity"], 8)

        base = (
            profile["danceability"] * 24 +
            profile["energy"] * 18 +
            profile["mixability"] * 18 +
            (1 - min(profile["roughness"] * 2, 1)) * 14 +
            (1 - abs(profile["brightness"] - 0.56)) * 14 +
            profile["drop_strength"] * 8 +
            (1 - profile["vocal_risk"] * 0.45) * 4
        )

        return round(max(0, min(100, base - penalty + 12)), 1)

    def urgent_fixes(self, issues):

        fixes = [
            item["repair"]
            for item in issues
            if item["severity"] == "HIGH"
        ]

        if fixes:
            return fixes

        return [
            "Gain staging'i -6 dB headroom ile baslat.",
            "Referans parca ile kick, bass, vocal ve loudness dengesini A/B kontrol et.",
        ]

    def suno_rescue_chain(self, profile, issues):

        chain = [
            "1. Kaynagi WAV/24-bit olarak al; MP3 ciktiysa once temiz kopya uret.",
            "2. Stem ayirma: drums, bass, vocal, other kanallarini ayir.",
            "3. Drums: transient shaper ile kick attack'i geri getir, clipper ile kontrollu punch ekle.",
            "4. Bass: 30 Hz altini temizle, 50-90 Hz govdeyi kick ile cakistirma.",
            "5. Other/vocal: AI pariltisini dinamik EQ ile yumusat, sibilance kontrol et.",
            "6. Mix bus: hafif glue compression, asiri limiter yok.",
            "7. Master: true peak -1.0 dBTP, hedef role gore LUFS, final A/B kontrol.",
        ]

        if any(item["code"] == "HARSH_TOP_END" for item in issues):
            chain.insert(5, "Ek: 2.5-5 kHz sertlik ve 8-12 kHz yapay parlakligi dinamik EQ ile indir.")

        if profile["role"] == "PEAK TIME":
            chain.append("8. Peak-time edit icin 16 bar clean intro ve net drop marker'i hazirla.")

        return chain

    def mix_chain(self, profile, issues):

        chain = [
            "Gain: tum kanallari clipping olmadan dengele.",
            "Sub temizlik: 25-30 Hz altinda gereksiz rumble kes.",
            "Kick/Bass: kick temel frekansi ile bass govdesini ayni yere yigma.",
            "Drum bus: transient netligi, kontrollu saturation, 1-2 dB glue.",
            "Music bus: low-mid camuru temizle; stereo genisligi mid/side ile kontrol et.",
            "Vocal/Lead: presence acarken 3-5 kHz sertligini dinamik tut.",
        ]

        if any(item["code"] == "DJ_INTRO_OUTRO_WEAK" for item in issues):
            chain.append("DJ edit: intro/outro icin kick-only veya groove-only 8/16 bar alan yarat.")

        return chain

    def mastering_chain(self, profile, score):

        target = "-8 ile -7 LUFS" if profile["role"] == "PEAK TIME" else "-10 ile -8.5 LUFS"

        return [
            "Pre-master headroom: -6 dB civari.",
            "Linear/clean EQ: buyuk hareket yok, sadece problem bolgesi.",
            "Dynamic EQ: sertlik, sibilance ve low-mid birikimini programatik kontrol et.",
            "Multiband compression: sadece low-end ve high-mid kontrolu gerekiyorsa kullan.",
            "Soft clipper: kick punch'i koruyarak algilanan ses yuksekligi ekle.",
            f"Limiter: true peak -1.0 dBTP, hedef {target}.",
            f"Final karar: profesyonel skor {score}/100; 85 altiysa tekrar mix'e don.",
        ]

    def stem_strategy(self, profile):

        return {
            "drums": "Kick attack ve snare/clap netligi oncelikli.",
            "bass": "Mono, temiz sub, kick ile ritmik bosluk.",
            "vocal": "Sibilance ve AI metalik ton kontrolu.",
            "music": "Low-mid temizlik, kontrollu stereo genislik.",
            "dj_edit": "Clean intro/outro, drop marker ve cue noktasi.",
        }

    def reference_targets(self, profile):

        return {
            "club_loudness": "-8/-7 LUFS peak-time, -10/-8.5 LUFS groove/warmup",
            "true_peak": "-1.0 dBTP",
            "low_end": "30 Hz alti temiz, 120 Hz alti mono",
            "kick_focus": "50-90 Hz govde, 2-5 kHz attack kontrolu",
            "stereo": "Mono uyumluluk kaybi yok, side low-end yok",
            "export": "WAV 24-bit master + 320 kbps DJ copy",
        }

    def doctor_note(self, score, issues):

        if score >= 85:
            return "Bu parca DJ/club mastering icin guclu; sadece kontrollu loudness ve final A/B yeterli."

        if any(item["severity"] == "HIGH" for item in issues):
            return "Master'a gecmeden once mix doktoru mudahalesi sart; limiter sorunu buyutur."

        return "Parca kurtarilabilir durumda; tonal denge ve clean DJ edit ile profesyonel seviyeye yaklasir."

    def verdict(self, score):

        if score >= 88:
            return "PRO_DJ_READY"
        if score >= 74:
            return "MASTERING_READY_WITH_FIXES"
        if score >= 58:
            return "MIX_REPAIR_REQUIRED"
        return "REBUILD_OR_STEM_RESCUE_REQUIRED"

    def issue(self, code, severity, message, repair):

        return {
            "code": code,
            "severity": severity,
            "message": message,
            "repair": repair,
        }

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
