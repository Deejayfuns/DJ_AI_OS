"""
ORB Module — HID Engine
=======================
Wraps the Pioneer XDJ-RR/RX2 HID protocol engine.
"""
from typing import Any, Dict, Optional

from .base import OrbModule


class HidModule(OrbModule):
    """Pioneer HID engine module."""

    EVENT_TOPICS = ["hid.event", "hid.connected", "hid.disconnected"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="hid_engine")
        self._engine = None
        self._device = None

    def start(self) -> None:
        try:
            from app.ai.hid_engine import HIDDeckController
            self._engine = HIDDeckController
            self.log("hid_engine available")
        except ImportError as e:
            self.log(f"hid_engine not available: {e}", "WARN")
            self._engine = None

        # Try to detect a connected Pioneer unit
        self._detect()
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None
        self._running = False
        self._state = "stopped"

    def _detect(self) -> None:
        if not self._engine:
            return
        try:
            dev = self._engine()  # assume engine detects device on construct
            self._device = dev
            self.publish("hid.connected", {"type": "pioneer"})
            self.log("Pioneer HID device connected")
        except Exception as e:
            self.log(f"no HID device: {e}")

    def health_check(self) -> Dict[str, Any]:
        return {"running": self._running, "connected": self._device is not None}