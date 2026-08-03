import os


class ArchiveBrain:

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aiff", ".aif"}
    GENERATED_FOLDERS = {
        "DJ_LIBRARY_OUTPUT",
        "DJ_LIBRARY_OUTPUT2",
        "DJ_EXPORTS",
        "DJ_REMIX_LAB",
        "DJ_COMMERCIAL",
        "__PYCACHE__",
    }

    def playable_path(self, track):

        for field in ("archived_path", "path", "id"):
            path = track.get(field)

            if path and os.path.exists(path):
                return os.path.abspath(path)

        return ""

    def path_status(self, track):

        playable = self.playable_path(track)

        if playable:
            if os.path.abspath(str(track.get("path") or "")) == playable:
                return "OK_SOURCE"

            if os.path.abspath(str(track.get("archived_path") or "")) == playable:
                return "OK_ARCHIVE_COPY"

            return "OK_RELINKED"

        return "MISSING_FILE"

    def health_report(self, tracks):

        report = {
            "total": len(tracks or []),
            "ok": 0,
            "archive_copy": 0,
            "missing": 0,
            "missing_tracks": [],
        }

        for track in tracks or []:
            status = self.path_status(track)
            track["path_status"] = status

            if status == "MISSING_FILE":
                report["missing"] += 1
                report["missing_tracks"].append(track)
            else:
                report["ok"] += 1

                if status == "OK_ARCHIVE_COPY":
                    report["archive_copy"] += 1

        return report

    def apply_playable_paths(self, tracks):

        relinked = 0

        for track in tracks or []:
            playable = self.playable_path(track)

            if not playable:
                track["path_status"] = "MISSING_FILE"
                continue

            if track.get("path") != playable:
                track["path"] = playable
                relinked += 1

            track["id"] = track.get("id") or playable
            track["path_status"] = self.path_status(track)

        return relinked

    def collect_audio_files(self, folder):

        files = []

        if not folder or not os.path.isdir(folder):
            return files

        if self.is_generated_path(folder):
            return files

        for root, dirs, names in os.walk(folder):
            dirs[:] = [
                item
                for item in dirs
                if item.upper() not in self.GENERATED_FOLDERS
            ]

            if self.is_generated_path(root):
                dirs[:] = []
                continue

            for name in names:
                path = os.path.join(root, name)

                if os.path.splitext(path)[1].lower() in self.AUDIO_EXTENSIONS:
                    files.append(path)

        return files

    def is_generated_path(self, path):

        try:
            parts = {
                item.upper()
                for item in os.path.abspath(path).split(os.sep)
                if item
            }
        except (TypeError, ValueError):
            return True

        return bool(parts.intersection(self.GENERATED_FOLDERS))
