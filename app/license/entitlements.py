from datetime import datetime


class EntitlementManager:

    PLAN_FEATURES = {
        "OWNER_DEV": {
            "library_analysis": True,
            "max_tracks": 0,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": True,
            "cloud_trends": True,
            "dj_archive_downloads": True,
            "server_ai": True,
            "team_admin": True,
            "mix_master_engine": True,
            "archive_repair": True,
        },
        "DEMO": {
            "library_analysis": True,
            "max_tracks": 1000,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": False,
            "cloud_trends": True,
            "dj_archive_downloads": False,
            "server_ai": False,
            "team_admin": False,
            "mix_master_engine": True,
            "archive_repair": False,
        },
        "PRO": {
            "library_analysis": True,
            "max_tracks": 50000,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": True,
            "cloud_trends": True,
            "dj_archive_downloads": False,
            "server_ai": True,
            "team_admin": False,
            "mix_master_engine": True,
            "archive_repair": True,
        },
        "DJ_ARCHIVE": {
            "library_analysis": True,
            "max_tracks": 100000,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": True,
            "cloud_trends": True,
            "dj_archive_downloads": True,
            "server_ai": True,
            "team_admin": False,
            "mix_master_engine": True,
            "archive_repair": True,
        },
        "STUDIO": {
            "library_analysis": True,
            "max_tracks": 250000,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": True,
            "cloud_trends": True,
            "dj_archive_downloads": True,
            "server_ai": True,
            "team_admin": True,
            "mix_master_engine": True,
            "archive_repair": True,
        },
        "ENTERPRISE": {
            "library_analysis": True,
            "max_tracks": 0,
            "ai_ear": True,
            "set_builder": True,
            "rekordbox_export": True,
            "cloud_trends": True,
            "dj_archive_downloads": True,
            "server_ai": True,
            "team_admin": True,
            "mix_master_engine": True,
            "archive_repair": True,
        },
    }

    PRICING = {
        "PRO": {
            "monthly_usd": 19,
            "headline": "Professional library AI and Rekordbox preparation.",
        },
        "DJ_ARCHIVE": {
            "monthly_usd": 49,
            "headline": "Pro tools plus monthly DJ archive downloads.",
        },
        "STUDIO": {
            "monthly_usd": 99,
            "headline": "Multi-DJ studio workflow, admin controls, cloud AI.",
        },
        "ENTERPRISE": {
            "monthly_usd": None,
            "headline": "Custom licensing for agencies, venues, and schools.",
        },
    }

    def entitlements_for(self, plan):

        name = str(plan.get("plan", "DEMO") or "DEMO").upper()
        features = dict(self.PLAN_FEATURES.get(name, self.PLAN_FEATURES["DEMO"]))

        max_tracks = int(plan.get("max_tracks", features["max_tracks"]) or 0)

        if max_tracks:
            features["max_tracks"] = max_tracks

        features["updates_active"] = self.updates_active(
            plan.get("updates_until")
        )
        features["plan"] = name
        features["licensed"] = bool(plan.get("licensed"))

        return features

    def can(self, plan, feature):

        return bool(self.entitlements_for(plan).get(feature))

    def pricing_table(self):

        return self.PRICING

    def updates_active(self, updates_until):

        if not updates_until:
            return False

        try:
            expiry = datetime.strptime(updates_until, "%Y-%m-%d")
        except ValueError:
            return False

        return datetime.now() <= expiry
