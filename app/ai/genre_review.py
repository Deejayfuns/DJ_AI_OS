import json
import os


class GenreReviewStudio:

    def __init__(self, mapping_path="app/config/genre_review_map.json"):

        self.mapping_path = mapping_path
        self.mapping = self.load()

    def needs_review(self, tracks):

        return [
            track for track in tracks
            if track.get("discovery_status") == "DISCOVERED"
            or str(track.get("genre", "")).upper().startswith("DISCOVERED_STYLE")
            or str(track.get("parent_genre", "")).upper() in {"UNKNOWN", ""}
        ]

    def approve(self, track, genre, parent_genre="", role=""):

        key = self.key_for(track)
        record = {
            "genre": genre,
            "parent_genre": parent_genre or genre,
            "role": role or track.get("role", ""),
        }
        self.mapping[key] = record
        self.save()

        return record

    def apply(self, track):

        key = self.key_for(track)
        record = self.mapping.get(key)

        if not record:
            return track

        track.update({
            "genre": record.get("genre", track.get("genre")),
            "parent_genre": record.get("parent_genre", track.get("parent_genre")),
            "role": record.get("role", track.get("role")),
            "discovery_status": "DJ_APPROVED",
            "confidence": max(float(track.get("confidence", 0) or 0), 0.9),
        })

        return track

    def key_for(self, track):

        name = str(track.get("name") or track.get("path") or track.get("id") or "")
        return name.lower().replace("\\", "/")

    def load(self):

        if not os.path.exists(self.mapping_path):
            return {}

        try:
            with open(self.mapping_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def save(self):

        os.makedirs(os.path.dirname(self.mapping_path), exist_ok=True)

        with open(self.mapping_path, "w", encoding="utf-8") as handle:
            json.dump(self.mapping, handle, indent=2, ensure_ascii=True)
