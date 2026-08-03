"""DJ Profile / Style DNA — aggregate analysis of a DJ's library and sets.

Analyzes the entire library or past sets to create a "DJ profile":
- Genre distribution (what genres dominate)
- Energy preference (low/mid/high energy ratio)
- BPM range (typical BPM, min, max)
- Harmonic style (which Camelot keys are most used)
- Role distribution (how much warmup vs peak)
- Mood distribution
- "DJ DNA" — a unique fingerprint of the DJ's style
"""


class DJProfile:

    def __init__(self):
        pass

    def build_profile(self, tracks):
        """Build a comprehensive DJ profile from tracks.

        Args:
            tracks: list of track dicts (library or set)

        Returns:
            dict with profile stats, DNA, and insights
        """
        if not tracks:
            return self._empty_profile()

        n = len(tracks)

        # Genre distribution
        genre_counts = {}
        for t in tracks:
            g = t.get("parent_genre", t.get("genre", "UNKNOWN"))
            genre_counts[g] = genre_counts.get(g, 0) + 1
        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)

        # Energy distribution
        energies = [float(t.get("energy", 0.5) or 0.5) for t in tracks]
        avg_energy = sum(energies) / max(1, n)
        low_energy = sum(1 for e in energies if e < 0.4) / max(1, n)
        mid_energy = sum(1 for e in energies if 0.4 <= e < 0.7) / max(1, n)
        high_energy = sum(1 for e in energies if e >= 0.7) / max(1, n)

        # BPM distribution
        bpms = [float(t.get("bpm", 0) or 0) for t in tracks if t.get("bpm")]
        avg_bpm = sum(bpms) / max(1, len(bpms)) if bpms else 0
        min_bpm = min(bpms) if bpms else 0
        max_bpm = max(bpms) if bpms else 0

        # Key distribution
        key_counts = {}
        for t in tracks:
            k = t.get("camelot", t.get("key", ""))
            if k:
                key_counts[k] = key_counts.get(k, 0) + 1
        top_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Role distribution
        role_counts = {}
        for t in tracks:
            r = t.get("role", "UNKNOWN")
            role_counts[r] = role_counts.get(r, 0) + 1

        # Mood distribution
        mood_counts = {}
        for t in tracks:
            m = t.get("emotional_color", t.get("mood", "UNKNOWN"))
            if m:
                mood_counts[m] = mood_counts.get(m, 0) + 1
        top_moods = sorted(mood_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Quality distribution
        quality_counts = {}
        for t in tracks:
            q = t.get("quality", "UNKNOWN")
            quality_counts[q] = quality_counts.get(q, 0) + 1

        # AI Ear average
        ear_scores = [float(t.get("ai_ear_score", 0) or 0) for t in tracks if t.get("ai_ear_score")]
        avg_ear = sum(ear_scores) / max(1, len(ear_scores)) if ear_scores else 0

        # Build DNA fingerprint
        dna = self._build_dna(
            avg_energy, avg_bpm, top_genres, top_keys, role_counts, n
        )

        # Insights
        insights = self._generate_insights(
            top_genres, avg_energy, avg_bpm, role_counts, high_energy, low_energy
        )

        return {
            "track_count": n,
            "top_genres": top_genres[:5],
            "genre_count": len(genre_counts),
            "avg_energy": round(avg_energy, 2),
            "energy_distribution": {
                "low": round(low_energy, 2),
                "mid": round(mid_energy, 2),
                "high": round(high_energy, 2),
            },
            "avg_bpm": round(avg_bpm, 1),
            "bpm_range": f"{min_bpm:.0f}-{max_bpm:.0f}",
            "top_keys": top_keys,
            "role_distribution": role_counts,
            "top_moods": top_moods,
            "quality_distribution": quality_counts,
            "avg_ear_score": round(avg_ear, 2),
            "dna": dna,
            "insights": insights,
        }

    def _build_dna(self, avg_energy, avg_bpm, top_genres, top_keys, role_counts, n):
        """Build a compact DJ DNA fingerprint."""
        # Normalize values
        energy_norm = int(avg_energy * 10)  # 0-10
        bpm_norm = int((avg_bpm - 60) / 12) if avg_bpm > 60 else 0  # 0-10
        genre_norm = len(top_genres)  # diversity
        peak_ratio = role_counts.get("PEAK TIME", 0) / max(1, n)

        # DNA string: energy-bpm-genrediv-peakratio
        return f"E{energy_norm:02d}-B{bpm_norm:02d}-G{genre_norm:02d}-P{int(peak_ratio*100):03d}"

    def _generate_insights(self, top_genres, avg_energy, avg_bpm, role_counts, high_pct, low_pct):
        """Generate actionable insights from the profile."""
        insights = []

        if top_genres:
            dominant = top_genres[0]
            if dominant[1] > len(top_genres) * 2:
                insights.append(
                    f"ONE DOMINANT GENRE: {dominant[0]} kutuphanenin buyuk bolumunu olusturuyor. "
                    "Cesitlilik icin farkli alt-turler deneyebilirsin."
                )

        if high_pct > 0.6:
            insights.append(
                "HIGH ENERGY BIAS: Kutuphanenin %60'indan fazlasi yuksek enerjili. "
                "Soguma ve warmup parcalari eklemeyi dusun."
            )

        if low_pct > 0.5:
            insights.append(
                "LOW ENERGY BIAS: Kutuphanenin yarisi dusuk enerjili. "
                "Peak time parcalarini guclendirmeyi dusun."
            )

        if avg_bpm > 130:
            insights.append(
                f"FAST DJ: Ortalama BPM {avg_bpm:.0f}. Techno/bass agirlikli bir stilin var."
            )
        elif avg_bpm < 115:
            insights.append(
                f"SLOW DJ: Ortalama BPM {avg_bpm:.0f}. Hip-hop/lounge agirlikli bir stilin var."
            )

        peak = role_counts.get("PEAK TIME", 0)
        warmup = role_counts.get("WARMUP", 0) + role_counts.get("OPENING", 0)
        total = sum(role_counts.values())

        if total > 0 and peak / total > 0.5:
            insights.append(
                "PEAK HEAVY: Parcalarin yarisi PEAK TIME. Set icin daha fazla gecis parcasi ekle."
            )

        if not insights:
            insights.append("Dengeli bir kutuphane! Cesitli enerji seviyeleri ve turler mevcut.")

        return insights

    def _empty_profile(self):
        return {
            "track_count": 0,
            "dna": "E00-B00-G00-P000",
            "insights": ["Kutuphane bos."],
        }
