"""
DJ AI OS — Billing Service (DB + Stripe)

Handles Stripe Checkout sessions, Customer Portal, and webhook processing
with idempotency and audit logging.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.license import signature as sig
from app.license.entitlements import EntitlementManager
from app.server.db.models import License, Subscription, User, WebhookEvent
from app.server.services.stripe_service import stripe_service


class BillingService:
    """DB + Stripe backed billing operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.entitlements = EntitlementManager()

    # ─── Checkout ───

    async def create_checkout(
        self,
        plan: str,
        email: str,
        success_url: str = "",
        cancel_url: str = "",
    ) -> dict:
        """
        Create Stripe Checkout Session for a subscription.

        Returns: {"ok": bool, "checkout": dict|None, "reason": str}
        """
        plan = str(plan or "").upper()
        pricing = self.entitlements.pricing_table()

        if plan not in pricing:
            return {"ok": False, "reason": "UNKNOWN_PLAN", "checkout": None}

        # Find or create user
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            from secrets import token_hex

            user = User(
                id=token_hex(16),
                email=email,
                is_admin=False,
                is_active=True,
            )
            self.session.add(user)
            await self.session.flush()

        # Create Stripe checkout
        checkout = stripe_service.create_checkout_session(
            plan=plan,
            email=email,
            period="monthly",  # default to monthly
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not checkout.get("ok"):
            return {"ok": False, "reason": checkout.get("reason"), "checkout": None}

        return {
            "ok": True,
            "reason": "OK",
            "checkout": {
                "id": checkout["session_id"],
                "plan": plan,
                "email": email,
                "monthly_usd": pricing[plan]["monthly_usd"],
                "status": "PENDING_CHECKOUT",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "stripe_session_id": checkout["session_id"],
                "checkout_url": checkout["url"],
            },
        }

    # ─── Customer Portal ───

    async def get_customer_portal_url(self, stripe_customer_id: str, return_url: str = "") -> dict:
        """Create Stripe Customer Portal session."""
        result = stripe_service.create_portal_session(stripe_customer_id, return_url)
        return result

    # ─── Webhook Handling ───

    async def handle_webhook(
        self,
        raw_body: bytes,
        sig_header: str,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Process Stripe webhook with idempotency.

        Returns: {"ok": bool, "action": str, "details": dict|None, "reason": str}
        """
        # Verify signature
        event, error = stripe_service.construct_webhook_event(raw_body, sig_header)
        if error:
            return {"ok": False, "action": "IGNORE", "reason": error}

        # Idempotency check
        event_id = event.id
        payload_hash = sig.sha256(raw_body.decode("utf-8")) if hasattr(sig, "sha256") else None
        # Simple hash without external deps
        import hashlib

        payload_hash = hashlib.sha256(raw_body).hexdigest()

        existing = await self.session.execute(
            select(WebhookEvent).where(WebhookEvent.id == event_id)
        )
        if existing.scalar_one_or_none():
            # Already processed
            return {"ok": True, "action": "DUPLICATE", "reason": "EVENT_ALREADY_PROCESSED"}

        # Record webhook event
        webhook_record = WebhookEvent(
            id=event_id,
            type=event.type,
            processed=False,
            payload_hash=payload_hash,
        )
        self.session.add(webhook_record)
        await self.session.flush()

        # Dispatch based on event type
        action_result = {"ok": False, "action": "IGNORE", "reason": "UNKNOWN_EVENT"}

        try:
            if event.type == "checkout.session.completed":
                action_result = await self._handle_checkout_completed(event, ip_address)
            elif event.type == "customer.subscription.created":
                action_result = await self._handle_subscription_created(event, ip_address)
            elif event.type == "customer.subscription.updated":
                action_result = await self._handle_subscription_updated(event, ip_address)
            elif event.type == "customer.subscription.deleted":
                action_result = await self._handle_subscription_deleted(event, ip_address)
            elif event.type == "invoice.payment_failed":
                action_result = await self._handle_payment_failed(event, ip_address)
            elif event.type == "invoice.payment_succeeded":
                action_result = await self._handle_payment_succeeded(event, ip_address)
            else:
                action_result = {"ok": True, "action": "IGNORED", "reason": f"UNHANDLED_EVENT: {event.type}"}

            # Mark processed
            webhook_record.processed = True
            await self.session.flush()

        except Exception as exc:
            webhook_record.processed = False
            await self.session.flush()
            action_result = {"ok": False, "action": "ERROR", "reason": f"HANDLER_EXCEPTION: {exc}"}

        # Audit log
        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="webhook.received",
            actor="stripe_webhook",
            target_type="webhook",
            target_id=event_id,
            details={
                "type": event.type,
                "action": action_result.get("action"),
                "ok": action_result.get("ok"),
            },
            ip_address=ip_address,
        )

        return action_result

    # ─── Webhook Handlers ───

    async def _handle_checkout_completed(self, event, ip_address) -> dict:
        """checkout.session.completed → issue license, create subscription record."""
        session_obj = event.data.object  # Stripe Checkout Session
        email = session_obj.get("customer_email") or session_obj.get("customer_details", {}).get("email")
        stripe_customer_id = session_obj.get("customer")
        stripe_subscription_id = session_obj.get("subscription")
        metadata = session_obj.get("metadata", {})
        plan = metadata.get("plan", "PRO").upper()
        period = metadata.get("period", "monthly")

        if not email:
            return {"ok": False, "action": "ISSUE_LICENSE", "reason": "NO_EMAIL_IN_SESSION"}

        # Find or create user
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            from secrets import token_hex

            user = User(id=token_hex(16), email=email, is_admin=False, is_active=True)
            self.session.add(user)
            await self.session.flush()

        # Get subscription details from Stripe
        sub_data = stripe_service.get_subscription(stripe_subscription_id) if stripe_subscription_id else None
        price_id = sub_data.items.data[0].price.id if sub_data and sub_data.items.data else None

        # Create subscription record
        subscription = Subscription(
            id=secrets.token_hex(16),
            user_id=user.id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=price_id,
            plan=plan,
            status="active",
            current_period_start=datetime.fromtimestamp(sub_data.current_period_start, tz=timezone.utc)
            if sub_data and sub_data.current_period_start
            else datetime.now(timezone.utc),
            current_period_end=datetime.fromtimestamp(sub_data.current_period_end, tz=timezone.utc)
            if sub_data and sub_data.current_period_end
            else None,
        )
        self.session.add(subscription)
        await self.session.flush()

        # Issue license
        license_obj = await self._issue_license_for_user(user.id, plan, months=12, actor="stripe_webhook")

        return {
            "ok": True,
            "action": "ISSUE_LICENSE",
            "email": email,
            "plan": plan,
            "license_id": license_obj["id"] if license_obj else None,
        }

    async def _handle_subscription_created(self, event, ip_address) -> dict:
        sub_obj = event.data.object
        return {"ok": True, "action": "SUBSCRIPTION_CREATED", "subscription_id": sub_obj.id}

    async def _handle_subscription_updated(self, event, ip_address) -> dict:
        """Update local subscription + reissue license if plan changed."""
        sub_obj = event.data.object
        stripe_sub_id = sub_obj.id

        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        local_sub = result.scalar_one_or_none()

        if not local_sub:
            return {"ok": True, "action": "SUBSCRIPTION_UPDATED", "note": "LOCAL_SUB_NOT_FOUND"}

        # Update status
        local_sub.status = sub_obj.status
        local_sub.current_period_start = (
            datetime.fromtimestamp(sub_obj.current_period_start, tz=timezone.utc)
            if sub_obj.current_period_start
            else None
        )
        local_sub.current_period_end = (
            datetime.fromtimestamp(sub_obj.current_period_end, tz=timezone.utc)
            if sub_obj.current_period_end
            else None
        )
        local_sub.cancel_at = (
            datetime.fromtimestamp(sub_obj.cancel_at, tz=timezone.utc) if sub_obj.cancel_at else None
        )
        local_sub.updated_at = datetime.now(timezone.utc)

        # If plan changed (price_id changed), reissue license
        new_price_id = sub_obj.items.data[0].price.id if sub_obj.items.data else None
        if new_price_id and new_price_id != local_sub.stripe_price_id:
            local_sub.stripe_price_id = new_price_id
            # Map price_id to plan
            plan = self._plan_from_price_id(new_price_id)
            if plan:
                local_sub.plan = plan
                # Reissue license for new plan
                await self._issue_license_for_user(local_sub.user_id, plan, months=12, actor="stripe_webhook")

        await self.session.flush()
        return {"ok": True, "action": "SUBSCRIPTION_UPDATED", "subscription_id": stripe_sub_id}

    async def _handle_subscription_deleted(self, event, ip_address) -> dict:
        """Downgrade to DEMO, revoke license."""
        sub_obj = event.data.object
        stripe_sub_id = sub_obj.id

        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        local_sub = result.scalar_one_or_none()

        if not local_sub:
            return {"ok": True, "action": "SUBSCRIPTION_DELETED", "note": "LOCAL_SUB_NOT_FOUND"}

        local_sub.status = "cancelled"
        local_sub.cancel_at = datetime.now(timezone.utc)

        # Find and revoke active license for this user
        from app.server.db.models import License

        lic_result = await self.session.execute(
            select(License).where(License.user_id == local_sub.user_id).where(License.is_active == True)
        )
        license_obj = lic_result.scalar_one_or_none()
        if license_obj:
            license_obj.is_active = False
            # Also deactivate machine activations
            from app.server.db.models import MachineActivation

            await self.session.execute(
                MachineActivation.__table__.update()
                .where(MachineActivation.license_id == license_obj.id)
                .values(is_active=False)
            )

        await self.session.flush()
        return {"ok": True, "action": "DOWNGRADE_TO_DEMO", "user_id": local_sub.user_id}

    async def _handle_payment_failed(self, event, ip_address) -> dict:
        """Suspend license + machine activations on payment failure."""
        inv_obj = event.data.object
        stripe_customer_id = inv_obj.get("customer")

        if not stripe_customer_id:
            return {"ok": True, "action": "SUSPEND_CLOUD_ENTITLEMENTS", "invoice_id": inv_obj.id, "note": "NO_CUSTOMER_ON_INVOICE"}

        # Find local subscription by stripe_customer_id
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        local_sub = result.scalar_one_or_none()

        if not local_sub:
            return {"ok": True, "action": "SUSPEND_CLOUD_ENTITLEMENTS", "invoice_id": inv_obj.id, "note": "LOCAL_SUB_NOT_FOUND"}

        # Deactivate license + machine activations (same as subscription_deleted)
        from app.server.db.models import License, MachineActivation

        lic_result = await self.session.execute(
            select(License).where(License.user_id == local_sub.user_id).where(License.is_active == True)
        )
        license_obj = lic_result.scalar_one_or_none()
        if license_obj:
            license_obj.is_active = False
            await self.session.execute(
                MachineActivation.__table__.update()
                .where(MachineActivation.license_id == license_obj.id)
                .values(is_active=False)
            )

        await self.session.flush()
        return {"ok": True, "action": "LICENSE_SUSPENDED_PAYMENT_FAILED", "user_id": local_sub.user_id, "invoice_id": inv_obj.id}

    async def _handle_payment_succeeded(self, event, ip_address) -> dict:
        """Reactivate license on payment recovery."""
        inv_obj = event.data.object
        stripe_customer_id = inv_obj.get("customer")

        if not stripe_customer_id:
            return {"ok": True, "action": "PAYMENT_SUCCEEDED", "invoice_id": inv_obj.id, "note": "NO_CUSTOMER_ON_INVOICE"}

        # Find local subscription by stripe_customer_id
        result = await self.session.execute(
            select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
        )
        local_sub = result.scalar_one_or_none()

        if not local_sub:
            return {"ok": True, "action": "PAYMENT_SUCCEEDED", "invoice_id": inv_obj.id, "note": "LOCAL_SUB_NOT_FOUND"}

        # Reactivate license if it was suspended due to payment failure
        from app.server.db.models import License, MachineActivation

        lic_result = await self.session.execute(
            select(License).where(License.user_id == local_sub.user_id).where(License.is_active == False)
        )
        license_obj = lic_result.scalar_one_or_none()
        if license_obj:
            license_obj.is_active = True
            # Reactivate machine activations for this license
            await self.session.execute(
                MachineActivation.__table__.update()
                .where(MachineActivation.license_id == license_obj.id)
                .values(is_active=True)
            )

        await self.session.flush()
        return {"ok": True, "action": "LICENSE_REACTIVATED_PAYMENT_SUCCEEDED", "user_id": local_sub.user_id, "invoice_id": inv_obj.id}

    # ─── Helpers ───

    def _plan_from_price_id(self, price_id: str) -> Optional[str]:
        """Map Stripe price_id back to plan name."""
        for (plan, period), pid in STRIPE_PRICES.items():
            if pid == price_id:
                return plan
        return None

    async def _issue_license_for_user(
        self, user_id: str, plan: str, months: int = 12, actor: str = "system"
    ) -> Optional[dict]:
        """Issue or re-issue a license for a user."""
        from secrets import token_hex
        from datetime import timedelta

        # Find existing active license for this user/plan
        result = await self.session.execute(
            select(License)
            .where(License.user_id == user_id)
            .where(License.plan == plan)
            .where(License.is_active == True)
        )
        existing = result.scalar_one_or_none()

        max_tracks = self.entitlements.PLAN_FEATURES.get(plan, self.entitlements.PLAN_FEATURES["PRO"])[
            "max_tracks"
        ]
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30 * months)
        updates_until = now + timedelta(days=90)

        if existing:
            # Update existing
            existing.expires_at = expires
            existing.updates_until = updates_until
            existing.max_tracks = max_tracks
            existing.signature_nonce = token_hex(32)
            license_obj = existing
        else:
            license_obj = License(
                id=token_hex(16),
                user_id=user_id,
                key=f"{plan}-{token_hex(20).upper()}",
                plan=plan,
                issued_at=now,
                expires_at=expires,
                max_tracks=max_tracks,
                updates_until=updates_until,
                is_active=True,
                signature_nonce=token_hex(32),
            )
            self.session.add(license_obj)

        await self.session.flush()

        from app.server.services.audit_service import log_audit

        await log_audit(
            self.session,
            action="license.issued" if not existing else "license.reissued",
            actor=actor,
            target_type="license",
            target_id=license_obj.id,
            details={"key": license_obj.key, "plan": plan},
        )

        return {
            "id": license_obj.id,
            "key": license_obj.key,
            "plan": license_obj.plan,
            "issued_at": license_obj.issued_at.isoformat(),
            "expires_at": license_obj.expires_at.isoformat(),
        }


# Import for local use in this module
import secrets
import hashlib

from app.server.services.stripe_service import STRIPE_PRICES