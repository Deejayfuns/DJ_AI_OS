import json
import os
from datetime import datetime


class MemoryEngine:

    def __init__(self, file="dj_memory.json"):

        self.file = file

        self.data = self.load()

        # AI learning cache
        self.transition_map = self.build_transition_map()

    # -------------------------
    # LOAD / SAVE
    # -------------------------

    def load(self):

        if not os.path.exists(self.file):
            return []

        try:

            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)

        except:
            print("⚠ MEMORY FILE CORRUPTED — RESETTING")
            return []

    def save(self):

        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def genre_weight(self, genre):

        if not genre:
            return 0

        total = 0

        for session in self.data:
            for track in session.get("tracks", []):
                if str(track.get("genre", "")).lower() == str(genre).lower():
                    total += 1

        return min(total * 0.02, 0.2)

    def learn(self, genre):

        if not genre:
            return

        self.log_session({
            "tracks": [{"id": f"genre:{genre}", "genre": genre}],
            "transitions": [],
            "feedback": 0
        })

    # -------------------------
    # LOG SESSION
    # -------------------------

    def log_session(self, session_data):

        session_data["timestamp"] = str(datetime.now())

        if "feedback" not in session_data:
            session_data["feedback"] = 0

        if "transitions" not in session_data:
            session_data["transitions"] = []

        self.data.append(session_data)

        self.save()

        # rebuild AI memory
        self.transition_map = self.build_transition_map()

    # -------------------------
    # AUTO SESSION LOGGER
    # -------------------------

    def auto_log_set(self, tracks):

        transitions = []

        for i in range(len(tracks) - 1):

            a = tracks[i]
            b = tracks[i + 1]

            predicted = self.predict_transition_score(a, b)

            transitions.append({
                "from": a.get("id"),
                "to": b.get("id"),
                "score": predicted
            })

        session = {
            "tracks": tracks,
            "transitions": transitions,
            "feedback": 0
        }

        self.log_session(session)

    # -------------------------
    # LEARNING MODEL
    # -------------------------

    def build_transition_map(self):

        t_map = {}

        for session in self.data:

            tracks = session.get("tracks", [])

            transitions = session.get("transitions", [])

            for i in range(len(tracks) - 1):

                a = tracks[i]
                b = tracks[i + 1]

                key = f"{a.get('id')}->{b.get('id')}"

                if key not in t_map:
                    t_map[key] = []

                # transition score
                if i < len(transitions):
                    score = transitions[i].get("score", 50)
                else:
                    score = 50

                # session feedback effect
                feedback = session.get("feedback", 0)

                score += (feedback * 10)

                t_map[key].append(score)

        return t_map

    # -------------------------
    # AI PREDICTION
    # -------------------------

    def predict_transition_score(self, track_a, track_b):

        key = f"{track_a.get('id')}->{track_b.get('id')}"

        scores = self.transition_map.get(key, [])

        if not scores:
            return 50

        return sum(scores) / len(scores)

    # -------------------------
    # GLOBAL STATS
    # -------------------------

    def get_stats(self):

        all_scores = []

        for session in self.data:

            for t in session.get("transitions", []):

                all_scores.append(t.get("score", 50))

        if not all_scores:

            return {
                "avg_transition": 0,
                "total_sessions": len(self.data),
                "learned_transitions": 0
            }

        return {
            "avg_transition": round(
                sum(all_scores) / len(all_scores),
                2
            ),
            "total_sessions": len(self.data),
            "learned_transitions": len(self.transition_map)
        }
