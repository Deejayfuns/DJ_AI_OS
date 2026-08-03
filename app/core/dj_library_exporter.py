import os
from app.core.organizer import Organizer


class DJLibraryExporter:

    def __init__(self, output_folder="DJ_LIBRARY_OUTPUT"):
        self.output_folder = output_folder
        self.organizer = Organizer(output_folder)

    # =====================================================
    # MAIN EXPORT
    # =====================================================

    def export(self, crates: dict):

        if not crates:
            return {
                "total_copied": 0,
                "folders": {}
            }

        os.makedirs(self.output_folder, exist_ok=True)

        report = {
            "total_copied": 0,
            "folders": {}
        }

        for genre, tracks in crates.items():

            if not tracks:
                continue

            genre_folder = os.path.join(self.output_folder, genre)
            os.makedirs(genre_folder, exist_ok=True)

            copied = 0

            for track in tracks:

                src = self._get_track_path(track)

                if not src:
                    continue

                if not os.path.exists(src):
                    continue

                try:
                    target = self.organizer.safe_copy(
                        src,
                        {
                            "genre": genre,
                            "parent_genre": genre,
                            "role": "UNSORTED",
                        },
                        os.path.basename(src)
                    )

                    if target:
                        copied += 1
                except Exception:
                    # sessiz fail (UI bozulmasın)
                    continue

            report["folders"][genre] = copied
            report["total_copied"] += copied

        return report

    # =====================================================
    # PATH RESOLVER (CRITICAL FIX)
    # =====================================================

    def _get_track_path(self, track: dict):

        if not track:
            return None

        # standart field
        if track.get("id") and isinstance(track["id"], str):
            return track["id"]

        # alternatif alanlar (future-proof)
        if track.get("path"):
            return track["path"]

        if track.get("file"):
            return track["file"]

        return None

