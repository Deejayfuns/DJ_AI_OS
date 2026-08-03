"""Smart Playlist Generator — mood/energy arc based playlists.

Generates playlists based on:
- Venue type (club, wedding, festival, lounge)
- Duration target (2h, 4h, 6h)
- Energy arc shape (warmup→peak→cool)
- Genre preferences
- Harmonic flow

Templates:
- Wedding: warm start → dance floor → ceremony moments → party → closing
- Club: warmup → groove → peak → cooldown
- Festival: building energy → main stage peak → encore
- Lounge: ambient → gentle rise → relaxed
"""


TEMPLATES = {
    "WEDDING": {
        "name": "Düğün Akışı",
        "phases": [
            {"name": "KARŞILAMA", "energy": (0.2, 0.35), "duration_pct": 0.10, "roles": ["OPENING", "WARMUP"]},
            {"name": "İLKL DANS", "energy": (0.4, 0.55), "duration_pct": 0.08, "roles": ["CEREMONY_MOMENT"]},
            {"name": "YEMEK MÜZİĞİ", "energy": (0.3, 0.45), "duration_pct": 0.20, "roles": ["WARMUP", "EVENT_SUPPORT"]},
            {"name": "DANS PARKURU", "energy": (0.6, 0.8), "duration_pct": 0.30, "roles": ["GROOVE", "DANCE_FLOOR_STARTER"]},
            {"name": "KAÇIRILMAZ ANLAR", "energy": (0.75, 0.9), "duration_pct": 0.15, "roles": ["PEAK TIME", "KINA_RITUAL"]},
            {"name": "KAPANIŞ", "energy": (0.4, 0.55), "duration_pct": 0.17, "roles": ["WARMUP", "REQUEST_FRIENDLY"]},
        ],
    },
    "CLUB": {
        "name": "Kulüp Akışı",
        "phases": [
            {"name": "ISITMA", "energy": (0.3, 0.45), "duration_pct": 0.15, "roles": ["OPENING", "WARMUP"]},
            {"name": "GROOVE", "energy": (0.5, 0.7), "duration_pct": 0.25, "roles": ["GROOVE"]},
            {"name": "YÜKSELİŞ", "energy": (0.7, 0.85), "duration_pct": 0.20, "roles": ["GROOVE", "PEAK TIME"]},
            {"name": "ZİRVE", "energy": (0.85, 1.0), "duration_pct": 0.25, "roles": ["PEAK TIME"]},
            {"name": "SOĞUMA", "energy": (0.4, 0.6), "duration_pct": 0.15, "roles": ["WARMUP", "GROOVE"]},
        ],
    },
    "FESTIVAL": {
        "name": "Festival Akışı",
        "phases": [
            {"name": "GİRİŞ", "energy": (0.4, 0.55), "duration_pct": 0.10, "roles": ["WARMUP"]},
            {"name": "BÜYÜME", "energy": (0.6, 0.8), "duration_pct": 0.25, "roles": ["GROOVE"]},
            {"name": "ANA SAHNE", "energy": (0.85, 1.0), "duration_pct": 0.35, "roles": ["PEAK TIME"]},
            {"name": "ENCORE", "energy": (0.75, 0.95), "duration_pct": 0.15, "roles": ["PEAK TIME", "GROOVE"]},
            {"name": "KAPANIŞ", "energy": (0.35, 0.5), "duration_pct": 0.15, "roles": ["WARMUP"]},
        ],
    },
    "LOUNGE": {
        "name": "Lounge Akışı",
        "phases": [
            {"name": "AMBIENT", "energy": (0.15, 0.3), "duration_pct": 0.25, "roles": ["OPENING"]},
            {"name": "YÜKSELİŞ", "energy": (0.3, 0.5), "duration_pct": 0.30, "roles": ["WARMUP"]},
            {"name": "ORTA SEVİYE", "energy": (0.45, 0.6), "duration_pct": 0.30, "roles": ["GROOVE"]},
            {"name": "KAPANIŞ", "energy": (0.2, 0.35), "duration_pct": 0.15, "roles": ["OPENING", "WARMUP"]},
        ],
    },
}


