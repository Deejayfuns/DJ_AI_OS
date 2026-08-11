"""
DJ AI OS — Rekordbox XML Import

Two-way Rekordbox integration: parse a Rekordbox XML library export and
turn it into DJ AI OS track dicts (BPM, key, cue points, beatgrid, folder
location). The Deck Studio browser and the library can load these directly.

Rekordbox XML structure (standard exported schema):
    <DJ_PLAYLISTS>
      <PRODUCT .../>
      <COLLECTION Entries="N">
        <TRACK>
          <Location>file:///C:/path/track.mp3</Location>
          <Name>, <Artist>, <Album>, <Genre>, <Bpm>, <Tonality>, <Length>
          <CuePoints Count="n">... </CuePoints>
          <BeatGrid>firstBeat offset, bpm</BeatGrid>
          <Positions>...</Positions>
        </TRACK>
      </COLLECTION>
      <PLAYLISTS>
        <NODE Type="PLAYLIST" Name="...">
          <TRACK Index="i"/> ...
        </NODE>
      </PLAYLISTS>
    </DJ_PLAYLISTS>

Usage:
    importer = RekordboxImporter()
    tracks, playlists = importer.parse("rekordbox.xml")
    deck_browser.load_rekordbox_playlist(playlists[0])
"""

import os
import re
import xml.etree.ElementTree as ET

FILE_URL_RE = re.compile(r"^file://(?:localhost/)?(.*)$", re.IGNORECASE)


def file_url_to_path(url):
    """Convert a Rekordbox file:// URL to a local filesystem path."""
    if not url:
        return ""
    m = FILE_URL_RE.match(url.strip())
    if not m:
        return url
    path = m.group(1)
    # URL-decode percent escapes
    from urllib.parse import unquote
    path = unquote(path)
    # normalize windows path: file:///C:/... -> C:/...
    path = re.sub(r"^/([A-Za-z]:)", r"\1", path)
    return os.path.normpath(path)


def parse_cue_points(cue_text):
    """Parse <CuePoints> text into a list of {time, type, num}."""
    cues = []
    if not cue_text:
        return cues
    # format like "1 60000 0 0 0" per line; first token = cue number,
    # second = time in ms. Tokens after vary (type/color).
    for line in str(cue_text).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            num = int(parts[0])
            ms = float(parts[1])
        except ValueError:
            continue
        cues.append({"time": ms / 1000.0, "type": "cue", "num": num})
    return cues


def parse_beatgrid(grid_text):
    """Parse <BeatGrid> text -> {first_beat_seconds, bpm}."""
    if not grid_text:
        return None
    parts = str(grid_text).strip().split()
    if len(parts) >= 2:
        try:
            return {
                "first_beat": float(parts[0]) / 1000.0,
                "bpm": float(parts[1]),
            }
        except ValueError:
            pass
    return None


def _text(node, tag):
    # Rekordbox exports fields as ATTRIBUTES on <TRACK> (Name, Bpm, Tonality,
    # Location...); some other tools emit them as child elements. Support both.
    val = node.get(tag)
    if val is None:
        el = node.find(tag)
        val = el.text if el is not None and el.text else ""
    return str(val).strip()


def _float(node, tag):
    raw = _text(node, tag)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class RekordboxImporter:
    """Parse a Rekordbox XML export into tracks + playlists."""

    def __init__(self, library_root=None):
        self.library_root = library_root

    def parse(self, xml_path):
        """Return (tracks:list[dict], playlists:list[dict])."""
        if not os.path.isfile(xml_path):
            return [], []
        tree = ET.parse(xml_path)
        root = tree.getroot()

        tracks = self._parse_collection(root)
        playlists = self._parse_playlists(root, len(tracks))
        return tracks, playlists

    def _parse_collection(self, root):
        tracks = []
        collection = root.find("COLLECTION")
        if collection is None:
            return tracks
        for tr in collection.findall("TRACK"):
            location = _text(tr, "Location")
            path = file_url_to_path(location)
            if self.library_root and path and not os.path.isabs(path):
                path = os.path.join(self.library_root, path)
            tonality = _text(tr, "Tonality")
            if not tonality:
                tonality = _text(tr, "MusicalKey")
            cue_el = tr.find("CuePoints")
            cues = parse_cue_points(cue_el.text if cue_el is not None else None)
            grid = parse_beatgrid(_text(tr, "BeatGrid"))
            bpm = _float(tr, "Bpm")
            length_ms = _float(tr, "Length")
            tracks.append({
                "id": f"rb_{len(tracks)}",
                "path": path,
                "location": location,
                "title": _text(tr, "Name") or os.path.basename(path),
                "name": _text(tr, "Name") or os.path.basename(path),
                "artist": _text(tr, "Artist"),
                "album": _text(tr, "Album"),
                "genre": _text(tr, "Genre"),
                "bpm": bpm,
                "key": tonality,
                "camelot": tonality,
                "length": (length_ms / 1000.0) if length_ms else 0.0,
                "duration": (length_ms / 1000.0) if length_ms else 0.0,
                "cue_points": cues,
                "beatgrid": grid,
                "source": "rekordbox",
            })
        return tracks

    def _parse_playlists(self, root, track_count):
        playlists = []
        pl = root.find("PLAYLISTS")
        if pl is None:
            return playlists

        def walk(node, folder=""):
            for child in node.findall("NODE"):
                ntype = child.get("Type", "")
                name = child.get("Name", "")
                if ntype == "PLAYLIST":
                    idx = [int(t.get("Index", "0")) for t in child.findall("TRACK")
                           if t.get("Index", "0").isdigit()]
                    playlists.append({
                        "name": f"{folder}/{name}".strip("/") or name,
                        "folder": folder,
                        "track_indexes": [i for i in idx if i < track_count],
                        "track_count": len(idx),
                    })
                else:
                    walk(child, f"{folder}/{name}".strip("/"))

        walk(pl, "")
        return playlists

    def playlist_tracks(self, playlists, index, all_tracks):
        """Resolve a playlist's track indexes to actual track dicts."""
        if index >= len(playlists):
            return []
        pl = playlists[index]
        return [all_tracks[i] for i in pl["track_indexes"] if i < len(all_tracks)]
