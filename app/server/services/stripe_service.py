"""
DJ AI OS — Stripe Service Wrapper

Wraps Stripe API for checkout sessions, customer portal, webhook verification,
and subscription management.

Real API keys via env:
  STRIPE_SECRET_KEY        = sk_test_xxx / sk_live_xxx
  STRIPE_WEBHOOK_SECRET    = whsec_xxx
"""

import os
from typing import Optional

from app.license.entitlements import EntitlementManager


# ─── Price ID Mapping ───
# (plan, period) → Stripe Price ID from dashboard
STRIPE_PRICES = {
    ("PRO", "monthly"): "price_pro_monthly",
    ("PRO", "yearly"): "price_pro_yearly",
    ("DJ_ARCHIVE", "monthly"): "price_archive_monthly",
    ("DJ_ARCHIVE", "yearly"): "price_archive_yearly",
    ("STUDIO", "monthly"): "price_studio_monthly",
    ("STUDIO", "yearly"): "price_studio_yearly",
    ("ENTERPRISE", "monthly"): "price_enterprise_monthly",
    ("ENTERPRISE", "yearly"): "price_enterprise_yearly",
}


class StripeService:
    """Wrapper around Stripe API (fail-safe if stripe lib / keys missing)."""

    def __init__(self):
        self.secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
        self._stripe = None

    @property
    def stripe(self):
        """Lazy-load stripe lib; returns None if unavailable."""
        if self._stripe is None:
            try:
                import stripe

                if self.secret_key:
                    stripe.api_key = self.secret_key
                self._stripe = stripe
            except ImportError:
                self._stripe = False
        return self._stripe or None

    def is_configured(self) -> bool:
        return bool(self.stripe and self.secret_key)

    def create_checkout_session(self, plan, email, period="monthly", success_url="", cancel_url=""):
        """
        Create a Stripe Checkout Session for a subscription.

        Returns: {"ok": bool, "url": str|None, "session_id": str|None, "reason": str}
        """
        stripe = self.stripe
        if not stripe:
            return {"ok": False, "url": None, "session_id": None, "reason": "STRIPE_NOT_CONFIGURED"}

        price_id = STRIPE_PRICES.get((plan, period))
        if not price_id:
            return {"ok": False, "url": None, "session_id": None, "reason": "UNKNOWN_PLAN_PRICE"}

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=email,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url or "https://dj-ai-os.example/success",
                cancel_url=cancel_url or "https://dj-ai-os.example/cancel",
                metadata={"plan": plan, "period": period, "email": email},
                allow_promotion_codes=True,
            )
            return {
                "ok": True,
                "url": session.url,
                "session_id": session.id,
                "reason": "OK",
            }
        except Exception as exc:
            return {"ok": False, "url": None, "session_id": None, "reason": f"STRIPE_ERROR: {exc}"}

    def create_portal_session(self, stripe_customer_id, return_url=""):
        """
        Create a Stripe Customer Portal session (self-serve billing).

        Returns: {"ok": bool, "url": str|None, "reason": str}
        """
        stripe = self.stripe
        if not stripe:
            return {"ok": False, "url": None, "reason": "STRIPE_NOT_CONFIGURED"}

        if not stripe_customer_id:
            return {"ok": False, "url": None, "reason": "MISSING_CUSTOMER_ID"}

        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url or "https://dj-ai-os.example/account",
            )
            return {"ok": True, "url": session.url, "reason": "OK"}
        except Exception as exc:
            return {"ok": False, "url": None, "reason": f"STRIPE_ERROR: {exc}"}

    def construct_webhook_event(self, raw_body: bytes, sig_header: str):
        """
        Verify and construct Stripe webhook event.

        Returns: (event | None, error_message | None)
        """
        stripe = self.stripe
        if not stripe:
            return None, "STRIPE_NOT_CONFIGURED"
        if not self.webhook_secret:
            return None, "WEBHOOK_SECRET_MISSING"

        try:
            event = stripe.Webhook.construct_event(raw_body, sig_header, self.webhook_secret)
            return event, None
        except ValueError as exc:
            return None, f"INVALID_PAYLOAD: {exc}"
        except stripe.error.SignatureVerificationError as exc:
            return None, f"INVALID_SIGNATURE: {exc}"

    def cancel_subscription(self, stripe_subscription_id):
        """Cancel a Stripe subscription immediately or at period end."""
        stripe = self.stripe
        if not stripe:
            return {"ok": False, "reason": "STRIPE_NOT_CONFIGURED"}
        try:
            sub = stripe.Subscription.delete(stripe_subscription_id)
            return {"ok": True, "status": sub.status}
        except Exception as exc:
            return {"ok": False, "reason": f"STRIPE_ERROR: {exc}"}

    def get_subscription(self, stripe_subscription_id):
        """Retrieve a Stripe subscription."""
        stripe = self.stripe
        if not stripe:
            return None
        try:
            return stripe.Subscription.retrieve(stripe_subscription_id)
        except Exception:
            return None

    def get_customer_portal_url(self, stripe_customer_id, return_url=""):
        """Alias for create_portal_session."""
        return self.create_portal_session(stripe_customer_id, return_url)


# Singleton
stripe_service = StripeService()
