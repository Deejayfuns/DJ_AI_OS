class SetCurveEngine:

    def __init__(self):

        self.curve = [
            "intro",
            "warmup",
            "groove",
            "build",
            "peak",
            "afterglow",
            "exit"
        ]

    # ---------------------------
    # ASSIGN TRACK TO CURVE
    # ---------------------------

    def assign_curve(self, tracks):

        if not tracks:
            return {}

        tracks = sorted(tracks, key=lambda x: x.get("energy", 0))

        result = {c: [] for c in self.curve}

        n = len(tracks)

        for i, track in enumerate(tracks):

            position = i / n

            curve_stage = self.map_position(position)

            result[curve_stage].append(track)

        return result

    # ---------------------------
    # POSITION MAPPING
    # ---------------------------

    def map_position(self, p):

        if p < 0.1:
            return "intro"

        elif p < 0.25:
            return "warmup"

        elif p < 0.45:
            return "groove"

        elif p < 0.65:
            return "build"

        elif p < 0.85:
            return "peak"

        elif p < 0.95:
            return "afterglow"

        return "exit"
