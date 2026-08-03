import json
import os


class ExportCenter:

    def __init__(self, output_folder="DJ_EXPORTS"):

        self.output_folder = output_folder

    def export_m3u(self, tracks, name="dj_ai_set"):

        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(self.output_folder, f"{self.safe_name(name)}.m3u")
        )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write("#EXTM3U\n")

            for track in tracks:
                source = track.get("archived_path") or track.get("path") or track.get("id")

                if not source:
                    continue

                duration = int(track.get("duration", -1) or -1)
                title = track.get("name", os.path.basename(source))
                handle.write(f"#EXTINF:{duration},{title}\n")
                handle.write(f"{source}\n")

        return path

    def export_show_manifest(self, show, name="dj_ai_show"):

        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(self.output_folder, f"{self.safe_name(name)}.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(show, handle, indent=2, ensure_ascii=True)

        return path

    def rekordbox_xml_stub(self, tracks, name="dj_ai_rekordbox"):

        os.makedirs(self.output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(self.output_folder, f"{self.safe_name(name)}.xml")
        )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            handle.write('<DJ_PLAYLISTS Version="1.0.0">\n')
            handle.write("  <COLLECTION Entries=\"{}\">\n".format(len(tracks)))

            for index, track in enumerate(tracks, start=1):
                source = track.get("archived_path") or track.get("path") or track.get("id") or ""
                handle.write(
                    "    <TRACK TrackID=\"{}\" Name=\"{}\" Location=\"{}\" "
                    "AverageBpm=\"{}\" Tonality=\"{}\" />\n".format(
                        index,
                        self.xml_escape(track.get("name", "")),
                        self.xml_escape(source),
                        track.get("bpm", ""),
                        self.xml_escape(track.get("camelot", track.get("key", ""))),
                    )
                )

            handle.write("  </COLLECTION>\n")
            handle.write("</DJ_PLAYLISTS>\n")

        return path

    def safe_name(self, value):

        keep = []

        for char in str(value or "export"):
            if char.isalnum() or char in ("-", "_"):
                keep.append(char)
            elif char.isspace():
                keep.append("_")

        return "".join(keep).strip("_") or "export"

    def xml_escape(self, value):

        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
