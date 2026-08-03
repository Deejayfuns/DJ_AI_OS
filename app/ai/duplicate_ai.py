class DuplicateAI:

    def decide(self, old_track, new_track):

        old_q = old_track.get("dj_score", 0)
        new_q = new_track.get("dj_score", 0)

        old_bitrate = old_track.get("bitrate", 0)
        new_bitrate = new_track.get("bitrate", 0)

        if new_bitrate > old_bitrate and new_q >= old_q:
            return "REPLACE"

        if new_q > old_q:
            return "REPLACE"

        return "KEEP"
