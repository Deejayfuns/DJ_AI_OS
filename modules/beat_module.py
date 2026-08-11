"""
ORB Module — Beat Engine
========================
Wraps beatgrid analysis, tempo detection, and beat sync.
"""
from typing import Any, Dict, Optional

from .base import OrbModule


class BeatModule(OrbModule):
    """Beatgrid engine module."""

    EVENT_TOPICS = ["beat.analyzed", "beat.sync"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="beat_engine")
        self._engine = None

    def start(self) -> None:
        try:
            from app.ai.beat_grid_engine import BeatGridEngine
            self._engine = BeatGridEngine()
        except ImportError as e:
            self.log(f"beat_grid_engine not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._engine = None
        self._running = False
        self._state = "stopped"

    # Public API
    def analyze(self, path: str) -> Optional[Dict[str, Any]]:
        if not self._engine:
            return None
        try:
            result = self._engine.analyze_file(path)
            self.publish("beat.analyzed", {"path": path, "result": result})
            return result
        except Exception as e:
            self.log(f"analysis failed: {e}", "ERROR")
            return None

    def sync_decks(self, deck_a, deck_b) -> None:
        self.publish("beat.sync", {"a": deck_a, "b": deck_b})

    def health_check(self) -> Dict[str, Any]:
        return {"engine_ready": self._engine is not None}