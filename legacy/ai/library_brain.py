import os
import hashlib

from app.core.organizer import Organizer


class LibraryBrain:

    def __init__(self, base_folder="DJ_AI_LIBRARY"):
        self.base = base_folder
        self.organizer = Organizer(base_folder)
        os.makedirs(self.base, exist_ok=True)

    # =====================================
    # FILE HASH (DUPLICATE ENGINE)
    # =====================================
    def get_hash(self, path):

        h = hashlib.md5()

        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)

        return h.hexdigest()

    # =====================================
    # CLASSIFY DESTINATION
    # =====================================
    def get_folder(self, genre):

        genre = (genre or "unknown").lower()

        mapping = {
            "house": "house",
            "techno": "techno",
            "deep": "deep_house",
            "afro": "afro_house"
        }

        return mapping.get(genre, "unknown")

    # =====================================
    # STORE TRACK
    # =====================================
    def store(self, track, genre):

        target = self.organizer.safe_copy(
            track,
            {
                "genre": genre,
                "parent_genre": genre,
                "role": "UNSORTED",
            },
            os.path.basename(track)
        )

        status = "linked_existing" if os.path.abspath(target) != os.path.abspath(track) else "already_in_archive"

        return {
            "status": status,
            "path": target
        }
