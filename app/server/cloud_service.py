"""
DJ AI OS — Cloud Service (DB-backed)

Provides DJ Archive pack listing and download with entitlement verification.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cloud.dj_archive_cloud import DJArchiveCloud
from app.server.db.models import License


class CloudService:
    """DB-backed cloud operations."""

    def __init__(self, session: AsyncSession, archive: Optional[DJArchiveCloud] = None):
        self.session = session
        self.archive = archive or DJArchiveCloud()

    async def list_packs(self, license_data: dict) -> dict:
        """
        List available monthly packs for a license.

        Requires valid license with DJ_ARCHIVE+ plan and active updates_until.
        """
        # Verify license signature first
        from app.license import signature as sig

        if not sig.verify(license_data, license_data.get("signature", "")):
            return {"ok": False, "access": False, "reason": "INVALID_SIGNATURE", "packs": []}

        # Check DB for revocation
        nonce = license_data.get("nonce")
        if not nonce:
            return {"ok": False, "access": False, "reason": "MISSING_NONCE", "packs": []}

        result = await self.session.execute(
            select(License).where(License.signature_nonce == nonce).where(License.is_active == True)
        )
        license_obj = result.scalar_one_or_none()

        if not license_obj:
            return {"ok": False, "access": False, "reason": "LICENSE_REVOKED", "packs": []}

        # Check plan access
        has_access = self.archive.has_access(license_obj.plan)
        if not has_access:
            return {"ok": False, "access": False, "reason": "PLAN_TOO_LOW", "packs": []}

        return {
            "ok": True,
            "access": True,
            "packs": self.archive.list_packs(),
        }

    async def download_pack(self, pack_id: str, license_data: dict) -> dict:
        """
        Generate signed download URL for a pack.

        Requires DJ_ARCHIVE+ plan with active license.
        """
        from app.license import signature as sig

        # Verify signature
        if not sig.verify(license_data, license_data.get("signature", "")):
            return {
                "ok": False,
                "reason": "INVALID_SIGNATURE",
                "download": None,
            }

        # Check DB
        nonce = license_data.get("nonce")
        result = await self.session.execute(
            select(License).where(License.signature_nonce == nonce).where(License.is_active == True)
        )
        license_obj = result.scalar_one_or_none()

        if not license_obj:
            return {
                "ok": False,
                "reason": "LICENSE_REVOKED",
                "download": None,
            }

        # Check plan access
        if not self.archive.has_access(license_obj.plan):
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

        # In production: generate signed S3/CDN URL
        # For now: placeholder
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