"""
DJ AI OS — Admin Service

Admin CRUD operations for users, licenses, subscriptions, and statistics.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.server.db.models import AuditLog, License, MachineActivation, Subscription, User
from app.license import signature as sig
from app.license.entitlements import EntitlementManager


class AdminService:
    """Admin operations on DB."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Stats ───

    async def get_stats(self) -> dict:
        """Dashboard statistics."""
        total_users = await self.session.scalar(select(func.count(User.id)))
        active_users = await self.session.scalar(
            select(func.count(User.id)).where(User.is_active == True)
        )
        total_licenses = await self.session.scalar(select(func.count(License.id)))
        active_licenses = await self.session.scalar(
            select(func.count(License.id)).where(License.is_active == True)
        )
        total_subscriptions = await self.session.scalar(select(func.count(Subscription.id)))
        active_subs = await self.session.scalar(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )

        # Plan distribution
        plan_dist = await self.session.execute(
            select(License.plan, func.count(License.id))
            .where(License.is_active == True)
            .group_by(License.plan)
        )
        plan_distribution = {plan: count for plan, count in plan_dist.all()}

        # MRR estimate (simplified: monthly price * active subs)
        pricing = EntitlementManager.PRICING
        mrr = 0
        for plan, count in plan_distribution.items():
            if plan in pricing and pricing[plan]["monthly_usd"]:
                mrr += pricing[plan]["monthly_usd"] * count

        # Recent audit logs (last 10)
        recent_audit = await self.session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(10)
        )
        recent_audit_logs = [
            {
                "id": a.id,
                "action": a.action,
                "actor": a.actor,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "details": a.details,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_audit.scalars().all()
        ]

        return {
            "total_users": total_users or 0,
            "active_users": active_users or 0,
            "total_licenses": total_licenses or 0,
            "active_licenses": active_licenses or 0,
            "total_subscriptions": total_subscriptions or 0,
            "active_subscriptions": active_subs or 0,
            "plan_distribution": plan_distribution,
            "mrr_usd": round(mrr, 2),
            "recent_audit": recent_audit_logs,
        }

    # ─── Users ───

    async def list_users(
        self, limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> list[dict]:
        stmt = select(User).order_by(User.created_at.desc())
        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "is_admin": u.is_admin,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
                "license_count": len(u.licenses),
            }
            for u in users
        ]

    # ─── Customers (User CRUD for admin) ───

    async def create_customer(self, email: str, name: str, company_name: Optional[str] = None) -> dict:
        """Create a new customer (User)."""
        from app.server.db.models import User
        from secrets import token_hex

        # Check email uniqueness
        existing = await self.session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("EMAIL_ALREADY_EXISTS")

        user = User(
            id=token_hex(16),
            email=email,
            name=name,
            company_name=company_name,
            is_admin=False,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()

        # Audit
        from app.server.services.audit_service import log_audit
        await log_audit(
            self.session,
            action="customer.created",
            actor="admin",
            target_type="user",
            target_id=user.id,
            details={"email": email, "name": name, "company_name": company_name},
        )

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company_name": user.company_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }

    async def list_customers(
        self, limit: int = 50, offset: int = 0, search: Optional[str] = None
    ) -> list[dict]:
        """List customers (Users)."""
        from app.server.db.models import User

        stmt = select(User).order_by(User.created_at.desc())
        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "company_name": u.company_name,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]

    async def get_customer_detail(self, customer_id: str) -> Optional[dict]:
        """Get customer detail."""
        from app.server.db.models import User

        result = await self.session.execute(select(User).where(User.id == customer_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "company_name": user.company_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }

    async def generate_download_payload(self, license_id: str, machine_id: Optional[str] = None) -> dict:
        """Generate signed license payload for download (used by download endpoint)."""
        from datetime import datetime, timezone
        from app.license import signature as sig
        from app.server.db.models import License

        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            raise ValueError("LICENSE_NOT_FOUND")

        # Determine machine_id
        if machine_id is None:
            # Use first active machine activation
            for m in lic.machine_activations:
                if m.is_active:
                    machine_id = m.machine_id
                    break

        if not machine_id:
            # No active machine - use placeholder (will fail machine check on client)
            machine_id = "0" * 64

        # Build license payload for signing
        payload = {
            "email": lic.user.email if lic.user else "",
            "machine_id": machine_id,
            "plan": lic.plan,
            "expiry": lic.expires_at.strftime("%Y-%m-%d") if lic.expires_at else "2099-12-31",
            "max_tracks": lic.max_tracks,
            "updates_until": lic.updates_until.strftime("%Y-%m-%d") if lic.updates_until else "2099-12-31",
            "issued_at": lic.issued_at.isoformat().replace("+00:00", "Z") if lic.issued_at else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "nonce": lic.signature_nonce,
        }

        # Sign with vendor private key
        signature_hex = sig.sign(payload)
        payload["signature"] = signature_hex

        return payload

    async def get_user_detail(self, user_id: str) -> Optional[dict]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        # Get licenses
        licenses = [
            {
                "id": l.id,
                "key": l.key,
                "plan": l.plan,
                "issued_at": l.issued_at.isoformat(),
                "expires_at": l.expires_at.isoformat(),
                "is_active": l.is_active,
                "max_tracks": l.max_tracks,
            }
            for l in user.licenses
        ]

        # Get subscriptions
        subs = [
            {
                "id": s.id,
                "plan": s.plan,
                "status": s.status,
                "stripe_customer_id": s.stripe_customer_id,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            }
            for s in user.subscriptions
        ]

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "licenses": licenses,
            "subscriptions": subs,
        }

    async def set_user_active(self, user_id: str, is_active: bool) -> bool:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.is_active = is_active
        await self.session.flush()
        return True

    async def get_user_licenses(self, user_id: str) -> list[dict]:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return []
        return [
            {
                "id": l.id,
                "key": l.key,
                "plan": l.plan,
                "issued_at": l.issued_at.isoformat(),
                "expires_at": l.expires_at.isoformat(),
                "is_active": l.is_active,
                "max_tracks": l.max_tracks,
            }
            for l in user.licenses
        ]

    async def get_user_subscription(self, user_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.created_at.desc())
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
        return {
            "id": sub.id,
            "plan": sub.plan,
            "status": sub.status,
            "stripe_customer_id": sub.stripe_customer_id,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at": sub.cancel_at.isoformat() if sub.cancel_at else None,
        }

    async def get_user_machines(self, user_id: str) -> list[dict]:
        # Machines are tied to licenses; gather all machine activations for user's licenses
        result = await self.session.execute(select(License).where(License.user_id == user_id))
        licenses = result.scalars().all()
        machines = []
        for lic in licenses:
            for m in lic.machine_activations:
                machines.append({
                    "id": m.id,
                    "machine_id": m.machine_id,
                    "license_key": lic.key,
                    "activated_at": m.activated_at.isoformat(),
                    "is_active": m.is_active,
                })
        return machines

    # ─── Licenses ───

    async def list_licenses(
        self, limit: int = 50, offset: int = 0, plan: Optional[str] = None, user_email: Optional[str] = None
    ) -> list[dict]:
        stmt = select(License).order_by(License.issued_at.desc())
        if plan:
            stmt = stmt.where(License.plan == plan)
        if user_email:
            stmt = stmt.join(User).where(User.email == user_email)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        licenses = result.scalars().all()

        return [
            {
                "id": l.id,
                "key": l.key,
                "plan": l.plan,
                "user_email": l.user.email if l.user else None,
                "issued_at": l.issued_at.isoformat(),
                "expires_at": l.expires_at.isoformat(),
                "max_tracks": l.max_tracks,
                "is_active": l.is_active,
            }
            for l in licenses
        ]

    async def get_license_detail(self, license_id: str) -> Optional[dict]:
        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            return None

        machines = [
            {
                "id": m.id,
                "machine_id": m.machine_id,
                "activated_at": m.activated_at.isoformat(),
                "is_active": m.is_active,
                "deactivated_at": m.deactivated_at.isoformat() if m.deactivated_at else None,
            }
            for m in lic.machine_activations
        ]

        return {
            "id": lic.id,
            "key": lic.key,
            "plan": lic.plan,
            "user_id": lic.user_id,
            "user_email": lic.user.email if lic.user else None,
            "issued_at": lic.issued_at.isoformat(),
            "expires_at": lic.expires_at.isoformat(),
            "max_tracks": lic.max_tracks,
            "updates_until": lic.updates_until.isoformat() if lic.updates_until else None,
            "is_active": lic.is_active,
            "revoked_at": lic.revoked_at.isoformat() if lic.revoked_at else None,
            "signature_nonce": lic.signature_nonce,
            "machine_activations": machines,
        }

    async def revoke_license(self, license_id: str, actor: str) -> bool:
        """Deactivate a license."""
        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            return False
        lic.is_active = False
        lic.revoked_at = datetime.now(timezone.utc)
        # Also deactivate all machine activations
        for m in lic.machine_activations:
            m.is_active = False
            m.deactivated_at = datetime.now(timezone.utc)
        await self.session.flush()
        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.revoked",
            actor=actor,
            target_type="license",
            target_id=license_id,
            details={"key": lic.key, "plan": lic.plan},
        )
        return True

    async def issue_license(
        self,
        user_id: str,
        plan: str,
        months: int = 12,
        actor: str = "admin",
        machine_id: Optional[str] = None,
        expiry: Optional[str] = None,
        updates_until: Optional[str] = None,
        max_tracks: Optional[int] = None,
    ) -> Optional[dict]:
        """Create a new license for a user."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None

        entitlements = EntitlementManager.PLAN_FEATURES.get(plan, EntitlementManager.PLAN_FEATURES["PRO"])
        default_max_tracks = entitlements["max_tracks"]

        # Use provided max_tracks or plan default
        if max_tracks is None:
            max_tracks = default_max_tracks

        # Map plan to license key prefix (must match LicenseService.plan_from_key)
        plan_prefix = {
            "PRO": "PRO",
            "DJ_ARCHIVE": "ARCHIVE",
            "STUDIO": "STUDIO",
            "ENTERPRISE": "ENT",
        }.get(plan, "PRO")
        license_key = f"{plan_prefix}-{secrets.token_hex(20).upper()}"
        now = datetime.now(timezone.utc)

        # Parse custom expiry or use default
        if expiry:
            try:
                expires = datetime.strptime(expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                expires = now + timedelta(days=30 * months)
        else:
            expires = now + timedelta(days=30 * months)

        # Parse custom updates_until or use default
        if updates_until:
            try:
                updates_until_dt = datetime.strptime(updates_until, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                updates_until_dt = now + timedelta(days=90)
        else:
            updates_until_dt = now + timedelta(days=90)

        license_obj = License(
            id=secrets.token_hex(16),
            user_id=user_id,
            key=license_key,
            plan=plan,
            issued_at=now,
            expires_at=expires,
            max_tracks=max_tracks,
            updates_until=updates_until_dt,
            is_active=True,
            signature_nonce=secrets.token_hex(32),
        )
        self.session.add(license_obj)

        # If machine_id provided, create machine activation
        if machine_id:
            from app.server.db.models import MachineActivation
            machine_activation = MachineActivation(
                id=secrets.token_hex(16),
                license_id=license_obj.id,
                machine_id=machine_id,
                activated_at=now,
                is_active=True,
                max_machines=EntitlementManager.MAX_MACHINES.get(plan, 3),
            )
            self.session.add(machine_activation)

        await self.session.flush()

        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.issued",
            actor=actor,
            target_type="license",
            target_id=license_obj.id,
            details={"key": license_key, "plan": plan, "user_email": user.email},
        )

        return {
            "id": license_obj.id,
            "key": license_key,
            "plan": plan,
            "issued_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }

    # ─── Subscriptions ───

    async def list_subscriptions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None
    ) -> list[dict]:
        stmt = select(Subscription).order_by(Subscription.created_at.desc())
        if status:
            stmt = stmt.where(Subscription.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        subs = result.scalars().all()

        return [
            {
                "id": s.id,
                "plan": s.plan,
                "status": s.status,
                "user_email": s.user.email if s.user else None,
                "stripe_customer_id": s.stripe_customer_id,
                "stripe_subscription_id": s.stripe_subscription_id,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            }
            for s in subs
        ]

    async def get_subscription_detail(self, sub_id: str) -> Optional[dict]:
        result = await self.session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            return None

        return {
            "id": sub.id,
            "plan": sub.plan,
            "status": sub.status,
            "user_email": sub.user.email if sub.user else None,
            "stripe_customer_id": sub.stripe_customer_id,
            "stripe_subscription_id": sub.stripe_subscription_id,
            "stripe_price_id": sub.stripe_price_id,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at": sub.cancel_at.isoformat() if sub.cancel_at else None,
            "created_at": sub.created_at.isoformat(),
        }

    async def deactivate_machine(self, license_id: str, machine_id: str, actor: str = "admin") -> bool:
        """Deactivate a specific machine activation for a license."""
        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            return False

        # Find the machine activation
        machine = None
        for m in lic.machine_activations:
            if m.machine_id == machine_id:
                machine = m
                break

        if not machine:
            return False

        machine.is_active = False
        machine.deactivated_at = datetime.now(timezone.utc)
        await self.session.flush()

        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="machine.deactivated",
            actor=actor,
            target_type="machine",
            target_id=machine.id,
            details={"license_id": license_id, "machine_id": machine_id, "license_key": lic.key},
        )
        return True

    async def renew_license(self, license_id: str, months: int = 12, actor: str = "admin") -> Optional[dict]:
        """Extend license expiry and updates_until by N months, re-sign with new nonce."""
        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            return None

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30 * months)
        updates_until = now + timedelta(days=90)

        old_expires = lic.expires_at
        old_updates = lic.updates_until
        old_nonce = lic.signature_nonce

        lic.expires_at = expires
        lic.updates_until = updates_until
        lic.signature_nonce = secrets.token_hex(32)

        await self.session.flush()

        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.renewed",
            actor=actor,
            target_type="license",
            target_id=license_id,
            details={
                "key": lic.key,
                "plan": lic.plan,
                "old_expires_at": old_expires.isoformat() if old_expires else None,
                "new_expires_at": expires.isoformat(),
                "old_updates_until": old_updates.isoformat() if old_updates else None,
                "new_updates_until": updates_until.isoformat(),
                "old_nonce": old_nonce,
                "new_nonce": lic.signature_nonce,
            },
        )

        return {
            "id": lic.id,
            "key": lic.key,
            "plan": lic.plan,
            "expires_at": expires.isoformat(),
            "updates_until": updates_until.isoformat(),
            "signature_nonce": lic.signature_nonce,
        }

    async def change_license_plan(self, license_id: str, new_plan: str, actor: str = "admin") -> Optional[dict]:
        """Change license plan, update max_tracks, updates_until, re-sign with new nonce."""
        result = await self.session.execute(select(License).where(License.id == license_id))
        lic = result.scalar_one_or_none()
        if not lic:
            return None

        valid_plans = ["PRO", "DJ_ARCHIVE", "STUDIO", "ENTERPRISE"]
        if new_plan not in valid_plans:
            raise ValueError(f"INVALID_PLAN: {new_plan}")

        entitlements = EntitlementManager.PLAN_FEATURES.get(new_plan, EntitlementManager.PLAN_FEATURES["PRO"])
        max_tracks = entitlements["max_tracks"]

        old_plan = lic.plan
        old_max_tracks = lic.max_tracks
        old_nonce = lic.signature_nonce

        lic.plan = new_plan
        lic.max_tracks = max_tracks
        lic.updates_until = datetime.now(timezone.utc) + timedelta(days=90)
        lic.signature_nonce = secrets.token_hex(32)

        await self.session.flush()

        # Audit
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.plan_changed",
            actor=actor,
            target_type="license",
            target_id=license_id,
            details={
                "key": lic.key,
                "old_plan": old_plan,
                "new_plan": new_plan,
                "old_max_tracks": old_max_tracks,
                "new_max_tracks": max_tracks,
                "old_nonce": old_nonce,
                "new_nonce": lic.signature_nonce,
            },
        )

        return {
            "id": lic.id,
            "key": lic.key,
            "plan": new_plan,
            "max_tracks": max_tracks,
            "updates_until": lic.updates_until.isoformat() if lic.updates_until else None,
            "signature_nonce": lic.signature_nonce,
        }

    # ─── Audit ───

    async def list_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        target_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[dict]:
        from app.server.services.audit_service import get_audit_logs

        logs = await get_audit_logs(self.session, limit, offset, action, actor, target_type)
        return [
            {
                "id": a.id,
                "action": a.action,
                "actor": a.actor,
                "target_type": a.target_type,
                "target_id": a.target_id,
                "details": a.details,
                "ip_address": a.ip_address,
                "created_at": a.created_at.isoformat(),
            }
            for a in logs
        ]