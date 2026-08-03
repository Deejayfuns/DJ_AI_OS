import json
import os
from datetime import datetime


class DJArchiveCloud:

    def __init__(self, catalog_path=None, download_folder="DJ_CLOUD_DOWNLOADS"):

        self.catalog_path = catalog_path or os.path.join(
            "app",
            "config",
            "cloud_archive_catalog.json"
        )
        self.download_folder = download_folder

    def has_access(self, plan):

        entitlements = plan.get("entitlements", {})

        if entitlements:
            return bool(entitlements.get("dj_archive_downloads"))

        return bool(plan.get("licensed")) and str(
            plan.get("plan", "")
        ).upper() in {"DJ_ARCHIVE", "STUDIO", "ENTERPRISE"}

    def list_packs(self):

        if os.path.exists(self.catalog_path):
            try:
                with open(self.catalog_path, "r", encoding="utf-8") as handle:
                    return json.load(handle).get("packs", [])
            except Exception:
                return self.default_catalog()

        return self.default_catalog()

    def download_pack(self, pack_id, plan):

        if not self.has_access(plan):
            return {
                "ok": False,
                "reason": "DJ_ARCHIVE_LICENSE_REQUIRED",
                "path": "",
            }

        pack = self.find_pack(pack_id)

        if not pack:
            return {
                "ok": False,
                "reason": "PACK_NOT_FOUND",
                "path": "",
            }

        os.makedirs(self.download_folder, exist_ok=True)

        manifest_path = os.path.abspath(
            os.path.join(
                self.download_folder,
                f"{pack_id}_manifest.json"
            )
        )

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "downloaded_at": datetime.now().isoformat(),
                    "pack": pack,
                    "note": (
                        "Bu manifest demo cloud indirme akisini temsil eder. "
                        "Gercek sistemde lisansli audio paketleri imzali "
                        "URL ile indirilir."
                    )
                },
                handle,
                indent=2
            )

        return {
            "ok": True,
            "reason": "OK",
            "path": manifest_path,
        }

    def find_pack(self, pack_id):

        for pack in self.list_packs():
            if pack.get("id") == pack_id:
                return pack

        return None

    def default_catalog(self):

        return [
            {
                "id": "monthly_tech_house_essentials",
                "name": "Monthly Tech House Essentials",
                "month": datetime.now().strftime("%Y-%m"),
                "genre": "TECH HOUSE",
                "tracks": 25,
                "license_required": "DJ_ARCHIVE",
                "quality": "320kbps / WAV-ready",
                "description": "Peak-time ve groove odakli aylik DJ arşiv paketi.",
            },
            {
                "id": "afro_melodic_warmup_pack",
                "name": "Afro / Melodic Warmup Pack",
                "month": datetime.now().strftime("%Y-%m"),
                "genre": "AFRO HOUSE / MELODIC HOUSE",
                "tracks": 18,
                "license_required": "DJ_ARCHIVE",
                "quality": "320kbps / WAV-ready",
                "description": "Warmup, sunset ve lounge gecisleri icin secili paket.",
            },
            {
                "id": "wedding_event_floorfillers_tr",
                "name": "Wedding & Event Floorfillers TR",
                "month": datetime.now().strftime("%Y-%m"),
                "genre": "WEDDING & EVENT",
                "tracks": 30,
                "license_required": "DJ_ARCHIVE",
                "quality": "320kbps",
                "description": "Kina, dugun ve event akislarina uygun pratik paket.",
            },
        ]
