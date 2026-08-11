"""
DJ AI OS — Set Builder (Consolidated)

Merges: SetEngine + ShowDirector + PerformancePlanner + SmartPlaylist
Single class for ALL set generation, show planning, and playlist creation.
"""

import math
from typing import Dict, List, Any, Optional


class SetBuilder:
    """
    Central set generation engine.
    """

    # ============================================================
    # STYLE PROFILES (from PerformancePlanner)
    # ============================================================

    STYLE_PROFILES = {
        "AFRO HOUSE": {
            "genres": {"AFRO HOUSE", "ORGANIC HOUSE", "DEEP HOUSE"},
            "bpm": (118, 126),
            "max_vocal": 0.45,
            "energy": 0.48,
        },
        "HOUSE": {
            "genres": {"DEEP HOUSE", "HOUSE", "ORGANIC HOUSE", "TECH HOUSE"},
            "bpm": (118, 128),
            "max_vocal": 0.5,
            "energy": 0.52,
        },
        "TECH HOUSE": {
            "genres": {"TECH HOUSE", "HOUSE", "DEEP HOUSE"},
            "bpm": (122, 130),
            "max_vocal": 0.45,
            "energy": 0.58,
        },
        "MELODIC": {
            "genres": {"MELODIC HOUSE", "MELODIC TECHNO", "ORGANIC HOUSE"},
            "bpm": (118, 128),
            "max_vocal": 0.55,
            "energy": 0.5,
        },
        "TECHNO": {
            "genres": {"TECHNO", "MELODIC TECHNO"},
            "bpm": (128, 140),
            "max_vocal": 0.3,
            "energy": 0.75,
        },
        "WEDDING": {
            "genres": {"TURKCE POP", "DISCO", "FUNK", "SOUL"},
            "bpm": (80, 128),
            "max_vocal": 0.85,
            "energy": 0.55,
        },
        "SUNRISE": {
            "genres": {"AMBIENT", "DEEP HOUSE", "ORGANIC HOUSE", "MELODIC"},
            "bpm": (110, 124),
            "max_vocal": 0.6,
            "energy": 0.35,
        },
    }

    # ============================================================
    # SET GENERATION (from SetEngine)
    # ============================================================

    def build_set(self, tracks: List[Dict], target_length: int = 20,
                  style: str = "HOUSE", energy_curve: str = "CLASSIC") -> Dict:
        """
        Build an AI-optimized set.

        energy_curve: 'CLASSIC' (rise+fall), 'SUSTAINED', 'WAVE', 'SUNRISE'
        """
        if not tracks:
            return {"tracks": [], "message": "Kütüphane bos"}

        profile = self.STYLE_PROFILES.get(style.upper(), self.STYLE_PROFILES["HOUSE"])
        enriched = self._filter_compatible(tracks, profile)

        if not enriched:
            enriched = tracks

        # Pick opening
        opener = self._pick_opener(enriched, profile)
        playlist = [opener]
        used = {opener.get("path", "")}

        # Build chain
        for _ in range(target_length - 1):
            next_track = self._find_best_next(playlist[-1], enriched, used)
            if not next_track:
                break
            playlist.append(next_track)
            used.add(next_track.get("path", ""))

        # Apply energy curve
        playlist = self._apply_energy_curve(playlist, energy_curve)

        # Assign positions and advice
        for i, track in enumerate(playlist):
            track["set_position"] = i + 1
            track["role"] = self._set_role(i, len(playlist), track.get("energy", 0.5))
            track["transition_advice"] = self._transition_advice(playlist, i)

        return {
            "tracks": playlist,
            "style": style,
            "energy_curve": energy_curve,
            "avg_bpm": round(sum(t.get("bpm", 0) for t in playlist if t.get("bpm")) / max(1, len(playlist)), 1),
            "message": f"{len(playlist)} parcalik {style} seti hazir",
        }

    # ============================================================
    # SHOW DIRECTOR (from ShowDirector)
    # ============================================================

    def build_show(self, tracks: List[Dict], style: str = "HOUSE",
                   hours: float = 4) -> Dict:
        """Build a complete show plan with segments."""
        target = int(hours * 12)  # ~12 tracks per hour

        segments = []
        remaining = list(tracks)

        # Segment breakdown by time
        seg_configs = [
            ("OPENING", 0.15, "Yavas baslangic, kalabaligi iceri al", 0.35),
            ("WARMUP", 0.20, "Enerjiyi kademeli olarak artir", 0.50),
            ("GROOVE", 0.25, "Ana groove kilitlendi, devam et", 0.65),
            ("PEAK", 0.25, "Maksimum enerji, buyuk anlar", 0.85),
            ("COOLDOWN", 0.15, "Kontrollu kapanis, DJ mix cikisi", 0.45),
        ]

        for name, ratio, instruction, target_energy in seg_configs:
            seg_count = max(1, int(target * ratio))
            seg_tracks = self._select_for_segment(remaining, seg_count, target_energy)

            segments.append({
                "name": name,
                "instruction": instruction,
                "target_energy": target_energy,
                "track_count": len(seg_tracks),
                "tracks": seg_tracks,
                "risk": "LOW" if name in ("OPENING", "COOLDOWN") else "MEDIUM",
            })

            for t in seg_tracks:
                if t in remaining:
                    remaining.remove(t)

        return {
            "segments": segments,
            "style": style,
            "hours": hours,
            "rescue_tracks": remaining[:5],
            "director_note": f"{hours} saatlik {style} show plani hazir. "
                           "Her segmentin kendi hedef enerjisi var.",
        }

    # ============================================================
    # SMART PLAYLIST (from SmartPlaylist)
    # ============================================================

    def build_smart_playlist(self, tracks: List[Dict], template: str = "CLUB_NIGHT",
                             duration_minutes: int = 120) -> Dict:
        """Build a playlist from a template."""
        target_count = max(1, duration_minutes // 5)  # ~5 min per track

        if template == "CLUB_NIGHT":
            result = self.build_set(tracks, target_length=target_count, style="HOUSE")
        elif template == "WEDDING":
            result = self.build_set(tracks, target_length=target_count, style="WEDDING")
        elif template == "SUNRISE":
            result = self.build_set(tracks, target_length=target_count, style="SUNRISE", energy_curve="SUNRISE")
        elif template == "FESTIVAL":
            result = self.build_set(tracks, target_length=target_count, style="TECHNO")
        else:
            result = self.build_set(tracks, target_length=target_count)

        return {
            "template": template,
            "duration_minutes": duration_minutes,
            "tracks": result.get("tracks", []),
            "message": f"{template} playlisti hazir: {len(result.get('tracks', []))} parca",
        }

    # ============================================================
    # OPENING RECOMMENDATIONS (from PerformancePlanner)
    # ============================================================

    def recommend_openers(self, tracks: List[Dict], style: str = "HOUSE",
                          limit: int = 5) -> List[Dict]:
        """Recommend opening tracks for a set."""
        profile = self.STYLE_PROFILES.get(style.upper(), self.STYLE_PROFILES["HOUSE"])
        scored = []

        for track in tracks:
            energy = float(track.get("energy", 0.5) or 0.5)
            vocal_risk = float(track.get("vocal_risk", 0.3) or 0.3)
            bpm = float(track.get("bpm", 0) or 0)
            genre = track.get("genre", "").upper()

            # Opening criteria: low energy, low vocal, within BPM range
            score = 0.0
            if energy < profile["energy"] + 0.15:
                score += 0.4
            if vocal_risk < profile["max_vocal"]:
                score += 0.3
            if profile["bpm"][0] <= bpm <= profile["bpm"][1]:
                score += 0.2
            if genre in profile["genres"] or any(g.lower() in genre.lower() for g in profile["genres"]):
                score += 0.1

            if score > 0.3:
                scored.append({**track, "opener_score": round(score, 3)})

        scored.sort(key=lambda t: t["opener_score"], reverse=True)
        return scored[:limit]

    # ============================================================
    # INTERNAL HELPERS
    # ============================================================

    def _filter_compatible(self, tracks, profile):
        """Filter tracks compatible with style profile."""
        compatible = []
        for track in tracks:
            genre = str(track.get("genre", "")).upper()
            bpm = float(track.get("bpm", 0) or 0)
            vocal = float(track.get("vocal_risk", 0.3) or 0.3)

            genre_ok = genre in profile["genres"] or any(g.lower() in genre.lower() for g in profile["genres"])
            bpm_ok = profile["bpm"][0] <= bpm <= profile["bpm"][1]
            vocal_ok = vocal <= profile["max_vocal"]

            if genre_ok or (bpm_ok and vocal_ok):
                compatible.append(track)

        return compatible if compatible else tracks

    def _pick_opener(self, tracks, profile):
        """Pick the best opening track."""
        best = None
        best_score = -1
        for track in tracks:
            energy = float(track.get("energy", 0.5) or 0.5)
            if energy < profile["energy"] + 0.2 and energy > best_score:
                best = track
                best_score = energy
        return best or tracks[0] if tracks else {}

    def _find_best_next(self, current, candidates, used):
        """Find the best track to follow the current one."""
        current_bpm = float(current.get("bpm", 120) or 120)
        current_energy = float(current.get("energy", 0.5) or 0.5)

        best = None
        best_score = -1

        for track in candidates:
            if track.get("path", "") in used:
                continue

            bpm = float(track.get("bpm", 120) or 120)
            energy = float(track.get("energy", 0.5) or 0.5)

            bpm_score = max(0, 1 - abs(bpm - current_bpm) / 20)
            energy_diff = abs(energy - current_energy)
            energy_score = max(0, 1 - energy_diff)

            score = bpm_score * 0.6 + energy_score * 0.4

            if score > best_score:
                best = track
                best_score = score

        return best

    def _apply_energy_curve(self, tracks, curve):
        """Reorder tracks based on energy curve."""
        if curve == "CLASSIC":
            # Rise then fall
            n = len(tracks)
            mid = n // 2
            first_half = sorted(tracks[:mid], key=lambda t: t.get("energy", 0.5))
            second_half = sorted(tracks[mid:], key=lambda t: -t.get("energy", 0.5))
            return first_half + second_half
        elif curve == "SUSTAINED":
            return sorted(tracks, key=lambda t: -t.get("energy", 0.5))
        elif curve == "WAVE":
            by_energy = sorted(tracks, key=lambda t: t.get("energy", 0.5))
            result = []
            low, high = by_energy[:len(by_energy)//2], by_energy[len(by_energy)//2:]
            while low or high:
                if high: result.append(high.pop(0))
                if low: result.append(low.pop(0))
            return result
        return tracks

    def _set_role(self, position, total, energy):
        """Assign set role based on position."""
        if position < total * 0.15: return "OPENING"
        if position < total * 0.35: return "WARMUP"
        if position > total * 0.85: return "COOLDOWN"
        if energy > 0.7: return "PEAK TIME"
        return "GROOVE"

    def _transition_advice(self, tracks, index):
        """Generate transition advice."""
        if index == 0:
            return "Introdan gir, kalabaligi okumak icin 32 bar bekle."
        if index >= len(tracks) - 1:
            return "Son parca; DJ mix cikisi icin temiz kapanis."
        curr = tracks[index]
        next_t = tracks[index + 1] if index + 1 < len(tracks) else None
        if not next_t:
            return "Set sonu."
        curr_bpm = float(curr.get("bpm", 120) or 120)
        next_bpm = float(next_t.get("bpm", 120) or 120)
        if abs(curr_bpm - next_bpm) > 5:
            return f"BPM farki buyuk ({curr_bpm:.0f} -> {next_bpm:.0f}); yumusak gecis kullan."
        return "BPM yaklasik; 8-16 bar blend ile gec."

    def _select_for_segment(self, tracks, count, target_energy):
        """Select tracks for a specific segment."""
        scored = [(abs(float(t.get("energy", 0.5) or 0.5) - target_energy), t) for t in tracks]
        scored.sort(key=lambda x: x[0])
        return [t for _, t in scored[:count]]
