class DeckEngine:

    def __init__(self):

        self.decks = {
            "A": self.empty_deck("A"),
            "B": self.empty_deck("B"),
        }
        self.crossfader = 0.0

    def empty_deck(self, deck_id):

        return {
            "deck": deck_id,
            "track": None,
            "state": "EMPTY",
            "volume": 1.0,
            "position": 0.0,
        }

    def load(self, deck_id, track):

        deck = self.decks[deck_id]
        deck["track"] = track
        deck["state"] = "LOADED"
        deck["position"] = 0.0

        return deck

    def play(self, deck_id):

        deck = self.decks[deck_id]

        if deck["track"]:
            deck["state"] = "PLAYING"

        return deck

    def stop(self, deck_id):

        deck = self.decks[deck_id]
        deck["state"] = "STOPPED"

        return deck

    def auto_mix_plan(self, from_track, to_track):

        bpm_from = self.number(from_track.get("bpm"), 120)
        bpm_to = self.number(to_track.get("bpm"), 120)
        energy_from = self.number(from_track.get("energy"), 0.5)
        energy_to = self.number(to_track.get("energy"), 0.5)
        phrase_points = to_track.get("phrase_points") or []
        start = self.find_phrase(phrase_points, "START", 0.0)
        build = self.find_phrase(phrase_points, "BUILD", 0.18)

        bpm_diff = abs(bpm_from - bpm_to)
        energy_diff = energy_to - energy_from

        if bpm_diff <= 3:
            mode = "LONG_BLEND"
            bars = 32
        elif bpm_diff <= 6:
            mode = "SHORT_BLEND"
            bars = 16
        else:
            mode = "FILTER_CUT"
            bars = 8

        if energy_diff > 0.18:
            mode = "ENERGY_LIFT"

        return {
            "mode": mode,
            "bars": bars,
            "start_position": start,
            "build_position": build,
            "crossfade_curve": self.crossfade_curve(mode),
            "instruction": (
                f"Deck B'yi {start:.2f} noktasindan hazirla, "
                f"{bars} bar icinde {mode} ile gec."
            ),
        }

    def crossfade_curve(self, mode):

        if mode == "LONG_BLEND":
            return [
                {"time": 0.00, "a": 1.0, "b": 0.0},
                {"time": 0.35, "a": 0.85, "b": 0.45},
                {"time": 0.70, "a": 0.40, "b": 0.85},
                {"time": 1.00, "a": 0.0, "b": 1.0},
            ]

        if mode == "ENERGY_LIFT":
            return [
                {"time": 0.00, "a": 1.0, "b": 0.0},
                {"time": 0.50, "a": 0.70, "b": 0.65},
                {"time": 0.85, "a": 0.20, "b": 1.0},
                {"time": 1.00, "a": 0.0, "b": 1.0},
            ]

        return [
            {"time": 0.00, "a": 1.0, "b": 0.0},
            {"time": 0.50, "a": 0.55, "b": 0.55},
            {"time": 1.00, "a": 0.0, "b": 1.0},
        ]

    def find_phrase(self, phrase_points, label, default):

        for point in phrase_points:
            if point.get("label") == label:
                return float(point.get("position", default) or default)

        return default

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
