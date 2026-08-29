import json
import os
from datetime import datetime

from app.ai.show_director import ShowDirector
from app.core.export_center import ExportCenter
from app.core.paths import get_exports_dir
from app.core.rekordbox_bridge import RekordboxBridge


class GigPackBuilder:

    def __init__(self, output_folder=None):

        self.output_folder = output_folder or str(get_exports_dir())
        self.exporter = ExportCenter(self.output_folder)
        self.rekordbox = RekordboxBridge(self.output_folder)
        self.show_director = ShowDirector()

    def build(self, tracks, style="AFRO HOUSE", hours=4, name="dj_ai_gig_pack"):

        tracks = list(tracks or [])

        if not tracks:
            return {
                "ok": False,
                "reason": "NO_TRACKS",
                "message": "Gig Pack icin once analiz edilmis parca veya set gerekli.",
            }

        pack_name = self.safe_name(name)
        pack_folder = os.path.abspath(
            os.path.join(self.output_folder, pack_name)
        )
        os.makedirs(pack_folder, exist_ok=True)

        show = self.show_director.build_show(tracks, style, hours)
        rescue_tracks = show.get("rescue_tracks", [])
        rekordbox = RekordboxBridge(pack_folder).prepare_ai_performance(
            tracks,
            pack_name
        )
        rescue_m3u = ExportCenter(pack_folder).export_m3u(
            rescue_tracks,
            f"{pack_name}_rescue_crate"
        )
        show_path = self.write_json(
            pack_folder,
            f"{pack_name}_show_director.json",
            show
        )
        briefing_path = self.write_text(
            pack_folder,
            f"{pack_name}_dj_briefing.txt",
            self.briefing_text(tracks, show, rekordbox)
        )
        manifest = {
            "ok": True,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "style": style,
            "hours": hours,
            "track_count": len(tracks),
            "pack_folder": pack_folder,
            "rekordbox_xml": rekordbox["xml_path"],
            "playlist_m3u": rekordbox["m3u_path"],
            "rekordbox_manifest": rekordbox["manifest_path"],
            "show_director": show_path,
            "rescue_crate_m3u": rescue_m3u,
            "briefing": briefing_path,
            "headline": self.headline(tracks, show),
        }
        manifest_path = self.write_json(
            pack_folder,
            f"{pack_name}_manifest.json",
            manifest
        )
        manifest["manifest_path"] = manifest_path

        return manifest

    def headline(self, tracks, show):

        avg_bpm = self.average(tracks, "bpm")
        avg_energy = self.average(tracks, "energy")
        rescue = show.get("rescue_tracks", [])

        return (
            f"{len(tracks)} parcali gig pack hazir. "
            f"Ortalama BPM {avg_bpm}, enerji {avg_energy}. "
            f"Rescue crate: {len(rescue)} parca."
        )

    def briefing_text(self, tracks, show, rekordbox):

        lines = [
            "DJ AI OS - GIG BRIEFING",
            "",
            self.headline(tracks, show),
            "",
            "Rekordbox hazirlik:",
        ]
        lines.extend(f"- {step}" for step in rekordbox["instructions"])
        lines.extend(["", "Show akisi:"])

        for segment in show.get("segments", []):
            lines.append(
                f"- {segment['name']}: {segment['purpose']} "
                f"Risk: {segment['risk']}. {segment['instruction']}"
            )

        lines.extend(["", "Rescue crate:"])

        for track in show.get("rescue_tracks", []):
            lines.append(
                f"- {track.get('name', 'UNKNOWN')} | "
                f"BPM {track.get('bpm', '')} | "
                f"{track.get('director_cue', '')}"
            )

        lines.extend(["", f"Director notu: {show.get('director_note', '')}"])

        return "\n".join(lines)

    def write_json(self, folder, filename, payload):

        path = os.path.abspath(os.path.join(folder, filename))

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)

        return path

    def write_text(self, folder, filename, text):

        path = os.path.abspath(os.path.join(folder, filename))

        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

        return path

    def average(self, tracks, field):

        values = []

        for track in tracks:
            try:
                value = float(track.get(field, 0) or 0)
            except (TypeError, ValueError):
                continue

            if value > 0:
                values.append(value)

        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def safe_name(self, value):

        keep = []

        for char in str(value or "dj_ai_gig_pack"):
            if char.isalnum() or char in ("-", "_"):
                keep.append(char)
            elif char.isspace():
                keep.append("_")

        return "".join(keep).strip("_") or "dj_ai_gig_pack"
