"""DJ Coach AI — post-set analysis and coaching.

Analyzes a completed or in-progress set and provides:
- Energy arc assessment (peaked too early? flat ending?)
- BPM flow analysis (monotony, jumps)
- Harmonic consistency (key jumps that killed flow)
- Role distribution (too many PEAK TIME? not enough WARMUP?)
- Specific actionable advice for the next set
"""


class DJCoach:

    def __init__(self):
        pass

    def analyze_set(self, tracks, venue="CLUB", hours=4):
        """Full set analysis with coaching feedback.

        Args:
            tracks: ordered list of played/queued tracks
            venue: "CLUB", "WEDDING", "FESTIVAL", "LOUNGE"
            hours: planned set duration

        Returns:
            dict with scores, issues, and coaching messages
        """
        if not tracks or len(tracks) < 2:
            return {
                "grade": "N/A",
                "message": "Yeterli parca yok. En az 2 parca gerekli.",
                "scores": {},
                "issues": [],
                "coaching": [],
            }

        scores = {}
        issues = []
        coaching = []

        # 1. Energy arc analysis
        energy_result = self._analyze_energy_arc(tracks, venue)
        scores["energy"] = energy_result["score"]
        issues.extend(energy_result["issues"])
        coaching.extend(energy_result["coaching"])

        # 2. BPM flow analysis
        bpm_result = self._analyze_bpm_flow(tracks)
        scores["bpm_flow"] = bpm_result["score"]
        issues.extend(bpm_result["issues"])
        coaching.extend(bpm_result["coaching"])

        # 3. Harmonic consistency
        harmonic_result = self._analyze_harmonic_flow(tracks)
        scores["harmonic"] = harmonic_result["score"]
        issues.extend(harmonic_result["issues"])
        coaching.extend(harmonic_result["coaching"])

        # 4. Role distribution
        role_result = self._analyze_role_distribution(tracks, venue)
        scores["roles"] = role_result["score"]
        issues.extend(role_result["issues"])
        coaching.extend(role_result["coaching"])

        # 5. Variety score
        variety_result = self._analyze_variety(tracks)
        scores["variety"] = variety_result["score"]
        issues.extend(variety_result["issues"])
        coaching.extend(variety_result["coaching"])

        # Overall grade
        avg_score = sum(scores.values()) / max(1, len(scores))
        grade = self._grade(avg_score)

        # Final coaching summary
        summary = self._build_summary(grade, scores, issues, venue, len(tracks))

        return {
            "grade": grade,
            "avg_score": round(avg_score, 2),
            "scores": scores,
            "issues": issues,
            "coaching": coaching,
            "summary": summary,
            "track_count": len(tracks),
        }

    def _analyze_energy_arc(self, tracks, venue):
        energies = [float(t.get("energy", 0.5) or 0.5) for t in tracks]
        n = len(energies)
        issues = []
        coaching = []

        # Ideal arc: low→medium→high→medium→low
        peak_position = energies.index(max(energies)) if energies else 0
        peak_pct = peak_position / max(1, n - 1)

        if peak_pct < 0.3:
            issues.append("EARLY_PEAK")
            coaching.append(
                "ERKEN ZIRVE: Enerji cok erken dustu (%"
                f"{peak_pct*100:.0f}). Setin ortasina dogru zirveyi kaydir."
            )
        elif peak_pct > 0.85:
            issues.append("LATE_PEAK")
            coaching.append(
                "GEC ZIRVE: Setin sonuna kadar enerji yukselmedi. "
                "Kulup seti icin daha erken zirveye ulas."
            )

        # Check for flat energy
        if max(energies) - min(energies) < 0.15:
            issues.append("FLAT_ENERGY")
            coaching.append(
                "DUZ ENERJI: Set boyunca enerji degisimi cok az. "
                "Daha belirgin sicak/soguk dalgalanmalar ekle."
            )

        # Venue-specific
        if venue == "WEDDING":
            if any(e > 0.85 for e in energies):
                coaching.append(
                    "DUGUN: Cok yuksek enerji parcalari var. "
                    "Dugun icin 0.7 ustune cikma."
                )

        score = 1.0
        for issue in issues:
            if issue == "EARLY_PEAK":
                score -= 0.3
            elif issue == "LATE_PEAK":
                score -= 0.2
            elif issue == "FLAT_ENERGY":
                score -= 0.25

        return {"score": max(0, score), "issues": issues, "coaching": coaching}

    def _analyze_bpm_flow(self, tracks):
        bpms = [float(t.get("bpm", 0) or 0) for t in tracks if t.get("bpm")]
        issues = []
        coaching = []

        if len(bpms) < 2:
            return {"score": 1.0, "issues": [], "coaching": []}

        # Check for monotony (same BPM for too long)
        consecutive_same = 1
        max_consecutive = 1
        for i in range(1, len(bpms)):
            if abs(bpms[i] - bpms[i-1]) < 2:
                consecutive_same += 1
                max_consecutive = max(max_consecutive, consecutive_same)
            else:
                consecutive_same = 1

        if max_consecutive > 6:
            issues.append("BPM_MONOTONY")
            coaching.append(
                f"BPM TEKDUZELIGI: {max_consecutive} parca arka arkaya ayni BPM'de. "
                "BPM cesitliligi veya daha belirgin gecisler ekle."
            )

        # Check for jarring jumps
        for i in range(1, len(bpms)):
            diff = abs(bpms[i] - bpms[i-1])
            if diff > 10:
                issues.append("BPM_JUMP")
                coaching.append(
                    f"BPM ATLAMASI: {bpms[i-1]:.0f} -> {bpms[i]:.0f} "
                    f"(fark: {diff:.0f}). Cok sert gecis."
                )
                break

        score = 1.0
        if "BPM_MONOTONY" in issues:
            score -= 0.2
        if "BPM_JUMP" in issues:
            score -= 0.3

        return {"score": max(0, score), "issues": issues, "coaching": coaching}

    def _analyze_harmonic_flow(self, tracks):
        keys = [t.get("camelot", t.get("key", "")) for t in tracks]
        keys = [k for k in keys if k]
        issues = []
        coaching = []

        if len(keys) < 2:
            return {"score": 1.0, "issues": [], "coaching": []}

        jumps = 0
        for i in range(1, len(keys)):
            from app.ui.dj_widgets import HarmonicWheel
            compatible = HarmonicWheel.COMPATIBLE_KEYS.get(keys[i-1], [])
            if keys[i] not in compatible:
                jumps += 1

        jump_pct = jumps / max(1, len(keys) - 1)

        if jump_pct > 0.4:
            issues.append("HARMONIC_CHAOS")
            coaching.append(
                f"HARMONIK KARISIKLIK: %{jump_pct*100:.0f} geciste uyumsuzluk. "
                "Camelot carkina uyumlu parcalar sec."
            )
        elif jump_pct > 0.2:
            coaching.append(
                f"Uyari: %{jump_pct*100:.0f} geciste harmonik uyumsuzluk var. "
                "Birkac uyumlu parca ekle."
            )

        score = max(0, 1 - jump_pct * 1.5)

        return {"score": score, "issues": issues, "coaching": coaching}

    def _analyze_role_distribution(self, tracks, venue):
        roles = [t.get("role", "UNKNOWN") for t in tracks]
        issues = []
        coaching = []

        role_counts = {}
        for r in roles:
            role_counts[r] = role_counts.get(r, 0) + 1

        total = len(roles)
        peak_pct = role_counts.get("PEAK TIME", 0) / max(1, total)
        warmup_pct = role_counts.get("WARMUP", 0) / max(1, total)

        if peak_pct > 0.5:
            issues.append("PEAK_HEAVY")
            coaching.append(
                f"PEAK YUKSEK: Parcalarin %{peak_pct*100:.0f}'u PEAK TIME. "
                "Daha fazla GROOVE ve WARMUP ekle."
            )

        if warmup_pct > 0.5 and venue in ("CLUB", "FESTIVAL"):
            issues.append("WARMUP_HEAVY")
            coaching.append(
                "CAZIP ISITMA: Setin yarisi warmup. "
                "Daha fazla groove ve peak parca ekle."
            )

        score = 1.0
        if "PEAK_HEAVY" in issues:
            score -= 0.25
        if "WARMUP_HEAVY" in issues:
            score -= 0.2

        return {"score": max(0, score), "issues": issues, "coaching": coaching}

    def _analyze_variety(self, tracks):
        genres = set(t.get("genre", "") for t in tracks)
        issues = []
        coaching = []

        if len(genres) <= 1 and len(tracks) > 5:
            issues.append("GENRE_MONO")
            coaching.append(
                "TEK TURLULUK: Tum parcalar ayni turden. "
                "Cesitlilik icin alt-turler veya farkli aile ekle."
            )

        score = min(1.0, len(genres) / max(1, len(tracks) * 0.3))

        return {"score": score, "issues": issues, "coaching": coaching}

    def _grade(self, score):
        if score >= 0.85:
            return "S"
        if score >= 0.75:
            return "A"
        if score >= 0.65:
            return "B"
        if score >= 0.50:
            return "C"
        return "D"

    def _build_summary(self, grade, scores, issues, venue, track_count):
        best = max(scores, key=scores.get) if scores else "none"
        worst = min(scores, key=scores.get) if scores else "none"

        return (
            f"Set degerlendirmesi: {grade} | "
            f"{track_count} parca | "
            f"En guclu: {best} ({scores.get(best, 0):.0%}) | "
            f"Gelistirme alani: {worst} ({scores.get(worst, 0):.0%}) | "
            f"{len(issues)} sorun tespit edildi"
        )
