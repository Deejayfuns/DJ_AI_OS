class SetBuilder:
    def __init__(self, harmonic_engine):
        self.harmonic = harmonic_engine

    def build(self, tracks, target_length=20):

        target_length = min(target_length, len(tracks))

        tracks = sorted(
            tracks,
            key=lambda x: (
                x.get("energy", 0),
                x.get("hit_score", 0)
            )
        )

        low, mid, high = [], [], []

        for t in tracks:
            e = t.get("energy", 0)

            if e < 0.4:
                low.append(t)
            elif e < 0.75:
                mid.append(t)
            else:
                high.append(t)

        set_list = []
        visited = set()
        low_count = max(1, int(target_length * 0.3))
        mid_count = max(1, int(target_length * 0.4))
        high_count = max(0, target_length - low_count - mid_count)

        def pick(pool, count):

            if not pool:
                return []

            result = []
            current = pool[0]

            result.append(current)
            visited.add(current["id"])

            pool = pool[1:]

            for _ in range(count - 1):

                best = None
                best_score = -1

                for c in pool:

                    if c["id"] in visited:
                        continue

                    score = self.harmonic.match_score(current, c)["score"]

                    if score > best_score:
                        best = c
                        best_score = score

                if best:
                    result.append(best)
                    visited.add(best["id"])
                    pool.remove(best)
                    current = best

            return result

        set_list += pick(low, low_count)
        set_list += pick(mid, mid_count)
        set_list += pick(high, high_count)

        if len(set_list) < target_length:
            remaining = [
                t for t in tracks
                if t.get("id") not in visited
            ]
            set_list += self.pick_sequence(
                remaining,
                target_length - len(set_list)
            )

        return set_list

    def pick_sequence(self, pool, count):

        if not pool:
            return []

        result = []
        current = pool[0]
        result.append(current)

        pool = pool[1:]

        for _ in range(count - 1):

            best = None
            best_score = -1

            for candidate in pool:

                score = self.harmonic.match_score(
                    current,
                    candidate
                )["score"]

                if score > best_score:
                    best_score = score
                    best = candidate

            if best:
                result.append(best)
                pool.remove(best)
                current = best

        return result
