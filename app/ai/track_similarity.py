"""Track Similarity Radar — find the most similar tracks in the library.

Uses a combination of:
- Audio feature distance (energy, brightness, danceability, roughness)
- BPM proximity
- Genre family match
- Camelot key compatibility
- Track DNA similarity

Returns ranked list of similar tracks with similarity scores.
"""

import math


class TrackSimilarityEngine:

    def __init__(self):
        pass

    def find_similar(self, target_track, library, limit=5):
        """Find the most similar tracks to the target.

        Args:
            target_track: the reference track dict
            library: list of all track dicts
            limit: max results

        Returns:
            list of track dicts with similarity_score and reason
        """
        if not target_track or not library:
            return []

        candidates = []

        for track in library:
            if track.get("id") == target_track.get("id"):
                continue

            score, reason = self._compute_similarity(target_track, track)

            if score > 0.3:
                candidates.append({
                    **track,
                    "similarity_score": round(score, 3),
                    "similarity_reason": reason,
                })

        candidates.sort(key=lambda t: t["similarity_score"], reverse=True)
        return candidates[:limit]

    def _compute_similarity(self, a, b):
        """Compute similarity between two tracks.

        Returns (score, reason_string).
        """
        # Feature distances
        energy_a = float(a.get("energy", 0.5) or 0.5)
        energy_b = float(b.get("energy", 0.5) or 0.5)
        brightness_a = float(a.get("brightness", 0.5) or 0.5)
        brightness_b = float(b.get("brightness", 0.5) or 0.5)
        dance_a = float(a.get("danceability", 0.5) or 0.5)
        dance_b = float(b.get("danceability", 0.5) or 0.5)

        # Euclidean distance in feature space (normalized 0-1)
        feature_dist = math.sqrt(
            (energy_a - energy_b) ** 2 +
            (brightness_a - brightness_b) ** 2 +
            (dance_a - dance_b) ** 2
        ) / math.sqrt(3)

        feature_score = max(0, 1 - feature_dist)

        # BPM proximity
        bpm_a = float(a.get("bpm", 0) or 0)
        bpm_b = float(b.get("bpm", 0) or 0)
        bpm_diff = abs(bpm_a - bpm_b) if bpm_a > 0 and bpm_b > 0 else 999
        bpm_score = max(0, 1 - bpm_diff / 40)

        # Genre family match
        genre_a = a.get("parent_genre", a.get("genre", ""))
        genre_b = b.get("parent_genre", b.get("genre", ""))
        genre_score = 1.0 if genre_a == genre_b and genre_a else 0.3

        # Key compatibility
        key_a = a.get("camelot", a.get("key", ""))
        key_b = b.get("camelot", b.get("key", ""))
        key_score = 0.0
        if key_a and key_b:
            from app.ui.dj_widgets import HarmonicWheel
            compatible = HarmonicWheel.COMPATIBLE_KEYS.get(key_a, [])
            key_score = 1.0 if key_b in compatible else 0.0

        # Role match
        role_a = a.get("role", "")
        role_b = b.get("role", "")
        role_score = 1.0 if role_a == role_b else 0.2

        # Weighted combination
        total = (
            feature_score * 0.35 +
            bpm_score * 0.20 +
            genre_score * 0.15 +
            key_score * 0.15 +
            role_score * 0.15
        )

        # Build reason
        reasons = []
        if feature_score > 0.7:
            reasons.append("benzer ses profili")
        if bpm_score > 0.8:
            reasons.append(f"yaklasik BPM ({bpm_b:.0f})")
        if genre_score > 0.5:
            reasons.append(f"ayni tur ({genre_b})")
        if key_score > 0.5:
            reasons.append(f"harmonik uyumlu ({key_b})")
        if role_score > 0.5:
            reasons.append(f"ayni rol ({role_b})")

        reason = " | ".join(reasons) if reasons else "genel benzerlik"

        return total, reason