class SmartPlaylistGenerator:

    def __init__(self):
        pass

    def generate(self, library, venue="CLUB", hours=4, style=None):
        """Generate a smart playlist based on venue and duration.

        Args:
            library: list of track dicts
            venue: "CLUB", "WEDDING", "FESTIVAL", "LOUNGE"
            hours: target duration in hours
            style: optional genre preference

        Returns:
            dict with phases, tracks per phase, and total stats
        """
        template = TEMPLATES.get(venue, TEMPLATES["CLUB"])

        total_tracks_needed = int(hours * 18)  # ~18 tracks per hour
        used_ids = set()
        phases = []

        for phase_def in template["phases"]:
            phase_tracks_count = max(1, int(total_tracks_needed * phase_def["duration_pct"]))
            energy_min, energy_max = phase_def["energy"]
            allowed_roles = phase_def["roles"]

            phase_tracks = self._select_tracks(
                library, used_ids,
                energy_min, energy_max,
                allowed_roles, style,
                phase_tracks_count
            )

            used_ids.update(t.get("id") for t in phase_tracks)

            phases.append({
                "name": phase_def["name"],
                "target_energy": f"{energy_min:.2f}-{energy_max:.2f}",
                "tracks": phase_tracks,
                "track_count": len(phase_tracks),
                "instruction": self._phase_instruction(phase_def["name"], len(phase_tracks)),
            })

        all_tracks = []
        for phase in phases:
            all_tracks.extend(phase["tracks"])

        return {
            "venue": venue,
            "template": template["name"],
            "hours": hours,
            "total_tracks": len(all_tracks),
            "phases": phases,
            "stats": self._compute_stats(all_tracks),
        }

    def _select_tracks(self, library, used_ids, energy_min, energy_max, roles, style, count):
        """Select tracks matching criteria."""
        candidates = []

        for track in library:
            if track.get("id") in used_ids:
                continue

            energy = float(track.get("energy", 0.5) or 0.5)
            role = track.get("role", "")
            genre = track.get("parent_genre", track.get("genre", ""))

            if not (energy_min <= energy <= energy_max):
                continue

            if role not in roles:
                continue

            if style and style.upper() not in genre.upper():
                # Relax style filter if not enough matches
                pass

            # Score
            score = abs(energy - (energy_min + energy_max) / 2)
            ear = float(track.get("ai_ear_score", 0.5) or 0.5)
            score = score * 0.6 + (1 - ear) * 0.4

            candidates.append((score, track))

        candidates.sort(key=lambda x: x[0])
        return [t for _, t in candidates[:count]]

    def _phase_instruction(self, phase_name, track_count):
        instructions = {
            "KARŞILAMA": f"Misafirleri karşıla, {track_count} parçayla sessiz başla.",
            "İLKL DANS": "İlk dans için duygusal ve akıcı parçalar seç.",
            "YEMEK MÜZİĞİ": "Yemek sırasında rahatsız etmeyen arka plan müziği.",
            "DANS PARKURU": "Dans pistini doldur! Enerjiyi yükselt.",
            "KAÇIRILMAZ ANLAR": "Zirve anları — en güçlü parçaları burada kullan.",
            "KAPANIŞ": "Yavaş yavaş soğuma, misafirleri uğurla.",
            "ISITMA": f"Geceyi {track_count} parçayla yavaş başlat.",
            "GROOVE": "Kademeli olarak ritme gir, groove'u kur.",
            "YÜKSELİŞ": "Enerjiyi tırmandır, zirveye hazırla.",
            "ZİRVE": "Tavanı vur! En güçlü parçalar burada.",
            "SOĞUMA": "Geceyi yavaş yavaş sonlandır.",
            "GİRİŞ": "Festival giriş enerjisi — coşkulu ama kontrollü.",
            "BÜYÜME": "Sahneyi büyüt, enerjiyi kademeli olarak artır.",
            "ANA SAHNE": "Ana sahne能量 — festivalin zirve noktası!",
            "ENCORE": "Bis — hala güçlü ama soğumaya başlıyor.",
            "AMBIENT": "Sakin başla, misafirlerin rahatlamasına izin ver.",
            "ORTA SEVİYE": "Dengeli, çok sert olmayan ama monoton olmayan akış.",
        }
        return instructions.get(phase_name, f"{phase_name} fazı için {track_count} parca.")

    def _compute_stats(self, tracks):
        if not tracks:
            return {}

        energies = [float(t.get("energy", 0.5) or 0.5) for t in tracks]
        bpms = [float(t.get("bpm", 0) or 0) for t in tracks if t.get("bpm")]
        genres = set(t.get("parent_genre", t.get("genre", "")) for t in tracks)

        return {
            "avg_energy": round(sum(energies) / max(1, len(energies)), 2),
            "avg_bpm": round(sum(bpms) / max(1, len(bpms)), 1) if bpms else 0,
            "energy_range": f"{min(energies):.2f}-{max(energies):.2f}",
            "genre_diversity": len(genres),
        }
