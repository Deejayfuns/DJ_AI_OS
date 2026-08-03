import json
import os
import urllib.error
import urllib.request
from datetime import datetime

from app.server.license_service import LicenseService


class CommercialAPIClient:

    def __init__(self, base_url="https://api.dj-ai-os.example"):

        self.base_url = base_url.rstrip("/")

    def account_status(self, plan, entitlements):

        return {
            "online": False,
            "mode": "LOCAL_STUB",
            "base_url": self.base_url,
            "checked_at": datetime.now().isoformat(),
            "account": {
                "email": "not-connected",
                "subscription": plan.get("plan", "DEMO"),
                "licensed": plan.get("licensed", False),
            },
            "entitlements": entitlements,
            "next_actions": [
                "Connect payment provider webhook",
                "Issue signed license token",
                "Sync cloud archive permissions",
                "Enable server-side AI analysis jobs",
            ],
        }

    def endpoint_contract(self):

        return {
            "health": f"{self.base_url}/health",
            "activate": f"{self.base_url}/activate",
            "entitlements": f"{self.base_url}/entitlements",
            "checkout": f"{self.base_url}/checkout",
            "cloud_packs": f"{self.base_url}/cloud/packs",
            "cloud_download": (
                f"{self.base_url}/cloud/packs/{{pack_id}}/download"
            ),
        }

    def activation_payload(self, email, license_key, machine_id):

        return {
            "email": email,
            "license_key": license_key,
            "machine_id": machine_id,
            "client": "DJ AI OS Desktop",
        }

    def activate_license(self, email, license_key, machine_id):

        payload = self.activation_payload(email, license_key, machine_id)

        try:
            return self.post_json(
                self.endpoint_contract()["activate"],
                payload
            )
        except Exception:
            service = LicenseService()
            result = service.activate(email, license_key, machine_id)
            result["mode"] = "LOCAL_DEV_ACTIVATION"
            return result

    def post_json(self, url, payload, timeout=8):

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            return {
                "ok": False,
                "reason": f"HTTP_{exc.code}",
                "detail": body,
            }

    def write_checkout_intent(self, plan_name, output_folder="DJ_COMMERCIAL"):

        os.makedirs(output_folder, exist_ok=True)
        path = os.path.abspath(
            os.path.join(output_folder, f"checkout_{plan_name.lower()}.json")
        )

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "created_at": datetime.now().isoformat(),
                    "plan": plan_name,
                    "status": "PENDING_PAYMENT_PROVIDER",
                    "provider_slots": [
                        "Stripe Checkout",
                        "Paddle",
                        "iyzico",
                        "PayTR",
                    ],
                    "webhook_contract": {
                        "subscription_created": "issue license",
                        "payment_failed": "suspend cloud entitlements",
                        "subscription_cancelled": "downgrade to demo",
                    },
                },
                handle,
                indent=2
            )

        return path
