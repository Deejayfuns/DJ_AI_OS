class SetStoryEngine:

    def __init__(self, transition_engine):

        self.transition = transition_engine

    def build_story_set(self, tracks, length=20):

        intro, groove, peak, outro = self.split_tracks(tracks)

        set_list = []

        # 1. INTRO START
        current = intro[0]
        set_list.append(current)

        pool = intro[1:] + groove + peak + outro

        # 2. STORY BUILD
        for _ in range(length - 1):

            next_track = self.transition.best_next(current, pool)

            if not next_track:
                break

            set_list.append(next_track)
            pool.remove(next_track)
            current = next_track

        return set_list

    def split_tracks(self, tracks):

        intro = []
        groove = []
        peak = []
        outro = []

        for t in tracks:

            energy = t.get("energy", 0.5)

            if energy < 0.4:
                intro.append(t)

            elif energy < 0.6:
                groove.append(t)

            elif energy < 0.8:
                peak.append(t)

            else:
                outro.append(t)

        return intro, groove, peak, outro
