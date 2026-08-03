class AIDecisionEngine:

    def decide(self, old_track, new_track):

        old_bitrate = old_track.get("bitrate", 0)
        new_bitrate = new_track.get("bitrate", 0)

        if new_bitrate > old_bitrate:
            return "upgrade_candidate"

        elif new_bitrate < old_bitrate:
            return "keep_old"

        return "equal_quality"
