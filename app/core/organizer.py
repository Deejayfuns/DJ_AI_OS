import os
import shutil
import hashlib


class Organizer:

    def __init__(self, output_folder):
        self.output_folder = output_folder
        self._fingerprint_index = None

    def sanitize(self, text):
        invalid = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

        for c in invalid:
            text = text.replace(c, "")

        return text.strip().upper()

    def build_path(self, prediction):

        genre = self.archive_genre(prediction)

        role = self.sanitize(
            prediction.get("role", "UNSORTED")
        )

        return os.path.join(
            self.output_folder,
            genre,
            role
        )

    def archive_genre(self, prediction):

        genre = str(prediction.get("genre", "UNKNOWN") or "UNKNOWN")
        parent = str(
            prediction.get("parent_genre", "") or ""
        )
        discovery = str(
            prediction.get("discovery_status", "") or ""
        )

        if (
            discovery == "DISCOVERED" or
            genre.upper().startswith("DISCOVERED_STYLE") or
            parent.upper() in {"UNKNOWN", ""}
        ):
            return "NEEDS_REVIEW"

        return self.sanitize(genre)

    def safe_copy(self, source_path, prediction, target_filename=None):

        source_path = os.path.abspath(source_path)

        if self.is_inside_archive(source_path):
            return source_path

        source_fingerprint = self.file_fingerprint(source_path)
        existing = self.find_existing_by_fingerprint(source_fingerprint)

        if existing:
            return existing

        target_dir = self.build_path(prediction)

        os.makedirs(target_dir, exist_ok=True)

        filename = target_filename or os.path.basename(source_path)
        filename = self.sanitize_filename(filename)

        target_path = os.path.join(target_dir, filename)

        # duplicate protection
        if os.path.exists(target_path):
            if self.same_file_content(source_path, target_path, source_fingerprint):
                self.register_fingerprint(source_fingerprint, target_path)
                return target_path

            raise FileExistsError(
                "ARCHIVE_FILENAME_COLLISION: hedef isim dolu ama icerik farkli. "
                f"Kaynak={source_path} | Hedef={target_path}"
            )

        shutil.copy2(source_path, target_path)
        self.register_fingerprint(source_fingerprint, target_path)

        return target_path

    def is_inside_archive(self, path):

        try:
            root = os.path.abspath(self.output_folder)
            return os.path.commonpath([root, path]) == root
        except ValueError:
            return False

    def find_existing_by_fingerprint(self, fingerprint):

        if not fingerprint:
            return ""

        if self._fingerprint_index is None:
            self._fingerprint_index = self.build_fingerprint_index()

        return self._fingerprint_index.get(fingerprint, "")

    def build_fingerprint_index(self):

        index = {}

        if not os.path.exists(self.output_folder):
            return index

        for current, _dirs, files in os.walk(self.output_folder):
            for filename in files:
                path = os.path.join(current, filename)

                if not self.is_audio_file(path):
                    continue

                fingerprint = self.file_fingerprint(path)

                if fingerprint:
                    index.setdefault(fingerprint, os.path.abspath(path))

        return index

    def register_fingerprint(self, fingerprint, path):

        if not fingerprint:
            return

        if self._fingerprint_index is None:
            self._fingerprint_index = {}

        self._fingerprint_index.setdefault(fingerprint, os.path.abspath(path))

    def same_file_content(self, source_path, target_path, source_fingerprint=None):

        source_fingerprint = source_fingerprint or self.file_fingerprint(source_path)
        target_fingerprint = self.file_fingerprint(target_path)

        return bool(
            source_fingerprint and
            target_fingerprint and
            source_fingerprint == target_fingerprint
        )

    def file_fingerprint(self, path):

        if not path or not os.path.exists(path):
            return ""

        try:
            size = os.path.getsize(path)
        except OSError:
            return ""

        digest = hashlib.sha1()
        digest.update(str(size).encode("ascii"))

        try:
            with open(path, "rb") as handle:
                self.hash_sample(handle, digest, 0)

                if size > 2 * 1024 * 1024:
                    self.hash_sample(handle, digest, max(0, size // 2))
                    self.hash_sample(handle, digest, max(0, size - 1024 * 1024))
        except OSError:
            return ""

        return f"{size}:{digest.hexdigest()}"

    def hash_sample(self, handle, digest, offset):

        handle.seek(offset)
        digest.update(handle.read(1024 * 1024))

    def is_audio_file(self, path):

        return os.path.splitext(path)[1].lower() in {
            ".mp3",
            ".wav",
            ".flac",
            ".aiff",
            ".aif",
            ".m4a",
        }

    def sanitize_filename(self, filename):

        base, ext = os.path.splitext(filename)
        clean_base = self.sanitize(base).title()
        clean_ext = ext.lower() or ".mp3"

        return f"{clean_base}{clean_ext}"
