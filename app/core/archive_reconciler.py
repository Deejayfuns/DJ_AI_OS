import json
import os

from app.core.organizer import Organizer


class ArchiveReconciler:

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a"}
    ROLE_FOLDERS = {
        "OPENING",
        "WARMUP",
        "GROOVE",
        "PEAK TIME",
        "KINA_RITUAL",
        "UNSORTED",
    }

    def __init__(self, archive_root="DJ_LIBRARY_OUTPUT"):

        self.archive_root = archive_root
        self.organizer = Organizer(archive_root)

    def build_cleanup_plan(self):

        groups = self.group_exact_duplicates()
        duplicate_groups = []
        reclaimable_bytes = 0

        for fingerprint, paths in groups.items():
            if len(paths) < 2:
                continue

            keep = self.choose_keeper(paths)
            duplicates = [
                path
                for path in paths
                if os.path.abspath(path) != os.path.abspath(keep)
            ]
            duplicate_bytes = sum(self.file_size(path) for path in duplicates)
            reclaimable_bytes += duplicate_bytes
            duplicate_groups.append({
                "fingerprint": fingerprint,
                "keep": keep,
                "duplicates": duplicates,
                "duplicate_count": len(duplicates),
                "reclaimable_bytes": duplicate_bytes,
                "recommendation": "REVIEW_THEN_QUARANTINE_DUPLICATES",
            })

        return {
            "archive_root": os.path.abspath(self.archive_root),
            "exists": os.path.exists(self.archive_root),
            "duplicate_groups": sorted(
                duplicate_groups,
                key=lambda group: group["reclaimable_bytes"],
                reverse=True
            ),
            "duplicate_file_count": sum(
                group["duplicate_count"]
                for group in duplicate_groups
            ),
            "reclaimable_bytes": reclaimable_bytes,
            "reclaimable_mb": round(reclaimable_bytes / (1024 * 1024), 2),
            "summary": self.summary(duplicate_groups, reclaimable_bytes),
        }

    def group_exact_duplicates(self):

        groups = {}

        if not os.path.exists(self.archive_root):
            return groups

        for current, _dirs, files in os.walk(self.archive_root):
            for filename in files:
                path = os.path.join(current, filename)

                if not self.is_audio_file(path):
                    continue

                fingerprint = self.organizer.file_fingerprint(path)

                if not fingerprint:
                    continue

                groups.setdefault(fingerprint, []).append(os.path.abspath(path))

        return groups

    def choose_keeper(self, paths):

        def score(path):
            basename = os.path.basename(path)
            normalized = os.path.normpath(path)
            parts = [item.upper() for item in normalized.split(os.sep)]
            parent = parts[-2] if len(parts) >= 2 else ""
            suffix_penalty = 100 if self.has_copy_suffix(basename) else 0
            review_penalty = 80 if "NEEDS_REVIEW" in parts else 0
            pool_penalty = 35 if any(part.startswith("DJ_POOL") for part in parts) else 0
            unstructured_penalty = 30 if parent not in self.ROLE_FOLDERS else 0
            repeated_tag_penalty = max(0, basename.upper().count("BPM") - 1) * 8
            repeated_artist_penalty = 12 if self.has_repeated_artist_prefix(basename) else 0
            path_depth = len(os.path.normpath(path).split(os.sep))
            return (
                suffix_penalty +
                review_penalty +
                pool_penalty +
                unstructured_penalty +
                repeated_tag_penalty +
                repeated_artist_penalty +
                path_depth
            )

        return sorted(paths, key=score)[0]

    def has_copy_suffix(self, filename):

        base, _ext = os.path.splitext(filename)
        return (
            base.endswith("_1") or
            base.endswith("_2") or
            base.endswith("_3") or
            base.endswith(" 1") or
            base.endswith(" 2") or
            base.endswith(" 3")
        )

    def has_repeated_artist_prefix(self, filename):

        base, _ext = os.path.splitext(filename)
        parts = [
            item.strip().upper()
            for item in base.split(" - ")
            if item.strip()
        ]

        return len(parts) >= 2 and parts[0] == parts[1]

    def is_audio_file(self, path):

        return os.path.splitext(path)[1].lower() in self.AUDIO_EXTENSIONS

    def file_size(self, path):

        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    def summary(self, groups, reclaimable_bytes):

        return (
            f"Exact duplicate groups={len(groups)} | "
            f"duplicate_files={sum(group['duplicate_count'] for group in groups)} | "
            f"reclaimable_mb={round(reclaimable_bytes / (1024 * 1024), 2)}"
        )

    def write_plan(self, plan, output_folder="DJ_EXPORTS"):

        os.makedirs(output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(output_folder, "archive_cleanup_plan_latest.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(plan, handle, indent=2, ensure_ascii=False)

        return path

    def quarantine_manifest(self, plan, quarantine_folder="DJ_EXPORTS/QUARANTINE"):

        operations = []

        for group in plan.get("duplicate_groups", []):
            for duplicate in group.get("duplicates", []):
                operations.append({
                    "action": "MOVE_TO_QUARANTINE_AFTER_USER_APPROVAL",
                    "source": duplicate,
                    "target": os.path.abspath(
                        os.path.join(
                            quarantine_folder,
                            os.path.basename(duplicate)
                        )
                    ),
                    "keep": group.get("keep"),
                    "reason": "Exact content duplicate",
                })

        return {
            "archive_root": os.path.abspath(self.archive_root),
            "quarantine_folder": os.path.abspath(quarantine_folder),
            "operation_count": len(operations),
            "operations": operations,
            "safety_note": (
                "Bu manifest dosyalari otomatik tasimaz. DJ onayi olmadan "
                "silme veya tasima yapilmaz."
            ),
        }

    def write_quarantine_manifest(
        self,
        plan,
        output_folder="DJ_EXPORTS",
        quarantine_folder="DJ_EXPORTS/QUARANTINE"
    ):

        os.makedirs(output_folder, exist_ok=True)
        manifest = self.quarantine_manifest(plan, quarantine_folder)
        path = os.path.abspath(
            os.path.join(output_folder, "archive_quarantine_manifest_latest.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

        return path
