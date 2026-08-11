"""
DJ AI OS — Portal Client (Cloud Connection)

Main cloud backend connection for the DJ AI OS platform.
Handles: auth, sync, data collection, archive delivery.

The Windows app = client for our cloud portal.
All user data flows through here (anonymized).
"""

import os
import json
import hashlib
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional


class PortalClient:
    """
    Cloud portal connection manager.
    """

    def __init__(self, base_url="https://api.djaios.com", config_dir="data"):
        self.base_url = base_url.rstrip("/")
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, "portal_config.json")
        self.machine_id = self._get_machine_id()
        self.user_token = None
        self.is_connected = False
        self._sync_queue = []
        self._load_config()

    def _get_machine_id(self) -> str:
        """Generate unique machine identifier."""
        try:
            import platform
            import socket
            raw = f"{platform.node()}-{platform.machine()}-{socket.gethostname()}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except Exception:
            return uuid.uuid4().hex[:16]

    def _load_config(self):
        """Load saved config."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                    self.user_token = config.get("token")
                    self.is_connected = config.get("connected", False)
        except Exception:
            pass

    def _save_config(self):
        """Save config to disk."""
        os.makedirs(self.config_dir, exist_ok=True)
        config = {
            "machine_id": self.machine_id,
            "token": self.user_token,
            "connected": self.is_connected,
            "last_sync": datetime.now().isoformat(),
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    # ============================================================
    # AUTH
    # ============================================================

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login to portal."""
        # Stub — in production, POST to /auth/login
        self.user_token = hashlib.sha256(f"{email}:{password}".encode()).hexdigest()[:32]
        self.is_connected = True
        self._save_config()

        return {
            "ok": True,
            "token": self.user_token,
            "user": {"email": email, "plan": "FREE"},
            "message": "Giriş başarılı",
        }

    def activate_license(self, license_key: str) -> Dict[str, Any]:
        """Activate a license key."""
        # Stub — validate key format
        if not license_key or len(license_key) < 10:
            return {"ok": False, "message": "Geçersiz lisans anahtarı"}

        self.user_token = hashlib.sha256(license_key.encode()).hexdigest()[:32]
        self.is_connected = True
        self._save_config()

        return {
            "ok": True,
            "plan": "PRO",
            "expires": "2027-01-01",
            "message": "Lisans aktif edildi!",
        }

    def logout(self):
        """Logout from portal."""
        self.user_token = None
        self.is_connected = False
        self._save_config()

    def get_account_info(self) -> Dict[str, Any]:
        """Get current account info."""
        return {
            "connected": self.is_connected,
            "machine_id": self.machine_id,
            "has_token": bool(self.user_token),
            "plan": "PRO" if self.is_connected else "FREE",
        }

    # ============================================================
    # DATA SYNC
    # ============================================================

    def sync_library_fingerprint(self, library_stats: Dict) -> Dict[str, Any]:
        """
        Sync anonymized library fingerprint to cloud.
        This is how we build our master archive:
        - We never get actual files
        - We get fingerprints: BPM, key, genre, duration, bitrate
        - Enough to know WHAT tracks exist, not WHERE they are
        """
        fingerprint = {
            "machine_id": self.machine_id,
            "timestamp": datetime.now().isoformat(),
            "total_tracks": library_stats.get("total_tracks", 0),
            "genre_distribution": library_stats.get("genres", {}),
            "bpm_distribution": library_stats.get("bpm_distribution", {}),
            "key_distribution": library_stats.get("keys", {}),
            "energy_profile": library_stats.get("energy_profile", {}),
            "mood_distribution": library_stats.get("moods", {}),
            "bitrate_distribution": library_stats.get("bitrates", {}),
            "top_artists": library_stats.get("top_artists", []),
            "total_duration_hours": library_stats.get("total_duration_hours", 0),
        }

        # Queue for sync
        self._sync_queue.append({
            "type": "library_fingerprint",
            "data": fingerprint,
            "queued_at": datetime.now().isoformat(),
        })

        return {
            "ok": True,
            "queued": True,
            "message": "Kütüphane parmak izi kuyruğa alındı",
        }

    def sync_listening_data(self, play_data: Dict) -> Dict[str, Any]:
        """
        Sync anonymized listening data.
        This builds our toplist:
        - Track fingerprint (not the file)
        - Play count, skip rate, repeat plays
        - Time of day, day of week
        - Duration played before skip
        """
        listening = {
            "machine_id": self.machine_id,
            "timestamp": datetime.now().isoformat(),
            "track_fingerprint": play_data.get("fingerprint", ""),
            "duration_played": play_data.get("duration_played", 0),
            "total_duration": play_data.get("total_duration", 0),
            "skipped": play_data.get("skipped", False),
            "skip_time": play_data.get("skip_time", 0),
            "context": play_data.get("context", "library"),  # library, set, live
            "bpm": play_data.get("bpm", 0),
            "key": play_data.get("key", ""),
            "genre": play_data.get("genre", ""),
        }

        self._sync_queue.append({
            "type": "listening_data",
            "data": listening,
            "queued_at": datetime.now().isoformat(),
        })

        return {"ok": True, "queued": True}

    def sync_set_data(self, set_data: Dict) -> Dict[str, Any]:
        """Sync DJ set performance data."""
        set_record = {
            "machine_id": self.machine_id,
            "timestamp": datetime.now().isoformat(),
            "style": set_data.get("style", ""),
            "duration_minutes": set_data.get("duration_minutes", 0),
            "track_count": set_data.get("track_count", 0),
            "avg_bpm": set_data.get("avg_bpm", 0),
            "energy_flow": set_data.get("energy_flow", []),
            "genre_mix": set_data.get("genre_mix", {}),
        }

        self._sync_queue.append({
            "type": "set_data",
            "data": set_record,
            "queued_at": datetime.now().isoformat(),
        })

        return {"ok": True, "queued": True}

    def flush_sync_queue(self) -> Dict[str, Any]:
        """Send all queued data to server."""
        if not self._sync_queue:
            return {"ok": True, "sent": 0}

        count = len(self._sync_queue)
        # In production: POST to /sync/batch
        self._sync_queue.clear()

        return {
            "ok": True,
            "sent": count,
            "message": f"{count} kayıt gönderildi",
        }

    # ============================================================
    # WEEKLY DELIVERY
    # ============================================================

    def get_weekly_packs(self) -> List[Dict]:
        """Get available weekly archive packs for download."""
        # Stub — in production: GET /archive/weekly
        return [
            {
                "id": "week_2026_31",
                "name": "Week 31 - Afro House Essentials",
                "description": "This week's top Afro House tracks from global DJs",
                "track_count": 25,
                "size_mb": 180,
                "genres": ["Afro House", "Amapiano", "Gqom"],
                "created_at": "2026-08-04",
                "downloaded": False,
            },
            {
                "id": "week_2026_30",
                "name": "Week 30 - Tech House Selection",
                "description": "Fresh tech house from the underground",
                "track_count": 30,
                "size_mb": 220,
                "genres": ["Tech House", "Minimal", "Deep Tech"],
                "created_at": "2026-07-28",
                "downloaded": True,
            },
            {
                "id": "week_2026_29",
                "name": "Week 29 - Melodic Journey",
                "description": "Melodic house and progressive selection",
                "track_count": 20,
                "size_mb": 150,
                "genres": ["Melodic House", "Progressive", "Trance"],
                "created_at": "2026-07-21",
                "downloaded": True,
            },
        ]

    def download_weekly_pack(self, pack_id: str) -> Dict[str, Any]:
        """Download a weekly archive pack."""
        # Stub — in production: GET /archive/{pack_id}/download
        return {
            "ok": True,
            "pack_id": pack_id,
            "download_path": f"DJ_CLOUD_DOWNLOADS/{pack_id}/",
            "message": "Pack indirildi",
        }

    # ============================================================
    # TOPLIST
    # ============================================================

    def get_global_toplist(self, limit: int = 50) -> List[Dict]:
        """Get global toplist from aggregated user data."""
        # Stub — in production: GET /toplist/global
        return [
            {"rank": i + 1, "fingerprint": f"track_{i}", "play_count": 1000 - i * 20}
            for i in range(min(limit, 50))
        ]

    def get_genre_toplist(self, genre: str, limit: int = 25) -> List[Dict]:
        """Get genre-specific toplist."""
        # Stub — in production: GET /toplist/genre/{genre}
        return []

    def get_local_toplist(self, limit: int = 25) -> List[Dict]:
        """Get user's personal toplist from their listening data."""
        # This stays local — we never upload the actual list
        return []
