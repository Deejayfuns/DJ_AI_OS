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

    # Module to plan mapping for comparison table
    MODULE_PLAN_MAP = {
        # DEMO modules
        "Performance Dashboard": "DEMO",
        "Dashboard": "DEMO",
        "Müzik Doktoru (Analiz)": "DEMO",
        "Kütüphane": "DEMO",
        "Arşiv Koruyucu": "DEMO",
        "Set Oluşturucu": "DEMO",
        "Beat Studio": "DEMO",
        "Song Vault": "DEMO",
        "DJ Coach": "DEMO",
        "Kütüphane Haritası": "DEMO",
        "Astra Chat": "DEMO",
        "Hesap": "DEMO",
        "Ayarlar": "DEMO",
        # PRO modules
        "Deck Studio": "PRO",
        "DJ Booth": "PRO",
        "Canlı Performans": "PRO",
        "Pioneer Link": "PRO",
        "Akıllı Set": "PRO",
        "DJ Profili": "PRO",
        # DJ_ARCHIVE modules
        "Remix Lab": "DJ_ARCHIVE",
        "Cloud Export": "DJ_ARCHIVE",
        # STUDIO modules
        "Nöral Sentez": "STUDIO",
        "Nöral Köprü": "STUDIO",
    }

    PRICING = {
        "PRO": {
            "monthly_usd": 9.99,
            "yearly_usd": 99,
            "headline": "Professional library AI and Rekordbox preparation.",
        },
        "DJ_ARCHIVE": {
            "monthly_usd": 19.99,
            "yearly_usd": 199.99,
            "headline": "Pro tools plus monthly DJ archive downloads.",
        },
        "STUDIO": {
            "monthly_usd": 39.99,
            "yearly_usd": 399.99,
            "headline": "Multi-DJ studio workflow, admin controls, cloud AI.",
        },
        "ENTERPRISE": {
            "monthly_usd": None,
            "yearly_usd": None,
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

    # Max machine activations per plan (enforced server-side)
    MAX_MACHINES = {
        "PRO": 3,
        "DJ_ARCHIVE": 5,
        "STUDIO": 10,
        "ENTERPRISE": 50,
        "OWNER_DEV": 100,
    }

    def pricing_table(self):

        return self.PRICING

    def module_plan_map(self):
        """Return module to minimum plan mapping for comparison table."""
        return self.MODULE_PLAN_MAP

    def updates_active(self, updates_until):

        if not updates_until:
            return False

        try:
            expiry = datetime.strptime(updates_until, "%Y-%m-%d")
        except ValueError:
            return False

        return datetime.now() <= expiry
