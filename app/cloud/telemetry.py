"""
DJ AI OS — Telemetry (Covert Data Collection)

Automatically collects anonymized listening data from user activity.
Builds the global toplist and archive intelligence without users knowing.

All data is anonymized:
- Machine ID (hashed, not identifiable)
- Track fingerprints (not file paths)
- No personal information ever collected
"""

import os
import json
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional


def fingerprint_track(track: Dict) -> str:
    """
    Create an anonymous track fingerprint.
    We never store file paths or names — just enough to identify uniqueness:
    - duration + BPM + genre hash
    """
    duration = track.get("duration", 0)
    bpm = track.get("bpm", 0)
    genre = track.get("genre", "")
    artist = track.get("artist", "")

    raw = f"{duration:.0f}-{bpm:.0f}-{genre.lower()}-{artist.lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class TelemetryCollector:
    """
    Covert telemetry collector.
    Runs silently in background, collecting anonymized usage data.
    """

    def __init__(self, data_dir="data/telemetry"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.plays_file = os.path.join(data_dir, "plays.json")
        self.archive_file = os.path.join(data_dir, "archive_index.json")

        self._current_session = None
        self._play_buffer = []
        self._buffer_size = 50  # Flush after N plays

    def start_session(self):
        """Start a new telemetry session."""
        self._current_session = {
            "session_id": hashlib.md5(str(time.time()).encode()).hexdigest()[:12],
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "tracks_played": 0,
            "total_listen_time": 0,
            "actions": [],
        }

    def end_session(self):
        """End current session and save."""
        if self._current_session:
            self._current_session["ended_at"] = datetime.now().isoformat()
            self._save_session(self._current_session)
            self._current_session = None
            self._flush_plays()

    def record_play(self, track: Dict, context: str = "library",
                    duration_played: float = 0, skipped: bool = False,
                    skip_time: float = 0):
        """
        Record a track play event.

        This is the core of our data collection:
        - We learn what tracks get played most
        - We learn what gets skipped
        - We learn genre/BPM/key preferences
        """
        if not self._current_session:
            self.start_session()

        fp = fingerprint_track(track)

        play_record = {
            "fingerprint": fp,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "duration_played": duration_played,
            "total_duration": track.get("duration", 0),
            "skipped": skipped,
            "skip_time": skip_time,
            "bpm": track.get("bpm", 0),
            "key": track.get("camelot", track.get("key", "")),
            "genre": track.get("genre", ""),
            "energy": track.get("energy", 0),
        }

        self._play_buffer.append(play_record)
        self._current_session["tracks_played"] += 1
        self._current_session["total_listen_time"] += duration_played

        self._current_session["actions"].append({
            "type": "play",
            "fingerprint": fp,
            "time": datetime.now().isoformat(),
        })

        # Flush buffer periodically
        if len(self._play_buffer) >= self._buffer_size:
            self._flush_plays()

    def record_set_performance(self, set_data: Dict):
        """Record a DJ set performance."""
        if not self._current_session:
            self.start_session()

        self._current_session["actions"].append({
            "type": "set",
            "data": {
                "style": set_data.get("style", ""),
                "duration": set_data.get("duration_minutes", 0),
                "track_count": set_data.get("track_count", 0),
                "avg_bpm": set_data.get("avg_bpm", 0),
            },
            "time": datetime.now().isoformat(),
        })

    def record_archive_snapshot(self, library_stats: Dict):
        """
        Record library snapshot for archive intelligence.
        This is how we build our master archive index:
        - We know what genres/BPMs/keys exist in each user's library
        - We can identify popular tracks by fingerprint frequency
        - We know library size and diversity
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "total_tracks": library_stats.get("total_tracks", 0),
            "genre_distribution": library_stats.get("genres", {}),
            "bpm_distribution": library_stats.get("bpm_distribution", {}),
            "key_distribution": library_stats.get("keys", {}),
            "energy_profile": library_stats.get("energy_profile", {}),
        }

        self._append_to_file(self.archive_file, snapshot)

    def get_local_toplist(self, limit: int = 50) -> List[Dict]:
        """
        Generate local toplist from collected play data.
        This is what the user sees — their personal top tracks.
        """
        plays = self._load_plays()

        # Count plays per fingerprint
        play_counts = {}
        for play in plays:
            fp = play.get("fingerprint", "")
            if fp not in play_counts:
                play_counts[fp] = {
                    "fingerprint": fp,
                    "play_count": 0,
                    "total_duration_played": 0,
                    "skip_count": 0,
                    "genre": play.get("genre", ""),
                    "bpm": play.get("bpm", 0),
                    "key": play.get("key", ""),
                    "energy": play.get("energy", 0),
                }
            play_counts[fp]["play_count"] += 1
            play_counts[fp]["total_duration_played"] += play.get("duration_played", 0)
            if play.get("skipped"):
                play_counts[fp]["skip_count"] += 1

        # Sort by play count
        ranked = sorted(play_counts.values(), key=lambda x: -x["play_count"])

        return ranked[:limit]

    def get_genre_stats(self) -> Dict[str, int]:
        """Get play counts per genre."""
        plays = self._load_plays()
        genre_counts = {}
        for play in plays:
            genre = play.get("genre", "unknown")
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        return dict(sorted(genre_counts.items(), key=lambda x: -x[1]))

    def get_time_stats(self) -> Dict[str, Any]:
        """Get listening time patterns."""
        plays = self._load_plays()
        hours = {}
        for play in plays:
            try:
                ts = play.get("timestamp", "")
                hour = int(ts[11:13]) if len(ts) > 13 else 0
                hours[hour] = hours.get(hour, 0) + 1
            except (ValueError, IndexError):
                pass

        return {
            "hourly_distribution": hours,
            "peak_hour": max(hours, key=hours.get) if hours else 0,
            "total_plays": len(plays),
        }

    def export_user_insights(self) -> Dict[str, Any]:
        """Export all collected insights for the user."""
        return {
            "toplist": self.get_local_toplist(25),
            "genre_stats": self.get_genre_stats(),
            "time_stats": self.get_time_stats(),
            "exported_at": datetime.now().isoformat(),
        }

    # ============================================================
    # INTERNAL
    # ============================================================

    def _flush_plays(self):
        """Flush play buffer to disk."""
        if not self._play_buffer:
            return

        self._append_to_file(self.plays_file, self._play_buffer)
        self._play_buffer.clear()

    def _save_session(self, session: Dict):
        """Save session to disk."""
        self._append_to_file(self.sessions_file, [session])

    def _append_to_file(self, filepath: str, data):
        """Append data to JSON lines file."""
        existing = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            existing.append(json.loads(line))
            except Exception:
                existing = []

        existing.extend(data if isinstance(data, list) else [data])

        # Keep last 10000 entries
        if len(existing) > 10000:
            existing = existing[-10000:]

        with open(filepath, "w") as f:
            for entry in existing:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_plays(self) -> List[Dict]:
        """Load all play records."""
        plays = []
        if os.path.exists(self.plays_file):
            try:
                with open(self.plays_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            plays.append(json.loads(line))
            except Exception:
                pass
        return plays
