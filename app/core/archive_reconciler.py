import json
import os

from app.core.organizer import Organizer
from app.core.paths import get_exports_dir, get_library_output_dir


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

    def __init__(self, archive_root=None):

        if archive_root is None:
            archive_root = str(get_library_output_dir())
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

    def write_plan(self, plan, output_folder=None):

        if output_folder is None:
            output_folder = str(get_exports_dir())
        os.makedirs(output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(output_folder, "archive_cleanup_plan_latest.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(plan, handle, indent=2, ensure_ascii=False)

        return path

    def quarantine_manifest(self, plan, quarantine_folder=None):

        if quarantine_folder is None:
            quarantine_folder = os.path.join(str(get_exports_dir()), "QUARANTINE")

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
        output_folder=None,
        quarantine_folder=None
    ):

        if output_folder is None:
            output_folder = str(get_exports_dir())
        if quarantine_folder is None:
            quarantine_folder = os.path.join(str(get_exports_dir()), "QUARANTINE")

        os.makedirs(output_folder, exist_ok=True)
        manifest = self.quarantine_manifest(plan, quarantine_folder)
        path = os.path.abspath(
            os.path.join(output_folder, "archive_quarantine_manifest_latest.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

        return path

    # =====================================================
    # QUARANTINE EXECUTION (real move, no delete)
    # =====================================================

    def execute_quarantine(
        self,
        manifest,
        dry_run=True,
        quarantine_folder=None,
    ):
        """Move duplicate files to quarantine folder.

        Args:
            manifest: dict from quarantine_manifest()
            dry_run: if True, only report what would happen
            quarantine_folder: override quarantine target dir

        Returns:
            dict with actions_taken / actions_planned + log_path
        """
        qfolder = quarantine_folder or manifest.get(
            "quarantine_folder",
            os.path.join(str(get_exports_dir()), "QUARANTINE"),
        )

        actions = []

        for operation in manifest.get("operations", []):
            source = operation.get("source")
            target = operation.get("target")

            if not source or not os.path.exists(source):
                actions.append({
                    "source": source,
                    "action": "SKIPPED",
                    "reason": "SOURCE_NOT_FOUND",
                })
                continue

            target = target or os.path.join(
                qfolder, os.path.basename(source)
            )

            if os.path.abspath(source) == os.path.abspath(target):
                actions.append({
                    "source": source,
                    "action": "SKIPPED",
                    "reason": "SOURCE_EQUALS_TARGET",
                })
                continue

            if dry_run:
                actions.append({
                    "source": source,
                    "target": target,
                    "action": "WOULD_MOVE",
                })
                continue

            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(source, target)
                actions.append({
                    "source": source,
                    "target": target,
                    "action": "MOVED",
                })
            except OSError as exc:
                actions.append({
                    "source": source,
                    "action": "ERROR",
                    "reason": str(exc),
                })

        result = {
            "dry_run": dry_run,
            "total_operations": len(manifest.get("operations", [])),
            "actions": actions,
            "moved_count": sum(
                1 for a in actions if a.get("action") == "MOVED"
            ),
        }

        if not dry_run and actions:
            log_path = self._write_quarantine_log(actions, qfolder)
            result["log_path"] = log_path

        return result

    def restore_from_quarantine(
        self,
        log_path,
        dry_run=True,
    ):
        """Restore files from quarantine back to their original paths.

        Args:
            log_path: path to quarantine_log.json
            dry_run: if True, only report what would happen

        Returns:
            dict with actions
        """
        if not os.path.exists(log_path):
            return {"error": "LOG_NOT_FOUND", "path": log_path}

        with open(log_path, "r", encoding="utf-8") as f:
            log = json.load(f)

        actions = []

        for entry in log.get("actions", []):
            if entry.get("action") != "MOVED":
                continue

            source = entry.get("target")  # quarantine path
            target = entry.get("source")  # original path

            if not source or not os.path.exists(source):
                actions.append({
                    "source": source,
                    "action": "SKIPPED",
                    "reason": "QUARANTINE_FILE_NOT_FOUND",
                })
                continue

            if dry_run:
                actions.append({
                    "source": source,
                    "target": target,
                    "action": "WOULD_RESTORE",
                })
                continue

            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(source, target)
                actions.append({
                    "source": source,
                    "target": target,
                    "action": "RESTORED",
                })
            except OSError as exc:
                actions.append({
                    "source": source,
                    "action": "ERROR",
                    "reason": str(exc),
                })

        return {
            "dry_run": dry_run,
            "actions": actions,
            "restored_count": sum(
                1 for a in actions if a.get("action") == "RESTORED"
            ),
        }

    def _write_quarantine_log(self, actions, quarantine_folder):
        """Write a quarantine log for later restore."""
        log = {
            "archive_root": os.path.abspath(self.archive_root),
            "quarantine_folder": os.path.abspath(quarantine_folder),
            "actions": actions,
        }

        os.makedirs(quarantine_folder, exist_ok=True)
        path = os.path.join(quarantine_folder, "quarantine_log.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        return os.path.abspath(path)
