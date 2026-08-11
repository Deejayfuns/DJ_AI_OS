"""
DJ AI OS — Smart Library Intelligence

Semantic understanding of music library:
- Mood mapping (energetic, chill, dark, euphoric, groovy)
- Key compatibility graph (Camelot wheel)
- Energy flow optimization for DJ sets
- Library health scoring
- Gap analysis & recommendations

Usage:
    ai = LibraryAI(library_tracks)
    mood_map = ai.mood_map()
    flow = ai.optimize_flow(tracks, style="ENERGY_RISE", duration_hours=4)
    health = ai.health_report()
"""

import math
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Tuple

# ============================================================
# CAMELOT WHEEL
# ============================================================
CAMELOT_ORDER = [
    "1A", "8A", "3A", "10A", "5A", "12A", "7A", "2A", "9A", "4A", "11A", "6A",
    "1B", "8B", "3B", "10B", "5B", "12B", "7B", "2B", "9B", "4B", "11B", "6B",
]

CAMELOT_COMPAT = {
    "1A": ["1A", "2A", "12A", "1B"],
    "2A": ["2A", "1A", "3A", "2B"],
    "3A": ["3A", "2A", "4A", "3B"],
    "4A": ["4A", "3A", "5A", "4B"],
    "5A": ["5A", "4A", "6A", "5B"],
    "6A": ["6A", "5A", "7A", "6B"],
    "7A": ["7A", "6A", "8A", "7B"],
    "8A": ["8A", "7A", "9A", "8B"],
    "9A": ["9A", "8A", "10A", "9B"],
    "10A": ["10A", "9A", "11A", "10B"],
    "11A": ["11A", "10A", "12A", "11B"],
    "12A": ["12A", "11A", "1A", "12B"],
    "1B": ["1B", "2B", "12B", "1A"],
    "2B": ["2B", "1B", "3B", "2A"],
    "3B": ["3B", "2B", "4B", "3A"],
    "4B": ["4B", "3B", "5B", "4A"],
    "5B": ["5B", "4B", "6B", "5A"],
    "6B": ["6B", "5B", "7B", "6A"],
    "7B": ["7B", "6B", "8B", "7A"],
    "8B": ["8B", "7B", "9B", "8A"],
    "9B": ["9B", "8B", "10B", "9A"],
    "10B": ["10B", "9B", "11B", "10A"],
    "11B": ["11B", "10B", "12B", "11A"],
    "12B": ["12B", "11B", "1B", "12A"],
}


# ============================================================
# MOOD CLASSIFIER
# ============================================================

def classify_mood(track):
    """Classify track mood from BPM, energy, genre, key."""
    bpm = float(track.get("bpm", 0) or 0)
    energy = float(track.get("energy", 0.5) or 0.5)
    genre = str(track.get("genre", "")).lower()
    brightness = float(track.get("brightness", 0.5) or 0.5)
    danceability = float(track.get("danceability", 0.5) or 0.5)

    scores = {
        "energetic": 0.0,
        "chill": 0.0,
        "dark": 0.0,
        "euphoric": 0.0,
        "groovy": 0.0,
        "aggressive": 0.0,
        "atmospheric": 0.0,
    }

    # BPM influence
    if bpm >= 130:
        scores["energetic"] += 0.3
        scores["aggressive"] += 0.15
    elif bpm >= 122:
        scores["groovy"] += 0.25
        scores["energetic"] += 0.15
    elif bpm >= 115:
        scores["chill"] += 0.2
        scores["groovy"] += 0.15
    else:
        scores["chill"] += 0.3
        scores["atmospheric"] += 0.15

    # Energy influence
    if energy > 0.75:
        scores["energetic"] += 0.25
        scores["aggressive"] += 0.1
    elif energy > 0.55:
        scores["groovy"] += 0.2
    elif energy > 0.35:
        scores["chill"] += 0.15
    else:
        scores["atmospheric"] += 0.25

    # Brightness influence
    if brightness > 0.7:
        scores["euphoric"] += 0.2
    elif brightness < 0.35:
        scores["dark"] += 0.25

    # Genre influence
    genre_moods = {
        "techno": ["dark", "aggressive"],
        "house": ["groovy", "energetic"],
        "afro": ["groovy", "chill"],
        "melodic": ["euphoric", "atmospheric"],
        "d&b": ["aggressive", "energetic"],
        "trap": ["aggressive", "dark"],
        "ambient": ["atmospheric", "chill"],
    }
    for keyword, moods in genre_moods.items():
        if keyword in genre:
            for mood in moods:
                scores[mood] += 0.15

    # Danceability influence
    if danceability > 0.7:
        scores["groovy"] += 0.15

    # Return top mood
    best_mood = max(scores, key=scores.get)
    return best_mood


