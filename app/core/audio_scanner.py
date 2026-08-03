import os

try:
    from mutagen import File
except Exception:
    File = None


class AudioScanner:

    def __init__(self):
        self.excluded_folder_names = {
            "DJ_LIBRARY_OUTPUT",
            "DJ_LIBRARY_OUTPUT2",
            "DJ_EXPORTS",
            "DJ_REMIX_LAB",
            "DJ_COMMERCIAL",
            "__PYCACHE__",
        }

    # =====================================================
    # SCAN FOLDER
    # =====================================================
    def scan_folder(self, folder_path):

        tracks = []

        if File is None:
            return tracks

        if self.is_excluded_path(folder_path):
            return tracks

        for root, dirs, files in os.walk(folder_path):

            dirs[:] = [
                item
                for item in dirs
                if item.upper() not in self.excluded_folder_names
            ]

            if self.is_excluded_path(root):
                dirs[:] = []
                continue

            for f in files:

                if not f.lower().endswith((".mp3", ".wav", ".flac")):
                    continue

                full_path = os.path.join(root, f)

                track = self.process_file(full_path)

                if track:
                    tracks.append(track)

        return tracks

    def is_excluded_path(self, path):

        try:
            parts = {
                item.upper()
                for item in os.path.abspath(path).split(os.sep)
                if item
            }
        except (TypeError, ValueError):
            return True

        return bool(parts.intersection(self.excluded_folder_names))

    # =====================================================
    # SAFE PROCESS FILE
    # =====================================================
    def process_file(self, path):

        name = os.path.basename(path)

        # DEFAULTS
        bpm = 0
        genre = "UNKNOWN"
        artist = "UNKNOWN"
        duration = 0
        bitrate = 0

        try:
            audio = File(path, easy=True)
            file_size = os.path.getsize(path)

            if audio.info is None:
                return None

            # BPM SAFE
            try:
                if "bpm" in audio:
                    bpm = int(float(audio["bpm"][0]))
            except Exception:
                bpm = 0

            # GENRE SAFE
            try:
                if "genre" in audio:
                    genre = audio["genre"][0]
            except Exception:
                genre = "UNKNOWN"

            # ARTIST SAFE
            try:
                if "artist" in audio:
                    artist = audio["artist"][0]
            except Exception:
                artist = "UNKNOWN"

            # DURATION SAFE
            try:
                duration = int(audio.info.length or 0)
            except Exception:
                duration = 0

            try:
                bitrate = int((audio.info.bitrate or 0) / 1000)
            except Exception:
                bitrate = 0

        except Exception as e:
            print(f"[SCAN ERROR SKIP]: {path}")
            print(e)
            return None

        # =====================================================
        # AI FEATURES (LIGHTWEIGHT)
        # =====================================================

        energy = self.estimate_energy(bpm)
        camelot = self.estimate_camelot(bpm, genre)
        quality = self.estimate_quality(bpm, energy, duration)
        brightness = self.estimate_brightness(genre, bpm)

        return {
            # CORE IDENTITY
            "id": path,
            "path": path,
            "name": name,
            "artist": artist,

            # AUDIO DATA
            "genre": genre,
            "bpm": bpm,
            "duration": duration,
            "bitrate": bitrate,
            "file_size": file_size,

            # AI FEATURES
            "energy": energy,
            "brightness": brightness,
            "camelot": camelot,
            "key": camelot,
            "quality": quality
        }

    # =====================================================
    # ENERGY MODEL
    # =====================================================
    def estimate_energy(self, bpm):

        if bpm <= 0:
            return 0.5

        if bpm < 100:
            return 0.25
        elif bpm < 115:
            return 0.40
        elif bpm < 123:
            return 0.60
        elif bpm < 128:
            return 0.78

        return 0.92

    # =====================================================
    # BRIGHTNESS MODEL (NEW AI FEATURE)
    # =====================================================
    def estimate_brightness(self, genre, bpm):

        genre = str(genre).lower()

        score = 0.5

        if "melodic" in genre:
            score += 0.2

        if "deep" in genre:
            score -= 0.1

        if bpm > 125:
            score += 0.1

        if bpm < 110:
            score -= 0.1

        return max(0.0, min(1.0, score))

    # =====================================================
    # CAMELot KEY ESTIMATION
    # =====================================================
    def estimate_camelot(self, bpm, genre):

        genre = str(genre).lower()

        if "techno" in genre:
            return "11A"
        if "house" in genre:
            return "8A"
        if "melodic" in genre:
            return "10A"
        if "afro" in genre:
            return "9A"

        if bpm < 110:
            return "6A"
        elif bpm < 120:
            return "8A"
        elif bpm < 128:
            return "10A"

        return "11A"

    # =====================================================
    # QUALITY AI
    # =====================================================
    def estimate_quality(self, bpm, energy, duration):

        if duration < 90:
            return "SHORT_TRACK"

        if bpm >= 124 and energy >= 0.75:
            return "PEAK_TIME_TRACK"

        if energy >= 0.65:
            return "STRONG_TRACK"

        if energy <= 0.35:
            return "WARMUP_TRACK"

        return "UTILITY_TRACK"
