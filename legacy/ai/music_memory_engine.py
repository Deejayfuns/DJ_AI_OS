class MusicMemoryEngine:

    def __init__(self, db):
        self.db = db

    # =====================================================
    # LEARN TRACK
    # =====================================================
    def learn(self, track):

        genre = track.get("genre", "unknown")
        mood = track.get("mood", "unknown")
        energy = track.get("energy", 0)

        # burada gelecekte ML gelecek
        tags = self.generate_tags(track)

        track["tags"] = tags

        self.db.save_track(track)

        return track

    # =====================================================
    # SIMPLE AI TAGGING (PHASE 1)
    # =====================================================
    def generate_tags(self, track):

        tags = []

        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0)
        mood = track.get("mood", "").lower()

        if bpm > 128:
            tags.append("high_energy")
        elif bpm < 100:
            tags.append("low_energy")

        if energy > 0.7:
            tags.append("club_ready")

        if "sad" in mood:
            tags.append("emotional")

        if "happy" in mood:
            tags.append("uplifting")

        return tags

    # =====================================================
    # FIND SIMILAR TRACKS
    # =====================================================
    def find_similar(self, track):

        all_tracks = self.db.load_all()

        result = []

        for t in all_tracks:

            score = 0

            if t.get("genre") == track.get("genre"):
                score += 3

            if t.get("mood") == track.get("mood"):
                score += 2

            if abs(t.get("bpm", 0) - track.get("bpm", 0)) < 5:
                score += 2

            if score > 3:
                result.append(t)

        return result
