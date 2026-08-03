from datetime import datetime, timedelta

from app.cloud.dj_archive_cloud import DJArchiveCloud


class CloudService:

    def __init__(self, archive=None):

        self.archive = archive or DJArchiveCloud()

    def list_packs(self, plan):

        return {
            "ok": True,
            "access": self.archive.has_access(plan),
            "packs": self.archive.list_packs(),
        }

    def download_pack(self, pack_id, plan):

        if not self.archive.has_access(plan):
            return {
                "ok": False,
                "reason": "DJ_ARCHIVE_LICENSE_REQUIRED",
                "download": None,
            }

        pack = self.archive.find_pack(pack_id)

        if not pack:
            return {
                "ok": False,
                "reason": "PACK_NOT_FOUND",
                "download": None,
            }

        expires = datetime.utcnow() + timedelta(minutes=15)

        return {
            "ok": True,
            "reason": "OK",
            "download": {
                "pack_id": pack_id,
                "pack_name": pack.get("name"),
                "signed_url": (
                    f"https://cdn.dj-ai-os.example/packs/{pack_id}"
                    "?signature=dev-signed-url"
                ),
                "checksum": f"sha256:{pack_id}",
                "expires_at": expires.isoformat(),
            },
        }
