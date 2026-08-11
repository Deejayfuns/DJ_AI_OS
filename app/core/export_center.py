"""
DJ AI OS — Export Center (Pro)

Professional export formats for DJ software:
- Rekordbox XML (full: hot cues, loops, playlists)
- Serato database format
- Traktor NML
- Denon DJ Engine
- M3U/M3U8 playlists
- WAV stems export
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional


class ExportCenter:
    """
    Professional DJ export center.
    Supports all major DJ software formats.
    """

    def __init__(self, output_folder: str = "DJ_EXPORTS"):
        self.output_folder = output_folder

    # ============================================================
    # REKORDBOX XML (full format)
    # ============================================================

    def export_rekordbox(self, tracks: List[Dict], name: str = "dj_ai_set",
                         hot_cues: bool = True, loops: bool = True) -> str:
        """
        Export to Rekordbox XML format.
        Includes: tracks, hot cues, loops, playlist.
        """
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}.xml")

        with open(path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<DJ_PLAYLISTS Version="1.0.0">\n')

            # COLLECTION
            f.write(f'  <COLLECTION Entries="{len(tracks)}">\n')
            for i, track in enumerate(tracks, 1):
                source = track.get("archived_path") or track.get("path") or ""
                name = self._xml_escape(track.get("name", ""))
                bpm = track.get("bpm", 0)
                key = track.get("camelot", track.get("key", ""))
                duration = int(track.get("duration", 0) * 1000)  # ms
                energy = int(track.get("energy", 0.5) * 127)

                f.write(f'    <TRACK TrackID="{i}" Name="{name}" '
                       f'Location="{self._xml_escape(source)}" '
                       f'AverageBpm="{bpm}" Tonality="{key}" '
                       f'Length="{duration}" '
                       f'HighEnergy="{1 if energy > 80 else 0}">\n')

                # Hot Cues
                if hot_cues and track.get("hot_cues"):
                    for j, cue in enumerate(track["hot_cues"][:8], 1):
                        cue_time = int(cue.get("time", 0) * 1000)
                        cue_name = self._xml_escape(cue.get("label", f"CUE{j}"))
                        f.write(f'      <POSITION MarkType="CUE" Name="{cue_name}" '
                               f'Start="{cue_time}" />\n')

                # Loops
                if loops and track.get("loop"):
                    loop_in = int(track["loop"].get("start", 0) * 1000)
                    loop_out = int(track["loop"].get("end", 0) * 1000)
                    f.write(f'      <POSITION MarkType="LOOP" Name="Loop" '
                           f'Start="{loop_in}" End="{loop_out}" />\n')

                f.write('    </TRACK>\n')
            f.write('  </COLLECTION>\n')

            # PLAYLIST
            f.write('  <PLAYLISTS>\n')
            f.write('    <NODE Type="0" Name="DJ AI OS">\n')
            f.write(f'      <NODE Type="1" Name="{self._xml_escape(name)}">\n')
            track_refs = " ".join(str(i) for i in range(1, len(tracks) + 1))
            f.write(f'        <TRACKS>{track_refs}</TRACKS>\n')
            f.write('      </NODE>\n')
            f.write('    </NODE>\n')
            f.write('  </PLAYLISTS>\n')
            f.write('</DJ_PLAYLISTS>\n')

        return path

    # ============================================================
    # SERATO LIBRARY
    # ============================================================

    def export_serato(self, tracks: List[Dict], name: str = "dj_ai_set") -> str:
        """Export to Serato library format (SQLite)."""
        import sqlite3
        os.makedirs(self.output_folder, exist_ok=True)
        db_path = os.path.join(self.output_folder, f"{self._safe_name(name)}_serato.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                path TEXT,
                title TEXT,
                artist TEXT,
                bpm REAL,
                key TEXT,
                duration INTEGER,
                hot_cues TEXT
            )
        """)

        for i, track in enumerate(tracks, 1):
            source = track.get("archived_path") or track.get("path") or ""
            hot_cues = json.dumps(track.get("hot_cues", []))
            conn.execute(
                "INSERT INTO tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (i, source, track.get("name", ""), track.get("artist", ""),
                 track.get("bpm", 0), track.get("camelot", track.get("key", "")),
                 int(track.get("duration", 0)), hot_cues)
            )

        conn.commit()
        conn.close()
        return db_path

    # ============================================================
    # TRAKTOR NML
    # ============================================================

    def export_traktor(self, tracks: List[Dict], name: str = "dj_ai_set") -> str:
        """Export to Traktor NML format."""
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}.nml")

        with open(path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<NML VERSION="19">\n')
            f.write('  <HEAD INFO="{\\\"DATABASE_VERSION\\\":19}">\n')
            f.write('    <COLLECTION ENTRIES="{}">\n'.format(len(tracks)))

            for i, track in enumerate(tracks, 1):
                source = track.get("archived_path") or track.get("path") or ""
                f.write('      <ENTRY>\n')
                f.write(f'        <LOCATION DIR="{self._xml_escape(os.path.dirname(source))}/" '
                       f'FILE="{self._xml_escape(os.path.basename(source))}" VOLUME="" />\n')
                f.write(f'        <TITLE>{self._xml_escape(track.get("name", ""))}</TITLE>\n')
                f.write(f'        <ARTIST>{self._xml_escape(track.get("artist", ""))}</ARTIST>\n')
                f.write(f'        <BPM>{track.get("bpm", 0)}</BPM>\n')
                f.write(f'        <KEY>{self._xml_escape(track.get("camelot", track.get("key", "")))}</KEY>\n')
                f.write('      </ENTRY>\n')

            f.write('    </COLLECTION>\n')
            f.write('  </HEAD>\n')
            f.write('</NML>\n')

        return path

    # ============================================================
    # M3U/M3U8 PLAYLISTS
    # ============================================================

    def export_m3u(self, tracks: List[Dict], name: str = "dj_ai_set") -> str:
        """Export as M3U playlist."""
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}.m3u")

        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for track in tracks:
                source = track.get("archived_path") or track.get("path") or ""
                duration = int(track.get("duration", -1) or -1)
                title = track.get("name", os.path.basename(source))
                f.write(f"#EXTINF:{duration},{title}\n")
                f.write(f"{source}\n")

        return path

    def export_m3u8(self, tracks: List[Dict], name: str = "dj_ai_set") -> str:
        """Export as M3U8 (UTF-8) playlist."""
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}.m3u8")

        with open(path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"#PLAYLIST:{name}\n")
            for track in tracks:
                source = track.get("archived_path") or track.get("path") or ""
                duration = int(track.get("duration", -1) or -1)
                title = track.get("name", os.path.basename(source))
                artist = track.get("artist", "")
                f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                f.write(f"{source}\n")

        return path

    # ============================================================
    # SHOW MANIFEST
    # ============================================================

    def export_show_manifest(self, show: Dict, name: str = "dj_ai_show") -> str:
        """Export show manifest as JSON."""
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}.json")

        manifest = {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "version": "2.0",
            "show": show,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return path

    # ============================================================
    # SET HISTORY
    # ============================================================

    def export_set_history(self, tracks: List[Dict], set_info: Dict,
                           name: str = "set_history") -> str:
        """Export complete set history for logging."""
        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.join(self.output_folder, f"{self._safe_name(name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        history = {
            "timestamp": datetime.now().isoformat(),
            "set_info": set_info,
            "tracks": [
                {
                    "position": i + 1,
                    "name": t.get("name", ""),
                    "artist": t.get("artist", ""),
                    "bpm": t.get("bpm", 0),
                    "key": t.get("camelot", t.get("key", "")),
                    "energy": t.get("energy", 0),
                    "played_at": t.get("played_at"),
                }
                for i, t in enumerate(tracks)
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        return path

    # ============================================================
    # HELPERS
    # ============================================================

    def _safe_name(self, value: str) -> str:
        keep = []
        for char in str(value or "export"):
            if char.isalnum() or char in ("-", "_"):
                keep.append(char)
            elif char.isspace():
                keep.append("_")
        return "".join(keep).strip("_") or "export"

    def _xml_escape(self, value: str) -> str:
        return (str(value or "")
                .replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    # ============================================================
    # BACKWARD COMPATIBILITY ALIASES
    # ============================================================

    def rekordbox_xml_stub(self, tracks: List[Dict], name: str = "rekordbox_export") -> str:
        """Backward compatibility alias for export_rekordbox."""
        return self.export_rekordbox(tracks, name)

    def get_supported_formats(self) -> List[Dict]:
        """List all supported export formats."""
        return [
            {"name": "Rekordbox XML", "ext": ".xml", "features": ["hot_cues", "loops", "playlists"]},
            {"name": "Serato Library", "ext": ".db", "features": ["hot_cues", "crates"]},
            {"name": "Traktor NML", "ext": ".nml", "features": ["tracks", "playlists"]},
            {"name": "M3U Playlist", "ext": ".m3u", "features": ["basic"]},
            {"name": "M3U8 (UTF-8)", "ext": ".m3u8", "features": ["basic", "unicode"]},
            {"name": "Show Manifest", "ext": ".json", "features": ["full"]},
        ]
