import os
import re
import json
from collections import Counter

from app.core.paths import get_exports_dir


class ArchiveAuditor:

    AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a")

    def audit(self, root):

        report = {
            "root": os.path.abspath(root),
            "exists": os.path.exists(root),
            "total_audio_files": 0,
            "zero_byte_files": [],
            "legacy_discovered_folders": [],
            "needs_review_files": 0,
            "peak_time_files": 0,
            "tempo_anomalies": [],
            "duplicate_name_groups": [],
            "top_genres": [],
            "health_score": 100,
            "summary": "",
        }

        if not report["exists"]:
            report["health_score"] = 0
            report["summary"] = "Arsiv klasoru bulunamadi."
            return report

        genre_counts = Counter()
        duplicate_candidates = {}

        for current, dirs, files in os.walk(root):
            for dirname in dirs:
                if dirname.upper().startswith("DISCOVERED_STYLE"):
                    report["legacy_discovered_folders"].append(
                        os.path.join(current, dirname)
                    )

            for filename in files:
                if not filename.lower().endswith(self.AUDIO_EXTENSIONS):
                    continue

                path = os.path.join(current, filename)
                report["total_audio_files"] += 1
                parts = self.relative_parts(root, path)

                if parts:
                    genre_counts[parts[0]] += 1

                if "NEEDS_REVIEW" in [part.upper() for part in parts]:
                    report["needs_review_files"] += 1

                if "PEAK TIME" in [part.upper() for part in parts]:
                    report["peak_time_files"] += 1

                duplicate_key = self.duplicate_name_key(filename)
                duplicate_candidates.setdefault(duplicate_key, []).append(path)

                try:
                    size = os.path.getsize(path)
                except OSError:
                    size = 0

                if size <= 0:
                    report["zero_byte_files"].append(path)

                anomaly = self.tempo_anomaly(path)

                if anomaly:
                    report["tempo_anomalies"].append(anomaly)

        report["top_genres"] = genre_counts.most_common(10)
        report["duplicate_name_groups"] = self.duplicate_name_groups(
            duplicate_candidates
        )
        report["health_score"] = self.health_score(report)
        report["summary"] = self.summary(report)

        return report

    def relative_parts(self, root, path):

        relative = os.path.relpath(path, root)
        return relative.split(os.sep)

    def tempo_anomaly(self, path):

        filename = os.path.basename(path)
        matches = re.findall(r"(?<!\d)(\d{2,3})(?:\s|-)*(?:bpm|bpm\))", filename.lower())

        if not matches:
            return None

        bpms = [
            int(value)
            for value in matches
            if 40 <= int(value) <= 260
        ]

        if not bpms:
            return None

        suspicious = [
            bpm
            for bpm in bpms
            if bpm < 70 or bpm > 190
        ]

        if not suspicious:
            return None

        return {
            "path": path,
            "bpms": bpms,
            "issue": "HALF_OR_DOUBLE_TEMPO_SUSPECT",
        }

    def health_score(self, report):

        score = 100
        score -= min(35, len(report["zero_byte_files"]) * 5)
        score -= min(25, len(report["legacy_discovered_folders"]) * 4)
        score -= min(20, len(report["tempo_anomalies"]) * 2)
        score -= min(25, len(report["duplicate_name_groups"]) * 3)

        total = max(report["total_audio_files"], 1)
        needs_review_ratio = report["needs_review_files"] / total
        score -= min(20, int(needs_review_ratio * 30))

        return max(0, score)

    def summary(self, report):

        return (
            f"Archive health {report['health_score']}/100 | "
            f"files={report['total_audio_files']} | "
            f"zero={len(report['zero_byte_files'])} | "
            f"legacy_discovered={len(report['legacy_discovered_folders'])} | "
            f"tempo_risk={len(report['tempo_anomalies'])} | "
            f"duplicates={len(report['duplicate_name_groups'])} | "
            f"needs_review={report['needs_review_files']}"
        )

    def duplicate_name_key(self, filename):

        base, ext = os.path.splitext(filename)
        base = re.sub(r"[_\-\s]*(?:copy|kopya|\(\d+\)|\d+)$", "", base, flags=re.IGNORECASE)
        base = re.sub(r"[_\-\s]+", " ", base)

        return f"{base.strip().lower()}|{ext.lower()}"

    def duplicate_name_groups(self, candidates):

        groups = []

        for key, paths in candidates.items():
            if len(paths) < 2:
                continue

            groups.append({
                "key": key,
                "count": len(paths),
                "paths": paths,
                "issue": "POSSIBLE_RENAMED_DUPLICATES",
            })

        return sorted(groups, key=lambda group: group["count"], reverse=True)

    def write_report(self, report, output_folder=None):

        if output_folder is None:
            output_folder = str(get_exports_dir())
        os.makedirs(output_folder, exist_ok=True)
        path = os.path.join(output_folder, "archive_audit_latest.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return os.path.abspath(path)
