class LicenseSchema:

    def validate_structure(self, license_data):

        required = [
            "machine_id",
            "plan",
            "expiry",
            "max_tracks",
            "updates_until",
            "issued_at",
            "nonce",
            "signature"
        ]

        for r in required:

            if r not in license_data:
                return False

        return True
