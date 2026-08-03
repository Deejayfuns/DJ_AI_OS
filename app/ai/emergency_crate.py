"""Emergency Crate — rescue tracks when energy drops or set goes wrong.

When the DJ's energy drops, crowd disengages, or an unexpected gap
appears, the Emergency Crate suggests the best rescue tracks from
the library based on energy, role, and harmonic compatibility.
"""

from app.ui.dj_widgets import HarmonicWheel


class EmergencyCrate:

    # Rescue priority: tracks with these roles are best for recovery
    RESCUE_ROLES = {
        "PEAK TIME": 1.0,
        "GROOVE": 0.8,
        "WARMUP": 0.5,
        "OPENING": 0.3,
    }

    def __init__(self):
        pass

    def find_rescue_tracks(
        self,
        library,
        current_track=None,
        energy_threshold=0.3,
        target_energy=0.7,
        limit=5,
    ):
        """Find rescue tracks when energy drops.

        Args:
            library: list of track dicts
            current_track: the currently playing track (for harmonic matching)
            energy_threshold: if current energy below this, rescue needed
            target_energy: desired energy level for rescue tracks
            limit: max rescue tracks to return

        Returns:
            list of rescue track dicts with rescue_score
        """
        if not library:
            return []

        current_key = (current_track or {}).get("camelot", "")
        current_energy = float((current_track or {}).get("energy", 0.5) or 0.5)

        rescue_candidates = []

        for track in library:
            energy = float(track.get("energy", 0.5) or 0.5)
            role = track.get("role", "")
            key = track.get("camelot", track.get("key", ""))
            name = track.get("name", "")

            # Skip if track is currently playing
            if current_track and track.get("id") == current_track.get("id"):
                continue

            # Score: higher energy = better rescue
            energy_score = max(0, energy - current_energy) * 2

            # Role score
            role_score = self.RESCUE_ROLES.get(role, 0.3)

            # Harmonic compatibility bonus
            harmonic_bonus = 0
            if current_key and key:
                compatible = HarmonicWheel.COMPATIBLE_KEYS.get(current_key, [])
                if key in compatible:
                    harmonic_bonus = 0.3

            # Distance from target energy (closer = better)
            target_proximity = max(0, 1 - abs(energy - target_energy))

            total_score = (
                energy_score * 0.4 +
                role_score * 0.25 +
                harmonic_bonus * 0.2 +
                target_proximity * 0.15
            )

            rescue_candidates.append({
                **track,
                "rescue_score": round(total_score, 3),
                "rescue_reason": self._build_reason(
                    energy, role, harmonic_bonus > 0, current_energy
                ),
            })

        # Sort by rescue_score descending
        rescue_candidates.sort(key=lambda t: t["rescue_score"], reverse=True)

        return rescue_candidates[:limit]

    def assess_set_health(self, tracks, current_index=0):
        """Assess overall set health and suggest intervention if needed.

        Returns dict with health_score, issues, and suggestions.
        """
        if not tracks:
            return {"health_score": 100, "issues": [], "suggestion": "Set bos."}

        issues = []
        suggestions = []

        # Check energy arc
        energies = [float(t.get("energy", 0.5) or 0.5) for t in tracks]
        avg_energy = sum(energies) / len(energies) if energies else 0.5

        # Check for energy drops
        if current_index > 0 and current_index < len(energies):
            recent = energies[max(0, current_index - 3):current_index + 1]
            if len(recent) >= 2 and recent[-1] < recent[0] * 0.6:
                issues.append("ENERGY_DROP")
                suggestions.append(
                    "Son 3 parcadan bu yana enerji ciddi dustu. "
                    "Yuksek enerjili bir parca ile canlandir."
                )

        # Check for repetitive BPM
        if len(tracks) >= 4:
            recent_bpms = [
                float(t.get("bpm", 0) or 0)
                for t in tracks[max(0, current_index - 3):current_index + 1]
            ]
            if recent_bpms and len(set(int(b) for b in recent_bpms if b > 0)) == 1:
                issues.append("BPM_MONOTONY")
                suggestions.append(
                    "Son parcalar ayni BPM'de — BPM cesitliligi ekle."
                )

        # Check for harmonic jumps
        if current_index > 0 and current_index < len(tracks):
            prev_key = tracks[current_index - 1].get("camelot", "")
            curr_key = tracks[current_index].get("camelot", "")
            if prev_key and curr_key:
                compatible = HarmonicWheel.COMPATIBLE_KEYS.get(prev_key, [])
                if curr_key not in compatible:
                    issues.append("HARMONIC_JUMP")
                    suggestions.append(
                        f"Harmonik atlama: {prev_key} -> {curr_key}. "
                        "Uyumlu bir gec parca ekle."
                    )

        health = 100 - len(issues) * 15

        return {
            "health_score": max(0, health),
            "issues": issues,
            "suggestions": suggestions,
            "avg_energy": round(avg_energy, 2),
        }

    def _build_reason(self, energy, role, harmonic, current_energy):
        parts = []
        if energy > current_energy + 0.2:
            parts.append(f"enerji {energy:.2f} (mevcut {current_energy:.2f})")
        if role in ("PEAK TIME", "GROOVE"):
            parts.append(f"rol: {role}")
        if harmonic:
            parts.append("harmonik uyumlu")
        return " | ".join(parts) if parts else "genel kurtarma adayi"
