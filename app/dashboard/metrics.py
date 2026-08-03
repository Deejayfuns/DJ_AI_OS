from collections import defaultdict


class MetricsEngine:

    def __init__(self):

        self.data = defaultdict(list)

    def ingest_track(self, track):

        genre = track.get("genre")
        energy = track.get("energy", 0)
        bpm = track.get("bpm", 0)
        role = track.get("role")

        self.data["genre"].append(genre)
        self.data["energy"].append(energy)
        self.data["bpm"].append(bpm)
        self.data["role"].append(role)

    def calculate(self):

        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        genres = self.data["genre"]

        top_genre = max(
            set(genres),
            key=genres.count
        ) if genres else "UNKNOWN"

        return {

            "top_genre": top_genre,

            "avg_energy": round(
                avg(self.data["energy"]),
                2
            ),

            "avg_bpm": round(
                avg(self.data["bpm"]),
                1
            ),

            "peak_ratio": round(
                self.data["role"].count("PEAK TIME") /
                len(self.data["role"])
                if self.data["role"] else 0,
                2
            )
        }
