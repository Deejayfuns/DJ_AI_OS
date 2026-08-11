"""
ORB Module — Cloud Sync
=======================
Wraps portal client, telemetry, and update engine.
"""
from typing import Any, Dict

from .base import OrbModule


class CloudModule(OrbModule):
    """Cloud sync module."""

    EVENT_TOPICS = ["cloud.synced", "cloud.update_available"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="cloud_sync")
        self._portal = None
        self._telemetry = None
        self._updater = None

    def start(self) -> None:
        # Cloud is optional — only enable if user opted in (config)
        cfg = self.get_module("config")
        if cfg and cfg.get("network.use_cloud"):
            try:
                from app.cloud.portal_client import PortalClient
                from app.cloud.update_engine import UpdateEngine
                self._portal = PortalClient()
                self._updater = UpdateEngine()
                self.log("cloud services ready")
            except ImportError as e:
                self.log(f"cloud not available: {e}", "WARN")
        else:
            self.log("cloud disabled (opt-in)")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    def check_update(self) -> Dict[str, Any]:
        if self._updater is None:
            return {"update": False}
        return self._updater.check()

    def health_check(self) -> Dict[str, Any]:
        return {"cloud_enabled": self._portal is not None}