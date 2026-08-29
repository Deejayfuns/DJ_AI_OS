"""Set Recorder — records DJ decisions during playback.

Tracks:
- Which tracks were played and for how long
- Which tracks were skipped
- Transition points and mix durations
- Energy levels at each point
- BPM changes during the set

Used by DJ Coach for post-set analysis and by FeedbackLearner
to improve future recommendations.
"""

import json
import os
import time

from app.core.paths import get_exports_dir


class SetRecorder:

    def __init__(self, log_dir=None):
        self.log_dir = log_dir or str(get_exports_dir())
        self.recording = False
        self.session = None
        self._start_time = 0

    def start_recording(self, venue="CLUB", style="AFRO HOUSE"):
        """Start recording a new set session."""
        self.recording = True
        self._start_time = time.time()

        self.session = {
            "venue": venue,
            "style": style,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tracks": [],
            "skipped": [],
            "transitions": [],
        }

    def stop_recording(self):
        """Stop recording and save the session."""
        self.recording = False

        if self.session:
            self.session["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.session["duration_seconds"] = time.time() - self._start_time
            self.session["total_tracks"] = len(self.session["tracks"])
            self.session["total_skipped"] = len(self.session["skipped"])

            path = self._save_session()
            self.session["log_path"] = path

        result = dict(self.session) if self.session else {}
        self.session = None
        return result

    def record_track_start(self, track):
        """Record when a track starts playing."""
        if not self.recording or not self.session:
            return

        entry = {
            "track_id": track.get("id", ""),
            "name": track.get("name", ""),
            "bpm": track.get("bpm", 0),
            "energy": track.get("energy", 0.5),
            "genre": track.get("genre", ""),
            "role": track.get("role", ""),
            "key": track.get("camelot", track.get("key", "")),
            "start_time_offset": time.time() - self._start_time,
            "end_time_offset": None,
            "duration_played": None,
        }

        self.session["tracks"].append(entry)

    def record_track_end(self):
        """Record when the current track stops playing."""
        if not self.recording or not self.session:
            return

        if self.session["tracks"]:
            current = self.session["tracks"][-1]
            current["end_time_offset"] = time.time() - self._start_time
            current["duration_played"] = (
                current["end_time_offset"] - current["start_time_offset"]
            )

    def record_skip(self, track, reason=""):
        """Record a skipped track."""
        if not self.recording or not self.session:
            return

        self.session["skipped"].append({
            "track_id": track.get("id", ""),
            "name": track.get("name", ""),
            "reason": reason,
            "time_offset": time.time() - self._start_time,
        })

    def record_transition(self, from_track, to_track, method=""):
        """Record a transition between tracks."""
        if not self.recording or not self.session:
            return

        self.session["transitions"].append({
            "from": from_track.get("name", ""),
            "to": to_track.get("name", ""),
            "bpm_from": from_track.get("bpm", 0),
            "bpm_to": to_track.get("bpm", 0),
            "key_from": from_track.get("camelot", ""),
            "key_to": to_track.get("camelot", ""),
            "method": method,
            "time_offset": time.time() - self._start_time,
        })

    def get_session_summary(self):
        """Get a summary of the current recording session."""
        if not self.session:
            return {}

        played = self.session["tracks"]
        skipped = self.session["skipped"]

        if not played:
            return {"message": "Henuz parca calinmadi."}

        energies = [t.get("energy", 0.5) for t in played]
        bpms = [t.get("bpm", 0) for t in played if t.get("bpm")]

        return {
            "tracks_played": len(played),
            "tracks_skipped": len(skipped),
            "avg_energy": round(sum(energies) / max(1, len(energies)), 2),
            "avg_bpm": round(sum(bpms) / max(1, len(bpms)), 1) if bpms else 0,
            "duration_minutes": round((time.time() - self._start_time) / 60, 1),
            "transitions": len(self.session["transitions"]),
        }

    def _save_session(self):
        """Save session to disk."""
        os.makedirs(self.log_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.log_dir, f"set_recording_{timestamp}.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.session, f, indent=2, ensure_ascii=False)

        return os.path.abspath(path)
