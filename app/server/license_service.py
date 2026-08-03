import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta

from app.license.entitlements import EntitlementManager


class LicenseService:

    def __init__(self, secret=None):

        self.secret = (
            secret
            or os.environ.get("DJ_AI_OS_LICENSE_SECRET")
            or "dev-secret-change-before-production"
        )
        self.entitlements = EntitlementManager()

    def activate(self, email, license_key, machine_id):

        plan = self.plan_from_key(license_key)

        if plan == "INVALID":
            return {
                "ok": False,
                "reason": "INVALID_LICENSE_KEY",
                "license": None,
            }

        now = datetime.utcnow()
        expiry = now + timedelta(days=365)
        updates_until = now + timedelta(days=90)
        max_tracks = self.entitlements.PLAN_FEATURES[plan]["max_tracks"]

        license_data = {
            "email": email,
            "machine_id": machine_id,
            "plan": plan,
            "expiry": expiry.strftime("%Y-%m-%d"),
            "max_tracks": max_tracks,
            "updates_until": updates_until.strftime("%Y-%m-%d"),
        }
        license_data["signature"] = self.sign(license_data)

        return {
            "ok": True,
            "reason": "OK",
            "license": license_data,
            "entitlements": self.entitlements.entitlements_for({
                "licensed": True,
                "plan": plan,
                "max_tracks": max_tracks,
                "updates_until": license_data["updates_until"],
            }),
        }

    def entitlements_for_license(self, license_data):

        if not self.verify(license_data):
            return {
                "ok": False,
                "reason": "INVALID_SIGNATURE",
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

    def plan_from_key(self, license_key):

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

    def sign(self, data):

        payload = {
            key: value
            for key, value in data.items()
            if key != "signature"
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")

        return hmac.new(
            self.secret.encode("utf-8"),
            raw,
            hashlib.sha256
        ).hexdigest()

    def verify(self, data):

        if not data or "signature" not in data:
            return False

        expected = self.sign(data)

        return hmac.compare_digest(
            str(data.get("signature")),
            expected
        )
