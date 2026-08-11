"""
DJ AI OS — Track Analyzer (Consolidated)

Merges: TrackDNA + TrackSimilarity + DJProfile + MFCCClassifier + MusicAI
Single class for ALL track analysis, similarity, and profiling.
"""

import math
import os
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple


class TrackAnalyzer:
    """
    Central track analysis engine.
    """

    # ============================================================
    # DNA GENERATION (from track_dna)
    # ============================================================

    def generate_dna(self, track: Dict) -> List[Tuple[str, int]]:
        """Generate a DNA barcode from track features."""
        energy = float(track.get("energy", 0.5) or 0.5)
        brightness = float(track.get("brightness", 0.5) or 0.5)
        danceability = float(track.get("danceability", 0.5) or 0.5)
        vocal_risk = float(track.get("vocal_risk", 0.2) or 0.2)
        drop = float(track.get("drop_strength", 0.3) or 0.3)
        heart = float(track.get("heart_score", 0.5) or 0.5)

        bars = []
        bars.append((self._energy_to_hue(energy), 3))
        bars.append((self._brightness_to_color(brightness), 2))
        d_color = "#00FFA3" if danceability > 0.7 else "#22D3FF" if danceability > 0.4 else "#6F7C8A"
        bars.append((d_color, 2 if danceability > 0.6 else 1))
        bars.append(("#FF3DF2" if vocal_risk > 0.5 else "#FFB020" if vocal_risk > 0.3 else "#00C896", 1))
        bars.append(("#FF4D6D" if drop > 0.6 else "#9B5CFF" if drop > 0.3 else "#3A1D78", 2 if drop > 0.5 else 1))
        bars.append(("#FF3DF2" if heart > 0.7 else "#FFB020" if heart > 0.4 else "#2979FF", 1))
        bars.append((self._energy_to_hue(energy), 2))
        return bars

    def dna_to_string(self, dna: List) -> str:
        return "|".join(f"{c}:{w}" for c, w in dna)

    def dna_similarity(self, dna_a: List, dna_b: List) -> float:
        if not dna_a or not dna_b:
            return 0.0
        matches = sum(1 for a, b in zip(dna_a, dna_b) if a == b)
        return matches / max(1, min(len(dna_a), len(dna_b)))

    # ============================================================
    # SIMILARITY (from track_similarity)
    # ============================================================

    def find_similar(self, target: Dict, library: List[Dict], limit: int = 5) -> List[Dict]:
        """Find most similar tracks using multi-feature distance."""
        if not target or not library:
            return []

        scored = []
        for track in library:
            if track.get("path") == target.get("path"):
                continue
            score, reason = self._compute_similarity(target, track)
            if score > 0.3:
                scored.append({**track, "similarity_score": round(score, 3), "similarity_reason": reason})

        scored.sort(key=lambda t: t["similarity_score"], reverse=True)
        return scored[:limit]

    def _compute_similarity(self, a: Dict, b: Dict) -> Tuple[float, str]:
        """Multi-feature similarity with weighted scoring."""
        # Feature distance
        features = ["energy", "brightness", "danceability"]
        dist = math.sqrt(sum(
            (float(a.get(f, 0.5) or 0.5) - float(b.get(f, 0.5) or 0.5)) ** 2
            for f in features
        )) / math.sqrt(len(features))
        feature_score = max(0, 1 - dist)

        # BPM
        bpm_a, bpm_b = float(a.get("bpm", 0) or 0), float(b.get("bpm", 0) or 0)
        bpm_score = max(0, 1 - abs(bpm_a - bpm_b) / 40) if bpm_a > 0 and bpm_b > 0 else 0.5

        # Genre
        g_a = a.get("parent_genre", a.get("genre", ""))
        g_b = b.get("parent_genre", b.get("genre", ""))
        genre_score = 1.0 if g_a == g_b and g_a else 0.3

        # Key
        k_a, k_b = a.get("camelot", a.get("key", "")), b.get("camelot", b.get("key", ""))
        from app.ai.library_ai import LibraryAI
        key_score = 1.0 if k_b in LibraryAI.key_compatibility(None, k_a) else 0.0

        # Role
        role_score = 1.0 if a.get("role") == b.get("role") else 0.2

        total = (feature_score * 0.35 + bpm_score * 0.20 + genre_score * 0.15 +
                 key_score * 0.15 + role_score * 0.15)

        reasons = []
        if feature_score > 0.7: reasons.append("benzer ses profili")
        if bpm_score > 0.8: reasons.append(f"yaklasik BPM ({bpm_b:.0f})")
        if genre_score > 0.5: reasons.append(f"ayni tur ({g_b})")
        if key_score > 0.5: reasons.append(f"harmonik uyumlu ({k_b})")
        if role_score > 0.5: reasons.append(f"ayni rol ({b.get('role', '')})")

        return total, " | ".join(reasons) if reasons else "genel benzerlik"

    # ============================================================
    # DJ PROFILE (from dj_profile)
    # ============================================================

    def build_profile(self, tracks: List[Dict]) -> Dict:
        """Build a comprehensive DJ profile from their library."""
        if not tracks:
            return {"dna": "E00-B00-G00-P000", "insights": ["Kutuphane bos"]}

        genres = [t.get("genre", "unknown").lower() for t in tracks]
        bpms = [float(t.get("bpm", 0) or 0) for t in tracks if t.get("bpm")]
        energies = [float(t.get("energy", 0.5) or 0.5) for t in tracks]
        roles = [t.get("role", "UNKNOWN") for t in tracks]

        genre_counts = Counter(genres)
        role_counts = Counter(roles)

        dominant_genre = genre_counts.most_common(1)[0][0] if genre_counts else "unknown"
        avg_bpm = sum(bpms) / len(bpms) if bpms else 0
        avg_energy = sum(energies) / len(energies) if energies else 0

        # Energy level classification
        e_level = "E00"
        if avg_energy > 0.7: e_level = "E03"
        elif avg_energy > 0.55: e_level = "E02"
        elif avg_energy > 0.4: e_level = "E01"

        # BPM level
        b_level = "B00"
        if avg_bpm > 130: b_level = "B03"
        elif avg_bpm > 122: b_level = "B02"
        elif avg_bpm > 115: b_level = "B01"

        # Genre diversity
        g_count = len(set(genres))
        g_level = f"G{min(9, g_count):02d}"

        # Peak-time ratio
        peak_count = role_counts.get("PEAK TIME", 0)
        peak_ratio = peak_count / max(1, len(roles))
        p_level = "P000"
        if peak_ratio > 0.5: p_level = "P003"
        elif peak_ratio > 0.3: p_level = "P002"
        elif peak_ratio > 0.15: p_level = "P001"

        dna = f"{e_level}-{b_level}-{g_level}-{p_level}"

        insights = []
        if avg_bpm > 128:
            insights.append(f"Yuksek tempo DJ: ortalama {avg_bpm:.0f} BPM")
        elif avg_bpm < 115:
            insights.append(f"Yavas groove DJ: ortalama {avg_bpm:.0f} BPM")
        if g_count > 5:
            insights.append(f"Genis tur yelpazesi: {g_count} farkli tur")
        if peak_ratio > 0.5:
            insights.append("Agirliklilik peak-time parcalarinda")
        if not insights:
            insights.append("Dengeli bir kütüphane profili")

        return {
            "dna": dna,
            "dominant_genre": dominant_genre,
            "genre_count": g_count,
            "avg_bpm": round(avg_bpm, 1),
            "avg_energy": round(avg_energy, 3),
            "track_count": len(tracks),
            "insights": insights,
        }

    # ============================================================
    # GENRE CLASSIFICATION (from mfcc_classifier)
    # ============================================================

    def classify_genre_heuristic(self, track: Dict) -> str:
        """Rule-based genre classification (no ML needed)."""
        bpm = float(track.get("bpm", 0) or 0)
        energy = float(track.get("energy", 0.5) or 0.5)
        brightness = float(track.get("brightness", 0.5) or 0.5)
        danceability = float(track.get("danceability", 0.5) or 0.5)
        vocal_risk = float(track.get("vocal_risk", 0.2) or 0.2)

        if bpm >= 170:
            return "drum_and_bass"
        if bpm >= 140 and energy > 0.7:
            return "techno"
        if 122 <= bpm <= 130 and danceability > 0.6:
            return "house"
        if 118 <= bpm <= 126 and energy < 0.55:
            return "deep_house"
        if bpm >= 120 and brightness > 0.6:
            return "melodic_house"
        if bpm <= 100 and vocal_risk > 0.5:
            return "hip_hop"
        if 85 <= bpm <= 106:
            return "reggaeton"

        return "house"  # Default

    # ============================================================
    # TRACK CLEANING (from music_ai)
    # ============================================================

    def clean_tracks(self, raw_tracks: List[Dict]) -> List[Dict]:
        """Clean and normalize track data."""
        cleaned = []
        for track in raw_tracks:
            clean = {
                "path": track.get("path", ""),
                "name": track.get("name", os.path.basename(track.get("path", "UNKNOWN"))),
                "artist": track.get("artist", "UNKNOWN"),
                "genre": str(track.get("genre", "UNKNOWN")).strip(),
                "bpm": self._safe_float(track.get("bpm"), 0),
                "energy": self._safe_float(track.get("energy"), 0.5),
                "brightness": self._safe_float(track.get("brightness"), 0.5),
                "danceability": self._safe_float(track.get("danceability"), 0.5),
                "duration": self._safe_float(track.get("duration"), 0),
                "bitrate": self._safe_int(track.get("bitrate"), 0),
                "id": track.get("path", track.get("id", "")),
            }
            clean["role"] = self._assign_role(clean)
            cleaned.append(clean)
        return cleaned

    def _assign_role(self, track: Dict) -> str:
        """Assign role based on features."""
        energy = track.get("energy", 0.5)
        duration = track.get("duration", 0)
        if energy > 0.75:
            return "PEAK TIME"
        if energy > 0.55:
            return "GROOVE"
        if energy < 0.35:
            return "WARMUP"
        if duration > 400:
            return "EXTENDED"
        return "UTILITY"

    # ============================================================
    # HELPERS
    # ============================================================

    def _energy_to_hue(self, energy):
        if energy > 0.8: return "#FF3DF2"
        if energy > 0.6: return "#9B5CFF"
        if energy > 0.4: return "#00FFA3"
        if energy > 0.2: return "#22D3FF"
        return "#6F7C8A"

    def _brightness_to_color(self, brightness):
        if brightness > 0.7: return "#EAF2FF"
        if brightness > 0.5: return "#22D3FF"
        if brightness > 0.3: return "#9B5CFF"
        return "#0D1020"

    def _safe_float(self, value, default=0):
        try: return float(value)
        except: return default

    def _safe_int(self, value, default=0):
        try: return int(value)
        except: return default
