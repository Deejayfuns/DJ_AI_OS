import json
import os
from datetime import datetime


class FeedbackLearner:

    def __init__(self, path="app/config/ai_feedback.json"):

        self.path = path
        self.memory = self.load()

    def record(self, track, signal, note=""):

        track_id = track.get("id") or track.get("path") or track.get("name")
        item = {
            "track_id": track_id,
            "name": track.get("name"),
            "genre": track.get("genre"),
            "role": track.get("role"),
            "signal": signal,
            "note": note,
            "created_at": datetime.now().isoformat(),
        }
        self.memory.setdefault("events", []).append(item)
        self.memory["weights"] = self.build_weights(self.memory["events"])
        self.save()

        return item

    def apply_to_track(self, track):

        weights = self.memory.get("weights", {})
        genre = str(track.get("genre", "")).upper()
        role = str(track.get("role", "")).upper()
        score = 0

        score += weights.get(f"genre:{genre}", 0)
        score += weights.get(f"role:{role}", 0)

        track["dj_feedback_score"] = round(score, 2)

        return track

    def build_weights(self, events):

        weights = {}
        signal_value = {
            "GOOD": 1.0,
            "BAD": -1.0,
            "NOT_PEAK": -0.6,
            "PEAK_CONFIRMED": 0.8,
            "GREAT_TRANSITION": 0.7,
        }

        for event in events:
            value = signal_value.get(event.get("signal"), 0)
            genre = str(event.get("genre", "")).upper()
            role = str(event.get("role", "")).upper()

            if genre:
                weights[f"genre:{genre}"] = weights.get(f"genre:{genre}", 0) + value

            if role:
                weights[f"role:{role}"] = weights.get(f"role:{role}", 0) + value

        return weights

    def load(self):

        if not os.path.exists(self.path):
            return {
                "events": [],
                "weights": {},
            }

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {
                "events": [],
                "weights": {},
            }

    def save(self):

        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.memory, handle, indent=2, ensure_ascii=True)
