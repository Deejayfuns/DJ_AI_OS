"""
ORB Module — Audio Engine
=========================
Wraps audio playback, analysis, and quality processing.
"""
from typing import Any, Dict, Optional

from .base import OrbModule


class AudioModule(OrbModule):
    """Audio engine module."""

    EVENT_TOPICS = ["audio.started", "audio.stopped", "audio.track_loaded"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="audio_engine")
        self._player = None
        self._backend = "auto"

    def start(self) -> None:
        from orb_core.platform import Audio as AudioAbstraction
        self._abstraction = AudioAbstraction
        available = self._abstraction.backends()
        self._backend = available[0] if available else "none"
        self._running = True
        self._state = "running"
        self.log(f"audio backend: {self._backend}")

    def stop(self) -> None:
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
            self._player = None
        self._running = False
        self._state = "stopped"

    # Public API
    def create_player(self, **kwargs):
        if self._backend == "none":
            return None
        self._player = self._abstraction.create_player(self._backend, **kwargs)
        return self._player

    def play_track(self, path: str) -> bool:
        player = self.create_player()
        if player is None:
            return False
        try:
            player.set_mrl(path)
            player.play()
            self.publish("audio.started", {"path": path})
            return True
        except Exception as e:
            self.log(f"play failed: {e}", "ERROR")
            return False

    def health_check(self) -> Dict[str, Any]:
        return {"backend": self._backend, "player": self._player is not None}