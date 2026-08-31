import json
import os
import urllib.error
import urllib.request
from datetime import datetime

from app.license import signature as sig


class CommercialAPIClient:

    def __init__(self, base_url=None):

        # Gerçek API adresini env ile verilebilir yap (örn. DJ_AI_OS_API_URL).
        self.base_url = (
            base_url
            or os.environ.get("DJ_AI_OS_API_URL", "")
            or "https://api.dj-ai-os.example"
        ).rstrip("/")

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
            "activate": f"{self.base_url}/api/activate",
            "entitlements": f"{self.base_url}/api/entitlements",
            "checkout": f"{self.base_url}/api/checkout",
            "customer_portal": f"{self.base_url}/api/customer-portal",
            "webhooks_stripe": f"{self.base_url}/api/webhooks/stripe",
            "cloud_packs": f"{self.base_url}/api/cloud/packs",
            "cloud_download": (
                f"{self.base_url}/api/cloud/packs/{{pack_id}}/download"
            ),
            "update_manifest": f"{self.base_url}/api/update/manifest",
            "admin": f"{self.base_url}/admin/",
        }

    def activation_payload(self, email, license_key, machine_id):

        return {
            "email": email,
            "license_key": license_key,
            "machine_id": machine_id,
            "client": "DJ AI OS Desktop",
        }

    def create_checkout(self, plan_name, email, success_url="", cancel_url=""):

        payload = {
            "plan": plan_name,
            "email": email,
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        return self.post_json(self.endpoint_contract()["checkout"], payload)

    def get_customer_portal_url(self, stripe_customer_id, return_url=""):

        payload = {
            "stripe_customer_id": stripe_customer_id,
            "return_url": return_url,
        }
        return self.post_json(self.endpoint_contract()["customer_portal"], payload)

    def activate_license(self, email, license_key, machine_id):

        payload = self.activation_payload(email, license_key, machine_id)

        try:
            result = self.post_json(
                self.endpoint_contract()["activate"],
                payload
            )
            # Çevrimiçi sunucu imzalı lisans döndürdüyse kullan.
            if isinstance(result, dict) and result.get("ok") and result.get("license"):
                return result
        except Exception:
            pass

        # Sunucu yok / ulaşılamıyor. Yerel imzalama YALNIZCA vendor makinesinde
        # çalışır (private key gerekir). Paketlenmiş client'ta key yoktur —
        # sahte lisans üretilemez, kullanıcıya temiz bir offline durumu döner.
        # Not: Bu kod production build'de asla çalışmaz çünkü vendor private key
        # paketlenmez (gitignored). Sadece geliştirme ortamında sig.has_signing_key()
        # True dönebiliyordu, ancak LicenseService artık session gerektirdiği için
        # lokal imzalama path'i production'da kullanılamaz ve güvenli bir şekilde
        # atlanmalıdır.
        return {
            "ok": False,
            "reason": "SERVER_UNREACHABLE_NO_LOCAL_KEY",
            "license": None,
            "mode": "OFFLINE",
            "message": (
                "Sunucuya ulaşılamadı ve bu makinede yerel imzalama yok. "
                "Lütfen çevrimiçi aktivasyon kullanın veya vendor'dan "
                "çevrimdışı imzalı lisans edinin."
            ),
        }

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
