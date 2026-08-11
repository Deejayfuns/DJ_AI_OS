"""
ORB Module — Platform
=====================
Exposes the cross-platform abstraction as a module service.
"""
from typing import Any, Dict, List

from .base import OrbModule


class PlatformModule(OrbModule):
    """Platform abstraction service module."""

    def __init__(self, kernel=None):
        super().__init__(kernel, name="platform")

    def start(self) -> None:
        from orb_core.platform import current_platform, Audio, MIDI, HID, FS, Process
        self._plat = current_platform()
        self._audio = Audio
        self._midi = MIDI
        self._hid = HID
        self._fs = FS
        self._process = Process
        self._running = True
        self._state = "running"
        self.log(f"platform {self._plat.value} ready")

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    # Public API
    def platform(self) -> str:
        return self._plat.value

    def audio_backends(self) -> List[str]:
        return self._audio.backends()

    def midi_ports(self) -> List[str]:
        return self._midi.get_input_names()

    def enumerate_hid(self, vid: int = None, pid: int = None) -> List[Dict]:
        return self._hid.enumerate(vid, pid)

    def normalize_path(self, path: str) -> str:
        return self._fs.normalize_path(path)

    def health_check(self) -> Dict[str, Any]:
        return {"platform": self._plat.value, "audio_backends": self.audio_backends()}