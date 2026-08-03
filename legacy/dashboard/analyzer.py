from app.dashboard.metrics import MetricsEngine


class DJAnalyzer:

    def __init__(self):

        self.metrics = MetricsEngine()

    def feed(self, track_result):

        self.metrics.ingest_track(track_result)

    def profile(self):

        stats = self.metrics.calculate()

        energy = stats["avg_energy"]

        if energy > 0.75:
            style = "HIGH ENERGY DJ"

        elif energy > 0.5:
            style = "BALANCED DJ"

        else:
            style = "WARMUP SPECIALIST"

        return {

            "style": style,

            "top_genre": stats["top_genre"],

            "avg_energy": stats["avg_energy"],

            "avg_bpm": stats["avg_bpm"],

            "peak_ratio": stats["peak_ratio"]
        }
