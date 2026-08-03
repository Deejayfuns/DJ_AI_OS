class LibraryClassifier:

    def __init__(self):
        pass

    # -------------------------
    # MAIN CLASSIFY FUNCTION
    # -------------------------

    def classify(self, track):

        bpm = track.get("bpm", 0)
        energy = track.get("energy", 0)
        genre = (track.get("genre") or "").lower()

        # -------------------------
        # DJ ROLE DETECTION
        # -------------------------

        role = self.detect_dj_role(bpm, energy)

        # -------------------------
        # STYLE CLASSIFICATION
        # -------------------------

        style = self.detect_style(genre, bpm, energy)

        # -------------------------
        # FOLDER SUGGESTION
        # -------------------------

        folder = self.suggest_folder(style, role)

        return {
            **track,
            "dj_role": role,
            "style": style,
            "folder": folder
        }

    # -------------------------
    # DJ ROLE ENGINE
    # -------------------------

    def detect_dj_role(self, bpm, energy):

        if energy < 0.4:
            return "WARMUP"

        if energy < 0.65:
            return "GROOVE"

        if energy < 0.8:
            return "PEAK"

        return "HARD_PEAK"

    # -------------------------
    # STYLE ENGINE
    # -------------------------

    def detect_style(self, genre, bpm, energy):

        if "afro" in genre:
            return "AFRO_HOUSE"

        if "melodic" in genre:
            return "MELODIC_TECHNO"

        if bpm > 128 and energy > 0.75:
            return "PEAK_TECHNO"

        if "house" in genre:
            return "DEEP_HOUSE"

        return "UNKNOWN"

    # -------------------------
    # FOLDER SYSTEM (DJ ARCHIVE)
    # -------------------------

    def suggest_folder(self, style, role):

        return f"{style}/{role}"
