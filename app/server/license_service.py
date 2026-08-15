"""
DJ AI OS — License Service (DB-backed)

Handles license activation, entitlements computation, and revocation using
PostgreSQL/SQLite persistence + Ed25519 signing.

NOTE: Ed25519 signing uses app.license.signature.sign() which requires the
vendor private key (env DJ_AI_OS_LICENSE_PRIVATE_KEY or vendor_private_key.pem).
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.license import signature as sig
from app.license.entitlements import EntitlementManager
from app.server.db.models import License, MachineActivation, User, WebhookEvent


class LicenseService:
    """DB-backed license operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.entitlements = EntitlementManager()

    # ─── Plan resolution ───

    def plan_from_key(self, license_key: str) -> str:
        """
        Server-side: parse plan prefix. Client does NOT trust this; client
        verifies the signature instead. Used for DB lookup.
        """
        key = str(license_key or "").strip().upper()
        prefixes = {
            "PRO-": "PRO",
            "ARCHIVE-": "DJ_ARCHIVE",
            "STUDIO-": "STUDIO",
            "ENT-": "ENTERPRISE",
        }
        for prefix, plan in prefixes.items():
            if key.startswith(prefix) and len(key) >= len(prefix) + 8:
                return plan
        return "INVALID"

    # ─── Activation ───

    async def activate(
        self,
        email: str,
        license_key: str,
        machine_id: str,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Activate a license on a machine.

        Flow:
        1. Lookup license by key (DB)
        2. Find/create user by email
        3. Check machine activation count vs plan limit
        4. Sign license data (Ed25519)
        5. Persist machine activation
        6. Audit log
        """
        plan = self.plan_from_key(license_key)

        if plan == "INVALID":
            return {"ok": False, "reason": "INVALID_LICENSE_KEY", "license": None}

        # Lookup license in DB
        result = await self.session.execute(select(License).where(License.key == license_key))
        license_obj = result.scalar_one_or_none()

        if not license_obj:
            return {"ok": False, "reason": "LICENSE_NOT_FOUND", "license": None}

        if not license_obj.is_active:
            return {"ok": False, "reason": "LICENSE_REVOKED", "license": None}

        # Find or create user
        user_result = await self.session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                id=secrets.token_hex(16),
                email=email,
                is_admin=False,
                is_active=True,
            )
            self.session.add(user)
            await self.session.flush()

        # Check machine activation limit
        max_machines = self.entitlements.MAX_MACHINES.get(plan, 3)
        active_machines = await self.session.execute(
            select(MachineActivation)
            .where(MachineActivation.license_id == license_obj.id)
            .where(MachineActivation.is_active == True)
        )
        existing = active_machines.scalars().all()

        # Reuse existing activation if same machine
        existing_machine = next((m for m in existing if m.machine_id == machine_id), None)
        if existing_machine:
            existing_machine.activated_at = datetime.now(timezone.utc)
            machine_activation = existing_machine
        else:
            if len(existing) >= max_machines:
                return {
                    "ok": False,
                    "reason": "MAX_MACHINES_EXCEEDED",
                    "license": None,
                    "max_machines": max_machines,
                }

            machine_activation = MachineActivation(
                id=secrets.token_hex(16),
                license_id=license_obj.id,
                machine_id=machine_id,
                is_active=True,
                max_machines=max_machines,
            )
            self.session.add(machine_activation)
            await self.session.flush()

        # Build signed license data
        now = datetime.now(timezone.utc)
        license_data = {
            "email": email,
            "machine_id": machine_id,
            "plan": plan,
            "expiry": license_obj.expires_at.strftime("%Y-%m-%d"),
            "max_tracks": license_obj.max_tracks,
            "updates_until": (
                license_obj.updates_until.strftime("%Y-%m-%d")
                if license_obj.updates_until
                else None
            ),
            "issued_at": now.isoformat(),
            "nonce": license_obj.signature_nonce,
        }

        # Sign (fail if no private key)
        if not sig.has_signing_key():
            return {
                "ok": False,
                "reason": "NO_SIGNING_KEY",
                "license": None,
            }

        license_data["signature"] = sig.sign(license_data)

        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.activated",
            actor=email,
            target_type="license",
            target_id=license_obj.id,
            details={"machine_id": machine_id, "plan": plan},
            ip_address=ip_address,
        )

        return {
            "ok": True,
            "reason": "OK",
            "license": license_data,
            "entitlements": self.entitlements.entitlements_for({
                "licensed": True,
                "plan": plan,
                "max_tracks": license_obj.max_tracks,
                "updates_until": license_data["updates_until"],
            }),
            "max_machines": max_machines,
            "active_machines": len(existing) + (0 if existing_machine else 1),
        }

    # ─── Entitlements ───

    async def entitlements_for_license_data(self, license_data: dict) -> dict:
        """
        Verify signature and compute entitlements for client-sent license.
        """
        if not self.verify(license_data):
            return {
                "ok": False,
                "reason": "INVALID_SIGNATURE",
                "entitlements": self.entitlements.entitlements_for({
                    "licensed": False,
                    "plan": "DEMO",
                }),
            }

        # Check DB for revocation
        result = await self.session.execute(
            select(License).where(License.signature_nonce == license_data.get("nonce"))
        )
        license_obj = result.scalar_one_or_none()

        if not license_obj or not license_obj.is_active:
            return {
                "ok": False,
                "reason": "LICENSE_REVOKED",
                "entitlements": self.entitlements.entitlements_for({
                    "licensed": False,
                    "plan": "DEMO",
                }),
            }

        return {
            "ok": True,
            "reason": "OK",
            "entitlements": self.entitlements.entitlements_for({
                "licensed": True,
                "plan": license_data.get("plan", "DEMO"),
                "max_tracks": license_data.get("max_tracks", 1000),
                "updates_until": license_data.get("updates_until"),
            }),
        }

    # ─── Revocation ───

    async def revoke_license(self, license_id: str, actor: str = "admin") -> bool:
        """Revoke a license (deactivate + audit)."""
        result = await self.session.execute(select(License).where(License.id == license_id))
        license_obj = result.scalar_one_or_none()
        if not license_obj:
            return False

        license_obj.is_active = False
        for m in license_obj.machine_activations:
            m.is_active = False
        await self.session.flush()

        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.revoked",
            actor=actor,
            target_type="license",
            target_id=license_id,
            details={"key": license_obj.key, "plan": license_obj.plan},
        )
        return True

    # ─── Sign/Verify ───

    def sign(self, data: dict) -> str:
        return sig.sign(data)

    def verify(self, data: dict) -> bool:
        if not data or "signature" not in data:
            return False
        return sig.verify(data, data.get("signature"))
