import os
import json
import shutil
import hashlib
import time


class Organizer:

    CACHE_FILE = ".fingerprint_cache.json"

    def __init__(self, output_folder):
        self.output_folder = output_folder
        self._fingerprint_index = None
        self._cache_loaded = False

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

        # Try loading from cache first
        index = self.load_fingerprint_cache()

        if not os.path.exists(self.output_folder):
            return index

        existing_paths = set(index.values())

        for current, _dirs, files in os.walk(self.output_folder):
            for filename in files:
                path = os.path.join(current, filename)

                if not self.is_audio_file(path):
                    continue

                abs_path = os.path.abspath(path)

                # Skip if already cached and file hasn't changed
                if abs_path in existing_paths:
                    continue

                fingerprint = self.file_fingerprint(path)

                if fingerprint:
                    index[fingerprint] = abs_path

        # Save updated cache
        self.save_fingerprint_cache(index)

        return index

    def load_fingerprint_cache(self):
        """Load fingerprint index from disk cache."""
        cache_path = self.cache_path()

        if not os.path.exists(cache_path):
            return {}

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # Validate: filter out paths that no longer exist
            valid = {
                fp: path
                for fp, path in cached.items()
                if os.path.exists(path)
            }

            self._cache_loaded = True
            return valid

        except (json.JSONDecodeError, OSError):
            return {}

    def save_fingerprint_cache(self, index):
        """Save fingerprint index to disk cache."""
        try:
            cache_path = self.cache_path()
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=None, ensure_ascii=False)

        except OSError:
            pass  # Non-critical; cache is optional

    def cache_path(self):
        """Return the fingerprint cache file path."""
        return os.path.join(self.output_folder, self.CACHE_FILE)

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
                if size <= 2 * 1024 * 1024:
                    # Small file: hash everything
                    digest.update(handle.read())
                elif size <= 50 * 1024 * 1024:
                    # Medium file: first 1MB + middle 1MB + last 1MB
                    self.hash_sample(handle, digest, 0)
                    self.hash_sample(handle, digest, max(0, size // 2))
                    self.hash_sample(handle, digest, max(0, size - 1024 * 1024))
                else:
                    # Large file (50MB+): first 1MB + last 1MB (skip middle)
                    self.hash_sample(handle, digest, 0)
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
