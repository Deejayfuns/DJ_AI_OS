"""
DJ AI OS — Set Flow AI

ML-based set optimization:
- Energy flow prediction
- Transition scoring
- Crowd energy modeling
- Set structure analysis

Uses real audio features, not just BPM/genre matching.
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple


class SetFlowAI:
    """
    AI-powered set flow optimization.
    Thinks like a real DJ: energy, harmony, timing.
    """

    # Set structure templates (bars)
    STRUCTURES = {
        "classic": {
            "warmup": 0.20,    # 20% of set
            "build": 0.25,
            "peak": 0.30,
            "cooldown": 0.25,
        },
        "peak_first": {
            "peak": 0.40,
            "groove": 0.35,
            "cooldown": 0.25,
        },
        "journey": {
            "intro": 0.10,
            "rise": 0.20,
            "peak1": 0.20,
            "dip": 0.10,
            "peak2": 0.25,
            "outro": 0.15,
        },
        "wedding": {
            "dinner": 0.30,
            "first_dance": 0.10,
            "party": 0.40,
            "last_dance": 0.10,
            "exit": 0.10,
        },
    }

    def optimize_set(self, tracks: List[Dict], duration_minutes: int = 120,
                     style: str = "classic", venue: str = "club") -> Dict:
        """
        Optimize track ordering for maximum impact.

        Algorithm:
        1. Analyze each track's features
        2. Score all possible transitions
        3. Apply structure template
        4. Optimize for energy flow + harmonic compatibility
        """
        if not tracks:
            return {"tracks": [], "message": "No tracks to optimize"}

        # Step 1: Ensure features
        enriched = [self._ensure_features(t) for t in tracks]

        # Step 2: Build transition matrix
        trans_matrix = self._build_transition_matrix(enriched)

        # Step 3: Apply structure
        structure = self.STRUCTURES.get(style, self.STRUCTURES["classic"])

        # Step 4: Optimize ordering
        optimized = self._optimize_ordering(enriched, trans_matrix, structure, duration_minutes)

        # Step 5: Score and annotate
        for i, track in enumerate(optimized):
            track["set_position"] = i + 1
            track["transition_score"] = self._score_transition(
                optimized[i-1] if i > 0 else None, track
            )
            track["role"] = self._assign_role(i, len(optimized), track)
            track["advice"] = self._transition_advice(optimized, i)

        return {
            "tracks": optimized,
            "structure": style,
            "duration_minutes": duration_minutes,
            "avg_energy": round(np.mean([t.get("energy", 0.5) for t in optimized]), 3),
            "energy_variance": round(np.var([t.get("energy", 0.5) for t in optimized]), 4),
        }

    def _ensure_features(self, track: Dict) -> Dict:
        """Ensure track has all required features."""
        t = dict(track)
        for field, default in [
            ("energy", 0.5), ("bpm", 120), ("danceability", 0.5),
            ("brightness", 0.5), ("roughness", 0.3), ("vocal_risk", 0.3),
        ]:
            if field not in t or t[field] is None:
                t[field] = default
            else:
                try:
                    t[field] = float(t[field])
                except (TypeError, ValueError):
                    t[field] = default

        if "camelot" not in t:
            t["camelot"] = t.get("key", "")
        if "genre" not in t:
            t["genre"] = "unknown"
        if "role" not in t:
            t["role"] = "GROOVE"

        return t

    def _build_transition_matrix(self, tracks: List[Dict]) -> np.ndarray:
        """Build pairwise transition scores."""
        n = len(tracks)
        matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                matrix[i][j] = self._transition_score(tracks[i], tracks[j])

        return matrix

    def _transition_score(self, from_track: Dict, to_track: Dict) -> float:
        """Score how well from_track transitions to to_track (0-1)."""
        # BPM proximity
        bpm_from = from_track.get("bpm", 120)
        bpm_to = to_track.get("bpm", 120)
        bpm_score = max(0, 1 - abs(bpm_from - bpm_to) / 20)

        # Key compatibility
        key_from = from_track.get("camelot", "")
        key_to = to_track.get("camelot", "")
        if key_from and key_to:
            from app.ai.library_ai import LibraryAI
            compatible_keys = LibraryAI.key_compatibility(None, key_from)
            key_score = 1.0 if key_to in compatible_keys else 0.3
        else:
            key_score = 0.5

        # Energy progression (smooth transitions preferred)
        energy_from = from_track.get("energy", 0.5)
        energy_to = to_track.get("energy", 0.5)
        energy_diff = abs(energy_to - energy_from)
        energy_score = max(0, 1 - energy_diff * 2)  # Penalize large jumps

        # Genre compatibility
        genre_from = from_track.get("genre", "").lower()
        genre_to = to_track.get("genre", "").lower()
        genre_score = 1.0 if genre_from == genre_to else 0.6

        # Vocal risk (don't put two vocal-heavy tracks together)
        vocal_from = from_track.get("vocal_risk", 0.3)
        vocal_to = to_track.get("vocal_risk", 0.3)
        vocal_penalty = -0.2 if vocal_from > 0.5 and vocal_to > 0.5 else 0

        # Weighted combination
        score = (
            bpm_score * 0.25 +
            key_score * 0.25 +
            energy_score * 0.25 +
            genre_score * 0.15 +
            0.10  # base score
        ) + vocal_penalty

        return max(0.0, min(1.0, score))

    def _optimize_ordering(self, tracks: List[Dict], matrix: np.ndarray,
                           structure: Dict, duration_minutes: int) -> List[Dict]:
        """Optimize track ordering using greedy + local search."""
        n = len(tracks)
        if n <= 1:
            return tracks

        # Greedy nearest-neighbor from seed
        used = set()
        # Find best opening track (low energy, low vocal)
        seed_idx = 0
        best_seed_score = -1
        for i, t in enumerate(tracks):
            score = (1 - t.get("energy", 0.5)) * 0.5 + (1 - t.get("vocal_risk", 0.3)) * 0.3
            if score > best_seed_score:
                best_seed_score = score
                seed_idx = i

        order = [seed_idx]
        used.add(seed_idx)

        # Greedy: always pick best transition from current
        for _ in range(n - 1):
            current = order[-1]
            best_next = -1
            best_score = -1

            for j in range(n):
                if j in used:
                    continue
                score = matrix[current][j]
                if score > best_score:
                    best_score = score
                    best_next = j

            if best_next >= 0:
                order.append(best_next)
                used.add(best_next)
            else:
                break

        # Local search: try swapping adjacent pairs for better energy flow
        ordered_tracks = [tracks[i] for i in order]
        ordered_tracks = self._local_search_swap(ordered_tracks, iterations=50)

        return ordered_tracks

    def _local_search_swap(self, tracks: List[Dict], iterations: int = 50) -> List[Dict]:
        """Local search: swap adjacent tracks if it improves energy flow."""
        best = list(tracks)
        best_energy = self._energy_smoothness(best)

        for _ in range(iterations):
            i = np.random.randint(0, len(best) - 1)
            candidate = list(best)
            candidate[i], candidate[i+1] = candidate[i+1], candidate[i]

            cand_energy = self._energy_smoothness(candidate)
            if cand_energy > best_energy:
                best = candidate
                best_energy = cand_energy

        return best

    def _energy_smoothness(self, tracks: List[Dict]) -> float:
        """Score how smooth the energy transitions are (higher = better)."""
        if len(tracks) < 2:
            return 1.0

        energies = [t.get("energy", 0.5) for t in tracks]
        diffs = [abs(energies[i+1] - energies[i]) for i in range(len(energies)-1)]
        avg_diff = np.mean(diffs)

        # Penalize large jumps
        return max(0, 1 - avg_diff * 3)

    def _score_transition(self, from_track: Optional[Dict], to_track: Dict) -> float:
        """Score a specific transition (0-100)."""
        if not from_track:
            return 100.0  # Opening track
        return round(self._transition_score(from_track, to_track) * 100, 1)

    def _assign_role(self, position: int, total: int, track: Dict) -> str:
        """Assign set role based on position and features."""
        ratio = position / max(1, total)
        energy = track.get("energy", 0.5)

        if ratio < 0.15:
            return "OPENING"
        if ratio < 0.35:
            return "WARMUP"
        if ratio > 0.85:
            return "COOLDOWN"
        if energy > 0.75:
            return "PEAK TIME"
        if energy > 0.55:
            return "GROOVE"
        return "UTILITY"

    def _transition_advice(self, tracks: List[Dict], index: int) -> str:
        """Generate transition advice for a specific point."""
        if index == 0:
            return "Introdan gir; 32 bar bekle, crowd'ı oku."
        if index >= len(tracks) - 1:
            return "Son parca; DJ mix çıkışı için temiz kapanış."

        curr = tracks[index]
        next_t = tracks[index + 1] if index + 1 < len(tracks) else None

        if not next_t:
            return "Set sonu."

        curr_bpm = curr.get("bpm", 120)
        next_bpm = next_t.get("bpm", 120)
        diff = abs(curr_bpm - next_bpm)

        if diff > 8:
            return f"BPM farkı büyük ({curr_bpm:.0f}→{next_bpm:.0f}); yumuşak geçiş + pitch."
        if diff > 4:
            return f"Orta BPM farkı; 8-16 bar blend."
        return "BPM uyumlu; 4-8 bar quick mix."

    # ============================================================
    # ENERGY PREDICTION
    # ============================================================

    def predict_energy_curve(self, tracks: List[Dict], minutes_per_track: float = 4.0) -> List[Dict]:
        """Predict energy curve for a set."""
        curve = []
        for i, track in enumerate(tracks):
            time_minutes = i * minutes_per_track
            energy = track.get("energy", 0.5)

            # Predict crowd response (simplified model)
            if energy > 0.7 and i > len(tracks) * 0.3:
                crowd_energy = min(1.0, energy * 1.1)
            elif energy < 0.4:
                crowd_energy = max(0.2, energy * 0.9)
            else:
                crowd_energy = energy

            curve.append({
                "time_minutes": round(time_minutes, 1),
                "track_energy": energy,
                "predicted_crowd": round(crowd_energy, 3),
                "track": track.get("name", f"Track {i+1}"),
            })

        return curve

    # ============================================================
    # SET ANALYSIS
    # ============================================================

    def analyze_set_quality(self, tracks: List[Dict]) -> Dict:
        """Analyze the quality of a DJ set."""
        if not tracks:
            return {"score": 0, "issues": []}

        energies = [t.get("energy", 0.5) for t in tracks]
        bpms = [t.get("bpm", 120) for t in tracks]
        keys = [t.get("camelot", "") for t in tracks]

        # Energy arc analysis
        energy_smoothness = self._energy_smoothness(tracks)
        energy_variance = np.var(energies)
        peak_position = np.argmax(energies) / max(1, len(energies))

        # BPM flow
        bpm_diffs = [abs(bpms[i+1] - bpms[i]) for i in range(len(bpms)-1)]
        avg_bpm_jump = np.mean(bpm_diffs) if bpm_diffs else 0
        max_bpm_jump = max(bpm_diffs) if bpm_diffs else 0

        # Key diversity
        unique_keys = len(set(keys))
        key_diversity = unique_keys / max(1, len(keys))

        # Score
        score = int(
            energy_smoothness * 30 +
            max(0, 1 - avg_bpm_jump / 8) * 25 +
            min(1, unique_keys / 12) * 20 +
            min(1, len(tracks) / 30) * 15 +
            (0.1 if peak_position > 0.3 and peak_position < 0.7 else 0) * 10
        )

        issues = []
        if avg_bpm_jump > 6:
            issues.append(f"BPM atlama ortalaması yüksek: {avg_bpm_jump:.1f}")
        if max_bpm_jump > 12:
            issues.append(f"BPM'de büyük atlama var: {max_bpm_jump:.0f}")
        if energy_variance > 0.08:
            issues.append("Enerji çok dalgalanmış")
        if peak_position < 0.2:
            issues.append("Peak çok erken geldi")
        if peak_position > 0.8:
            issues.append("Peak çok geç geldi")
        if unique_keys < 6:
            issues.append("Ton çeşitliliği düşük")

        return {
            "score": score,
            "energy_smoothness": round(energy_smoothness, 3),
            "avg_bpm_jump": round(avg_bpm_jump, 1),
            "max_bpm_jump": round(max_bpm_jump, 1),
            "unique_keys": unique_keys,
            "peak_position": round(peak_position, 2),
            "issues": issues,
        }
