import os
import re
from urllib.parse import quote_plus


class MusicResearchAssistant:

    def __init__(self):

        self.sources = {
            "beatport": "https://www.beatport.com/search?q={query}",
            "soundcloud": "https://soundcloud.com/search?q={query}",
            "youtube": "https://www.youtube.com/results?search_query={query}",
            "spotify": "https://open.spotify.com/search/{query}",
            "discogs": "https://www.discogs.com/search/?q={query}&type=all",
            "musicbrainz": "https://musicbrainz.org/search?query={query}&type=recording&method=indexed",
        }

    def prepare_research(self, track):

        query = self.build_query(track)
        encoded = quote_plus(query)
        links = {
            name: template.format(query=encoded)
            for name, template in self.sources.items()
        }

        needs_research = self.needs_research(track)
        artwork_status = self.artwork_status(track)
        hit_status = self.hit_status(track)

        return {
            "research_status": "NEEDS_REVIEW" if needs_research else "READY",
            "research_query": query,
            "research_links": links,
            "artwork_status": artwork_status,
            "album_art_url": track.get("album_art_url", ""),
            "hit_status": hit_status,
            "release_year": track.get("release_year", ""),
            "label": track.get("label", ""),
            "external_metadata": {},
            "research_message": self.build_message(
                track,
                needs_research,
                artwork_status,
                hit_status
            ),
        }

    def build_query(self, track):

        artist = self.clean_query_part(track.get("artist", ""))
        title = self.clean_query_part(track.get("name", ""))
        title = self.strip_extension(title)
        title = self.strip_noise(title)

        parts = [
            part for part in [artist, title]
            if part and part.lower() != "unknown"
        ]

        if not parts:
            parts = [self.strip_extension(track.get("name", "unknown track"))]

        genre = track.get("genre", "")

        if genre and genre.upper() not in ("UNKNOWN", "DISCOVERED"):
            parts.append(str(genre))

        return " ".join(parts).strip()

    def needs_research(self, track):

        confidence = float(track.get("confidence", 0) or 0)
        artist = str(track.get("artist", "")).lower()
        genre = str(track.get("genre", "")).upper()

        return (
            confidence < 0.65 or
            artist in ("", "unknown") or
            genre.startswith("DISCOVERED_STYLE") or
            genre in ("", "UNKNOWN")
        )

    def artwork_status(self, track):

        if track.get("album_art_url") or track.get("album_art_path"):
            return "READY"

        return "MISSING"

    def hit_status(self, track):

        genre = str(track.get("genre", "")).upper()
        parent = str(track.get("parent_genre", "")).upper()
        role = str(track.get("role", "")).upper()
        energy = float(track.get("energy", 0) or 0)

        if parent == "WEDDING & EVENT":
            if role in ("DANCE_FLOOR_STARTER", "KINA_RITUAL"):
                return "EVENT_FLOOR_ESSENTIAL"

            return "EVENT_LIBRARY_CANDIDATE"

        if "PEAK" in role and energy >= 0.75:
            return "CLUB_READY_CANDIDATE"

        if genre in ("POP", "EDM", "BIG ROOM", "MAINSTAGE"):
            return "COMMERCIAL_CANDIDATE"

        return "UNKNOWN"

    def build_message(self, track, needs_research, artwork_status, hit_status):

        name = track.get("name", "UNKNOWN")

        if track.get("parent_genre") == "WEDDING & EVENT":
            return (
                f"{name} dugun/kina/event arsivi icin isaretlendi. "
                "Bu tur parcalarda bolge, rituel ani ve istek potansiyeli "
                "kontrol edilmeli."
            )

        if needs_research:
            return (
                f"{name} icin internet arastirmasi oneriyorum. "
                "Beatport, SoundCloud, YouTube, Spotify, Discogs ve "
                "MusicBrainz arama linklerini hazirladim."
            )

        if artwork_status == "MISSING":
            return (
                f"{name} metadata olarak guvenli gorunuyor ama album kapagi "
                "eksik. Kapak guncellemesi icin arastirma oneriyorum."
            )

        if hit_status != "UNKNOWN":
            return (
                f"{name} sahne icin guclu aday gorunuyor: {hit_status}."
            )

        return (
            f"{name} icin temel metadata yeterli gorunuyor. "
            "Istersen yine de online dogrulama yapabiliriz."
        )

    def clean_query_part(self, value):

        value = str(value or "")
        value = re.sub(r"[_]+", " ", value)
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def strip_extension(self, value):

        return os.path.splitext(str(value))[0]

    def strip_noise(self, value):

        patterns = [
            r"\bofficial\b",
            r"\baudio\b",
            r"\bvideo\b",
            r"\blyrics?\b",
            r"\bextended\b",
            r"\boriginal\b",
            r"\bradio edit\b",
            r"\bclub mix\b",
            r"\bremix\b",
            r"\bbootleg\b",
            r"\b320kbps\b",
            r"\b\d{4}\b",
        ]

        cleaned = str(value)

        for pattern in patterns:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

        return re.sub(r"\s+", " ", cleaned).strip()
