import os
from mutagen import File


class DuplicateDetector:

    def __init__(self):

        self.index = {}

    # ---------------------------
    # MAIN CHECK
    # ---------------------------

    def check(self, file_path):

        try:
            audio = File(file_path)
        except:
            return None

        if not audio:
            return None

        # metadata
        size = os.path.getsize(file_path)
        bitrate = self.get_bitrate(audio)

        key = self.create_key(file_path, audio)

        if key in self.index:

            existing = self.index[key]

            return {
                "duplicate": True,
                "existing": existing,
                "new": {
                    "path": file_path,
                    "bitrate": bitrate,
                    "size": size
                }
            }

        self.index[key] = {
            "path": file_path,
            "bitrate": bitrate,
            "size": size
        }

        return {"duplicate": False}

    # ---------------------------
    # KEY GENERATOR (basic fingerprint)
    # ---------------------------

    def create_key(self, path, audio):

        # basit fingerprint (sonra AI upgrade yapılacak)
        name = os.path.basename(path).lower()

        return name.replace(" ", "")

    # ---------------------------
    # BITRATE
    # ---------------------------

    def get_bitrate(self, audio):

        try:
            return audio.info.bitrate
        except:
            return 0
