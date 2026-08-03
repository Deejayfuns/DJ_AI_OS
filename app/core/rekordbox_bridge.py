import json
import os
import shutil
from datetime import datetime

from app.core.export_center import ExportCenter


class RekordboxBridge:

    def __init__(self, output_folder="DJ_EXPORTS"):

        self.output_folder = output_folder
        self.exporter = ExportCenter(output_folder)

    def status(self):

        rekordbox_paths = self.find_rekordbox_paths()

        return {
            "mode": "XML_BRIDGE",
            "direct_control": False,
            "rekordbox_found": bool(rekordbox_paths),
            "rekordbox_paths": rekordbox_paths,
            "output_folder": os.path.abspath(self.output_folder),
            "note": (
                "Guvenli mod: DJ AI OS seti hazirlar, Rekordbox XML/M3U "
                "dosyasina aktarir ve performans talimatlarini uretir."
            ),
        }

    def prepare_ai_performance(self, tracks, name="dj_ai_live_set"):

        os.makedirs(self.output_folder, exist_ok=True)
        playlist_name = self.safe_name(name)
        xml_path = self.exporter.rekordbox_xml_stub(
            tracks,
            f"{playlist_name}_rekordbox_bridge"
        )
        m3u_path = self.exporter.export_m3u(
            tracks,
            f"{playlist_name}_playlist"
        )
        manifest = self.performance_manifest(tracks, xml_path, m3u_path)
        manifest_path = os.path.abspath(
            os.path.join(self.output_folder, f"{playlist_name}_rekordbox_live.json")
        )

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=True)

        return {
            "ok": True,
            "xml_path": xml_path,
            "m3u_path": m3u_path,
            "manifest_path": manifest_path,
            "instructions": self.import_instructions(xml_path),
        }

    def performance_manifest(self, tracks, xml_path, m3u_path):

        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "REKORDBOX_XML_BRIDGE",
            "xml_path": xml_path,
            "m3u_path": m3u_path,
            "track_count": len(tracks),
            "deck_plan": self.deck_plan(tracks),
            "operator_note": (
                "Rekordbox'ta XML Bridge dosyasini sec, playlisti ice aktar, "
                "DJ AI OS'un siralamasina gore cal."
            ),
        }

    def deck_plan(self, tracks):

        plan = []

        for index, track in enumerate(tracks):
            deck = "A" if index % 2 == 0 else "B"
            plan.append({
                "order": index + 1,
                "deck": deck,
                "name": track.get("name", "UNKNOWN"),
                "path": track.get("archived_path") or track.get("path") or track.get("id", ""),
                "bpm": track.get("bpm", ""),
                "camelot": track.get("camelot", track.get("key", "")),
                "role": track.get("role", ""),
                "ai_instruction": self.track_instruction(track, deck),
            })

        return plan

    def track_instruction(self, track, deck):

        bpm = track.get("bpm", "")
        role = track.get("role", "")
        key = track.get("camelot", track.get("key", ""))

        return (
            f"Deck {deck}: {track.get('name', 'UNKNOWN')} yukle. "
            f"BPM {bpm}, ton {key}, rol {role}. "
            "Sonraki parcaya harmonic ve enerji uyumuyla gec."
        )

    def import_instructions(self, xml_path):

        return [
            "Rekordbox'u ac.",
            "File > Preferences > Bridge bolumune git.",
            f"Imported Library alaninda bu XML dosyasini sec: {xml_path}",
            "Sol tarafa gelen rekordbox xml/bridge listesinden playlisti ice aktar.",
            "DJ AI OS deck planini takip ederek seti cal.",
        ]

    def find_rekordbox_paths(self):

        candidates = [
            shutil.which("rekordbox"),
            r"C:\Program Files\rekordbox\rekordbox.exe",
            r"C:\Program Files\Pioneer\rekordbox\rekordbox.exe",
            r"C:\Program Files (x86)\Pioneer\rekordbox\rekordbox.exe",
        ]

        return [
            os.path.abspath(path)
            for path in candidates
            if path and os.path.exists(path)
        ]

    def safe_name(self, value):

        keep = []

        for char in str(value or "dj_ai_live_set"):
            if char.isalnum() or char in ("-", "_"):
                keep.append(char)
            elif char.isspace():
                keep.append("_")

        return "".join(keep).strip("_") or "dj_ai_live_set"
