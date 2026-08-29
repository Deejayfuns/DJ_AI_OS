import json
import os
import sys
from pathlib import Path
from datetime import datetime

from app.license.machine_id import MachineID
from app.license.license_schema import LicenseSchema
from app.license.entitlements import EntitlementManager
from app.license import signature as sig


def _resolve_license_path() -> Path:
    """Resolve license file path: frozen build → APPDATA/DJ_AI_OS/license.key, dev → repo root."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or Path.home())
        return base / "DJ_AI_OS" / "license.key"
    return Path.cwd() / "license.key"


class LicenseManager:

    def __init__(self):

        self.machine = MachineID()
        self.schema = LicenseSchema()
        self.entitlements = EntitlementManager()

        self.license_file = str(_resolve_license_path())

        self.owner_dev_mode = self.detect_owner_dev_mode()

    # -------------------------
    # LICENSE CREATE CHECK
    # -------------------------

    def generate_signature(self, data):

        # Ed25519 imzası — YALNIZCA vendor makinesinde çalışır (private key gerekir).
        # Client'ta asla imza üretilmez; sadece doğrulanır.
        return sig.sign(data)

    # -------------------------
    # LICENSE VALIDATION
    # -------------------------

    def load_license(self):

        try:

            with open(self.license_file, "r") as f:

                return json.load(f)

        except Exception:

            return None

    def save_license(self, license_data):

        with open(self.license_file, "w", encoding="utf-8") as f:
            json.dump(license_data, f, indent=2)

        return self.get_plan()

    def is_valid(self):

        license_data = self.load_license()

        if not license_data:

            return False, "NO LICENSE"

        if not self.schema.validate_structure(license_data):

            return False, "INVALID STRUCTURE"

        # MACHINE CHECK
        current_machine = self.machine.generate()

        if license_data.get("machine_id") != current_machine:

            return False, "WRONG MACHINE"

        # SIGNATURE CHECK — client gömülü vendor public key ile doğrular.
        # Forge için private key gerekir; bu key client'ta asla bulunmaz.
        if not sig.verify(license_data, license_data.get("signature", "")):

            return False, "INVALID SIGNATURE"

        # EXPIRY CHECK (hazırlıksız parse artık boot'u çökertmez)
        try:
            expiry = datetime.strptime(
                license_data.get("expiry", ""),
                "%Y-%m-%d"
            )
        except (ValueError, TypeError):
            return False, "INVALID EXPIRY"

        if datetime.now() > expiry:

            return False, "EXPIRED"

        return True, "OK"

    def get_plan(self):

        valid, reason = self.is_valid()
        license_data = self.load_license()

        if self.owner_dev_mode:
            plan = {
                "licensed": True,
                "plan": "OWNER_DEV",
                "reason": "LOCAL_OWNER_DEV_MODE",
                "max_tracks": 0,
                "updates_until": "2099-12-31"
            }
            plan["entitlements"] = self.entitlements.entitlements_for(plan)
            return plan

        if not valid or not license_data:
            plan = {
                "licensed": False,
                "plan": "DEMO",
                "reason": reason,
                # DEMO limitini entitlements tek kaynağından al (tutarsızlık düzeltildi)
                "max_tracks": self.entitlements.PLAN_FEATURES["DEMO"]["max_tracks"],
                "updates_until": None
            }
            plan["entitlements"] = self.entitlements.entitlements_for(plan)
            return plan

        plan = {
            "licensed": True,
            "plan": license_data.get("plan", "PRO"),
            "reason": "OK",
            "max_tracks": int(
                license_data.get("max_tracks", 0) or 0
            ),
            "updates_until": license_data.get("updates_until")
        }
        plan["entitlements"] = self.entitlements.entitlements_for(plan)

        return plan

    def detect_owner_dev_mode(self):

        # Kaynak ağacı koşulu: paketlenmiş build'de main.py+app+tests yoktur,
        # dolayısıyla bu dal pakete asla girmez.
        source_tree = (
            os.path.exists("main.py") and
            os.path.isdir("app") and
            os.path.isdir("tests")
        )
        if not source_tree:
            return False

        # AÇIK bayrak: env DJ_AI_OS_DEV=1 VEYA repo-root'taki gitignored dev.flag.
        # İkisi de yoksa DEMO çalışır — böylece demo/limit yolu geliştirirken test edilebilir.
        env_dev = os.environ.get("DJ_AI_OS_DEV", "").strip().lower()
        if env_dev in {"1", "true", "yes", "on"}:
            return True

        return os.path.exists("dev.flag")

    def machine_id_display(self):

        return self.machine.generate()

    def can_use(self, feature):

        return self.entitlements.can(
            self.get_plan(),
            feature
        )

    # -------------------------
    # DEMO LIMIT CHECK
    # -------------------------

    def check_limit(self, processed_count):

        plan = self.get_plan()
        max_tracks = plan["max_tracks"]

        if max_tracks <= 0:
            return True

        return processed_count < max_tracks
