import os
import re
from difflib import SequenceMatcher


class LibraryDoctor:

    def __init__(self):

        self.index = {}

    def build_index(self, tracks):

        self.index = {}

        for track in tracks:
            self.ensure_file_size(track)
            key = self.identity_key(track)

            if key:
                self.index.setdefault(key, []).append(track)

    def inspect(self, track):

        self.ensure_file_size(track)
        suggestion = self.suggest_filename(track)
        key = self.identity_key(track)
        duplicate = self.find_duplicate(track, key)

        result = {
            "suggested_filename": suggestion,
            "identity_key": key,
            "duplicate_status": "UNIQUE",
            "duplicate_confidence": 0,
            "duplicate_match": None,
            "doctor_message": self.build_filename_message(track, suggestion),
        }

        if duplicate:
            result.update(duplicate)

        if key:
            self.index.setdefault(key, []).append(track)

        return result

    def identity_key(self, track):

        artist = self.clean_identity(track.get("artist", ""))
        title = self.clean_identity(track.get("name", ""))

        title = self.strip_extension(title)
        title = self.strip_mix_tokens(title)

        if artist and artist != "unknown":
            return f"{artist}-{title}"

        return title

    def find_duplicate(self, track, key):

        if not key:
            return None

        direct_matches = self.index.get(key, [])

        if direct_matches:
            return self.build_duplicate_result(track, direct_matches[0], 1.0)

        best = None
        best_score = 0

        for existing_key, candidates in self.index.items():
            score = SequenceMatcher(None, key, existing_key).ratio()

            if score > best_score:
                best_score = score
                best = candidates[0]

        if best and best_score >= 0.88:
            return self.build_duplicate_result(track, best, best_score)

        return None

    def build_duplicate_result(self, new_track, old_track, confidence):

        self.ensure_file_size(new_track)
        self.ensure_file_size(old_track)

        old_size = int(old_track.get("file_size", 0) or old_track.get("size", 0) or 0)
        new_size = int(new_track.get("file_size", 0) or new_track.get("size", 0) or 0)
        old_bitrate = int(old_track.get("bitrate", 0) or 0)
        new_bitrate = int(new_track.get("bitrate", 0) or 0)

        recommended = "ASK_DJ"

        if new_bitrate > old_bitrate:
            recommended = "KEEP_NEW_HIGHER_QUALITY"
        elif old_bitrate > new_bitrate:
            recommended = "KEEP_EXISTING_HIGHER_QUALITY"
        elif new_size and old_size and new_size == old_size:
            recommended = "LIKELY_EXACT_COPY"

        return {
            "duplicate_status": "POSSIBLE_DUPLICATE",
            "duplicate_confidence": round(confidence, 2),
            "duplicate_match": {
                "id": old_track.get("id"),
                "name": old_track.get("name"),
                "path": old_track.get("path"),
                "bitrate": old_bitrate,
                "file_size": old_size,
            },
            "recommended_duplicate_action": recommended,
            "doctor_message": (
                "Benzer veya ayni parca yakaladim. "
                f"Yeni: {new_track.get('name', 'UNKNOWN')} "
                f"({new_bitrate} kbps, {self.format_size(new_size)}), mevcut: "
                f"{old_track.get('name', 'UNKNOWN')} "
                f"({old_bitrate} kbps, {self.format_size(old_size)}). "
                "Canli performans riski olmamasi icin kararini soracagim."
            ),
        }

    def ensure_file_size(self, track):

        if not track:
            return 0

        size = int(track.get("file_size", 0) or track.get("size", 0) or 0)

        if size > 0:
            return size

        path = track.get("path") or track.get("id") or track.get("archived_path")

        if path and os.path.exists(path):
            size = os.path.getsize(path)
            track["file_size"] = size

        return size

    def format_size(self, size):

        if not size:
            return "boyut bilinmiyor"

        mb = size / (1024 * 1024)

        if mb >= 1:
            return f"{mb:.1f} MB"

        return f"{size} bytes"

    def suggest_filename(self, track):

        artist = self.clean_display(track.get("artist", "Unknown Artist"))
        title = self.clean_display(track.get("name", "Unknown Track"))
        title = self.strip_extension(title)
        title = self.strip_mix_tokens(title)

        bpm = int(float(track.get("bpm", 0) or 0))
        key = track.get("camelot") or track.get("key") or "NA"
        genre = self.clean_display(self.display_genre(track))
        role = self.clean_display(track.get("role", "Unsorted"))

        parts = [artist, title]
        details = []

        if bpm:
            details.append(f"{bpm}BPM")

        if key and key != "NA":
            details.append(str(key).upper())

        if genre:
            details.append(genre)

        if role:
            details.append(role)

        filename = " - ".join(parts)

        if details:
            filename = f"{filename} ({' - '.join(details)})"

        extension = os.path.splitext(track.get("path", ""))[1] or ".mp3"

        return self.safe_filename(f"{filename}{extension.lower()}")

    def display_genre(self, track):

        genre = str(track.get("genre", "Unknown") or "Unknown")

        if genre.upper().startswith("DISCOVERED_STYLE"):
            return "Needs Review"

        return genre

    def build_filename_message(self, track, suggestion):

        current = os.path.basename(track.get("path", track.get("name", "")))

        if current == suggestion:
            return "Dosya adi arsiv standardina uygun gorunuyor."

        return (
            "Dosya adi icin profesyonel arsiv onerim: "
            f"{suggestion}"
        )

    def clean_identity(self, value):

        value = str(value or "").lower()
        value = self.strip_extension(value)
        value = self.strip_mix_tokens(value)
        value = re.sub(r"[^a-z0-9]+", "", value)

        return value

    def clean_display(self, value):

        value = str(value or "").strip()
        value = self.strip_extension(value)
        value = re.sub(r"[_]+", " ", value)
        value = re.sub(r"\s+", " ", value)

        return value.strip().title()

    def strip_extension(self, value):

        return os.path.splitext(str(value))[0]

    def strip_mix_tokens(self, value):

        patterns = [
            r"\bofficial\b",
            r"\baudio\b",
            r"\bvideo\b",
            r"\blyrics?\b",
            r"\bextended\b",
            r"\boriginal\b",
            r"\bradio edit\b",
            r"\bclub mix\b",
            r"\bremaster(ed)?\b",
            r"\b320kbps\b",
            r"\b\d{4}\b",
        ]

        cleaned = str(value)

        for pattern in patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

        return re.sub(r"\s+", " ", cleaned).strip()

    def safe_filename(self, value):

        value = re.sub(r'[<>:"/\\|?*]', "", value)
        value = re.sub(r"\s+", " ", value)

        return value.strip()