# ============================================================
# LIBRARY AI
# ============================================================

class LibraryAI:
    """
    Smart library intelligence for professional DJs.
    """

    def __init__(self, tracks: List[Dict[str, Any]]):
        self.tracks = tracks or []
        self._mood_cache = None
        self._health_cache = None

    def mood_map(self) -> Dict[str, str]:
        """Classify every track's mood. Returns {track_id: mood}."""
        if self._mood_cache:
            return self._mood_cache

        mood_map = {}
        for track in self.tracks:
            tid = track.get("id", track.get("path", ""))
            mood_map[tid] = classify_mood(track)

        self._mood_cache = mood_map
        return mood_map

    def mood_distribution(self) -> Dict[str, int]:
        """Count tracks per mood."""
        mood_map = self.mood_map()
        return dict(Counter(mood_map.values()))

    def key_compatibility(self, camelot_key: str) -> List[str]:
        """Return compatible Camelot keys for mixing."""
        return CAMELOT_COMPAT.get(camelot_key, [])

    def get_compatible_tracks(self, reference_track: Dict, max_results: int = 10) -> List[Dict]:
        """Find tracks compatible with reference track for mixing."""
        ref_key = reference_track.get("camelot", reference_track.get("key", ""))
        ref_bpm = float(reference_track.get("bpm", 0) or 0)

        compatible_keys = set(self.key_compatibility(ref_key))

        scored = []
        for track in self.tracks:
            if track.get("path") == reference_track.get("path"):
                continue

            t_key = track.get("camelot", track.get("key", ""))
            t_bpm = float(track.get("bpm", 0) or 0)

            # Key compatibility score
            key_score = 1.0 if t_key in compatible_keys else 0.3

            # BPM proximity score (within 5% = perfect)
            if ref_bpm > 0 and t_bpm > 0:
                bpm_diff = abs(t_bpm - ref_bpm) / ref_bpm
                bpm_score = max(0, 1.0 - bpm_diff * 10)
            else:
                bpm_score = 0.5

            total = (key_score * 0.6) + (bpm_score * 0.4)
            scored.append((total, track))

        scored.sort(key=lambda x: -x[0])
        return [track for _, track in scored[:max_results]]

    def optimize_flow(self, tracks: List[Dict], style: str = "ENERGY_RISE",
                      duration_hours: float = 4) -> List[Dict]:
        """
        Optimize track ordering for a DJ set.

        Styles:
        - ENERGY_RISE: starts low, builds to peak, then cools down
        - SUSTAINED: keeps high energy throughout
        - WAVE: alternating energy peaks and valleys
        - SUNRISE: very gradual build over the set
        """
        if not tracks:
            return []

        # Score each track
        scored = []
        for i, track in enumerate(tracks):
            bpm = float(track.get("bpm", 0) or 0)
            energy = float(track.get("energy", 0.5) or 0.5)
            mood = classify_mood(track)

            scored.append({
                "track": track,
                "bpm": bpm,
                "energy": energy,
                "mood": mood,
                "original_index": i,
            })

        # Sort by energy for flow optimization
        if style == "ENERGY_RISE":
            return self._build_energy_rise(scored, duration_hours)
        elif style == "SUSTAINED":
            return self._build_sustained(scored, duration_hours)
        elif style == "WAVE":
            return self._build_wave(scored, duration_hours)
        elif style == "SUNRISE":
            return self._build_sunrise(scored, duration_hours)
        else:
            return [s["track"] for s in sorted(scored, key=lambda x: x["bpm"])]

    def _build_energy_rise(self, scored, duration_hours):
        """Energy rises then falls: warmup → build → peak → cooldown."""
        target_count = min(len(scored), int(duration_hours * 12))

        # Sort by energy
        by_energy = sorted(scored, key=lambda x: x["energy"])

        warmup = by_energy[:target_count // 4]
        build = by_energy[target_count // 4:target_count // 2]
        peak = by_energy[target_count // 2:3 * target_count // 4]
        cooldown = by_energy[3 * target_count // 4:]

        ordered = warmup + build + peak + cooldown
        return [s["track"] for s in ordered[:target_count]]

    def _build_sustained(self, scored, duration_hours):
        """Keep energy high throughout."""
        target_count = min(len(scored), int(duration_hours * 12))
        by_energy = sorted(scored, key=lambda x: -x["energy"])
        return [s["track"] for s in by_energy[:target_count]]

    def _build_wave(self, scored, duration_hours):
        """Alternating energy peaks and valleys."""
        target_count = min(len(scored), int(duration_hours * 12))
        by_energy = sorted(scored, key=lambda x: x["energy"])

        result = []
        half = len(by_energy) // 2
        low = by_energy[:half]
        high = by_energy[half:]

        while len(result) < target_count and (low or high):
            if high:
                result.append(high.pop(0))
            if low:
                result.append(low.pop(0))

        return [s["track"] for s in result[:target_count]]

    def _build_sunrise(self, scored, duration_hours):
        """Very gradual build."""
        return self._build_energy_rise(scored, duration_hours)

    def find_gaps(self) -> List[str]:
        """Find what's missing from the library."""
        suggestions = []

        # Genre coverage
        genres = [t.get("genre", "unknown").lower() for t in self.tracks]
        genre_counts = Counter(genres)

        core_genres = {
            "house", "techno", "hip hop", "r&b", "pop", "disco",
            "afro", "reggaeton", "d&b", "trance", "ambient",
        }
        found = set(genres)
        missing_genres = core_genres - found
        if missing_genres:
            suggestions.append(f"Missing genres: {', '.join(sorted(missing_genres)[:5])}")

        # BPM coverage
        bpms = [float(t.get("bpm", 0) or 0) for t in self.tracks if t.get("bpm")]
        if bpms:
            bpm_range = max(bpms) - min(bpms)
            if bpm_range < 40:
                suggestions.append(f"Narrow BPM range ({min(bpms):.0f}-{max(bpms):.0f}). Consider adding tracks from 100-150 BPM range.")

        # Key coverage
        keys = [t.get("camelot", t.get("key", "")) for t in self.tracks if t.get("camelot") or t.get("key")]
        unique_keys = set(keys)
        if len(unique_keys) < 12:
            missing_keys = set(CAMELOT_ORDER[:12]) - unique_keys
            if missing_keys:
                suggestions.append(f"Missing Camelot keys: {', '.join(sorted(missing_keys)[:5])}")

        # Energy coverage
        energies = [float(t.get("energy", 0.5) or 0.5) for t in self.tracks]
        if energies:
            if max(energies) < 0.7:
                suggestions.append("No high-energy tracks (>0.7). Add peak-time tracks.")
            if min(energies) > 0.4:
                suggestions.append("No chill/warmup tracks (<0.4). Add low-energy tracks for set openings.")

        if not suggestions:
            suggestions.append("Library looks well-balanced!")

        return suggestions

    def health_report(self) -> Dict[str, Any]:
        """Comprehensive library health score."""
        if self._health_cache:
            return self._health_cache

        total = len(self.tracks)
        if total == 0:
            return {"total": 0, "score": 0, "issues": ["Library is empty"]}

        # Genre diversity
        genres = set(t.get("genre", "").lower() for t in self.tracks if t.get("genre"))
        genre_score = min(100, len(genres) * 10)

        # Key diversity
        keys = set(t.get("camelot", t.get("key", "")) for t in self.tracks if t.get("camelot") or t.get("key"))
        key_score = min(100, int(len(keys) / 24 * 100))

        # BPM spread
        bpms = [float(t.get("bpm", 0) or 0) for t in self.tracks if t.get("bpm")]
        bpm_score = 50
        if bpms:
            spread = max(bpms) - min(bpms)
            bpm_score = min(100, int(spread / 80 * 100))

        # Energy distribution
        energies = [float(t.get("energy", 0.5) or 0.5) for t in self.tracks]
        energy_score = 50
        if energies:
            e_range = max(energies) - min(energies)
            energy_score = min(100, int(e_range / 0.8 * 100))

        # Mood coverage
        mood_map = self.mood_map()
        unique_moods = len(set(mood_map.values()))
        mood_score = min(100, unique_moods * 18)

        # Quality indicators
        has_bitrate = sum(1 for t in self.tracks if t.get("bitrate", 0) > 0)
        quality_score = min(100, int(has_bitrate / max(1, total) * 100))

        # Overall score (weighted average)
        overall = int(
            genre_score * 0.2 +
            key_score * 0.2 +
            bpm_score * 0.15 +
            energy_score * 0.15 +
            mood_score * 0.15 +
            quality_score * 0.15
        )

        report = {
            "total": total,
            "score": overall,
            "genre_diversity": genre_score,
            "key_diversity": key_score,
            "bpm_spread": bpm_score,
            "energy_distribution": energy_score,
            "mood_coverage": mood_score,
            "quality": quality_score,
            "unique_genres": len(genres),
            "unique_keys": len(keys),
            "bpm_range": f"{min(bpms):.0f}-{max(bpms):.0f}" if bpms else "N/A",
            "mood_distribution": self.mood_distribution(),
            "issues": self.find_gaps(),
        }

        self._health_cache = report
        return report

    def suggest_set_opening(self, style: str = "house") -> List[Dict]:
        """Suggest good opening tracks for a set."""
        style_keywords = {
            "house": ("groovy", "chill"),
            "techno": ("dark", "atmospheric"),
            "melodic": ("euphoric", "atmospheric"),
            "peak": ("aggressive", "energetic"),
        }

        target_moods = style_keywords.get(style, ("chill", "groovy"))

        candidates = []
        for track in self.tracks:
            mood = classify_mood(track)
            energy = float(track.get("energy", 0.5) or 0.5)

            if mood in target_moods and energy < 0.6:
                candidates.append(track)

        # Sort by energy (lowest first for opening)
        candidates.sort(key=lambda t: float(t.get("energy", 0.5) or 0.5))

        return candidates[:10]

    def find_similar(self, reference_track: Dict, max_results: int = 10) -> List[Dict]:
        """Find tracks similar to reference (simple feature matching)."""
        ref_genre = reference_track.get("genre", "").lower()
        ref_energy = float(reference_track.get("energy", 0.5) or 0.5)
        ref_bpm = float(reference_track.get("bpm", 0) or 0)
        ref_key = reference_track.get("camelot", reference_track.get("key", ""))

        scored = []
        for track in self.tracks:
            if track.get("path") == reference_track.get("path"):
                continue

            t_genre = track.get("genre", "").lower()
            t_energy = float(track.get("energy", 0.5) or 0.5)
            t_bpm = float(track.get("bpm", 0) or 0)
            t_key = track.get("camelot", track.get("key", ""))

            genre_sim = 0.3 if t_genre == ref_genre else 0.0
            energy_sim = 1.0 - abs(ref_energy - t_energy)
            bpm_sim = 1.0 - min(1.0, abs(ref_bpm - t_bpm) / 40) if ref_bpm > 0 else 0.5
            key_sim = 0.3 if t_key in self.key_compatibility(ref_key) else 0.0

            total = genre_sim + energy_sim * 0.3 + bpm_sim * 0.3 + key_sim
            scored.append((total, track))

        scored.sort(key=lambda x: -x[0])
        return [track for _, track in scored[:max_results]]
