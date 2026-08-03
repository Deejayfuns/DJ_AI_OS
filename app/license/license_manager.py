import json
import hashlib
import os
from datetime import datetime

from app.license.machine_id import MachineID
from app.license.license_schema import LicenseSchema
from app.license.entitlements import EntitlementManager


class LicenseManager:

    def __init__(self):

        self.machine = MachineID()
        self.schema = LicenseSchema()
        self.entitlements = EntitlementManager()

        self.license_file = "license.key"

        self.trial_limit = 10000
        self.owner_dev_mode = self.detect_owner_dev_mode()

    # -------------------------
    # LICENSE CREATE CHECK
    # -------------------------

    def generate_signature(self, data):

        raw = json.dumps(
            data,
            sort_keys=True
        )

        return hashlib.sha256(
            raw.encode()
        ).hexdigest()

    # -------------------------
    # LICENSE VALIDATION
    # -------------------------

    def load_license(self):

        try:

            with open(self.license_file, "r") as f:

                return json.load(f)

        except:

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

        if license_data["machine_id"] != current_machine:

            return False, "WRONG MACHINE"

        # EXPIRY CHECK
        expiry = datetime.strptime(
            license_data["expiry"],
            "%Y-%m-%d"
        )

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
                "max_tracks": self.trial_limit,
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

        return (
            os.path.exists("main.py") and
            os.path.isdir("app") and
            os.path.isdir("tests")
        )

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
