import uuid
from datetime import datetime

from app.license.entitlements import EntitlementManager


class BillingService:

    def __init__(self):

        self.entitlements = EntitlementManager()

    def create_checkout(self, plan, email, success_url="", cancel_url=""):

        plan = str(plan or "").upper()
        pricing = self.entitlements.pricing_table()

        if plan not in pricing:
            return {
                "ok": False,
                "reason": "UNKNOWN_PLAN",
                "checkout": None,
            }

        checkout_id = f"chk_{uuid.uuid4().hex[:16]}"

        return {
            "ok": True,
            "reason": "OK",
            "checkout": {
                "id": checkout_id,
                "plan": plan,
                "email": email,
                "monthly_usd": pricing[plan]["monthly_usd"],
                "status": "PENDING_PROVIDER",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "created_at": datetime.utcnow().isoformat(),
                "provider_next": (
                    "Replace this with Stripe/Paddle/iyzico/PayTR checkout URL."
                ),
            },
        }

    def handle_webhook(self, event):

        event_type = event.get("type")
        payload = event.get("payload", {})

        if event_type == "subscription_created":
            return {
                "ok": True,
                "action": "ISSUE_LICENSE",
                "email": payload.get("email"),
                "plan": payload.get("plan"),
            }

        if event_type == "payment_failed":
            return {
                "ok": True,
                "action": "SUSPEND_CLOUD_ENTITLEMENTS",
                "email": payload.get("email"),
            }

        if event_type == "subscription_cancelled":
            return {
                "ok": True,
                "action": "DOWNGRADE_TO_DEMO",
                "email": payload.get("email"),
            }

        return {
            "ok": False,
            "action": "IGNORE",
            "reason": "UNKNOWN_EVENT",
        }
