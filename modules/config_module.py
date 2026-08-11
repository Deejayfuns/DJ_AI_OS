"""
ORB Module — Config
===================
Wraps orb_core.config.ConfigStore into an ORB module lifecycle.
"""
from pathlib import Path
from typing import Any, Dict

from .base import OrbModule


class ConfigModule(OrbModule):
    """Centralized config store module."""

    EVENT_TOPICS = ["config.changed"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="config")
        self.store = None

    def start(self) -> None:
        from orb_core.config import ConfigStore
        cfg_path = Path("orb_config.json")
        self.store = ConfigStore(cfg_path)
        self.store.load()
        self.store.watch("*", self._on_change)
        self._running = True
        self._state = "running"
        self.log(f"config store loaded from {cfg_path}")

    def stop(self) -> None:
        if self.store:
            self.store.stop_file_watch()
            self.store.save()
        self._running = False
        self._state = "stopped"

    def _on_change(self, key: str, value: Any) -> None:
        self.publish("config.changed", {"key": key, "value": value})

    # Public API
    def get(self, key: str, default: Any = None) -> Any:
        return self.store.get(key, default) if self.store else default

    def set(self, key: str, value: Any) -> None:
        if self.store:
            self.store.set(key, value)

    def get_all(self) -> Dict[str, Any]:
        return self.store.get_all() if self.store else {}

    def health_check(self) -> Dict[str, Any]:
        return {"running": self._running, "config_keys": len(self.get_all())}