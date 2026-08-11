"""
ORB Module — Beat Studio (DAW)
===============================
Wraps the full DAW: step sequencer, piano roll, arrangement, mixer.
"""
from typing import Any, Dict, Optional

from .base import OrbModule


class BeatStudioModule(OrbModule):
    """DAW module."""

    EVENT_TOPICS = ["daw.track_armed", "daw.arrangement_changed", "daw.mixer_changed"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="beat_studio")
        self._daw = None
        self._project = None

    def start(self) -> None:
        try:
            from app.ai.daw_engine import DAWEngine
            from app.ai.daw_project import DAWProject
            self._daw = DAWEngine()
            self._project = DAWProject()
            self.log("DAW engine + project ready")
        except (ImportError, AttributeError) as e:
            self.log(f"daw engine not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    # Public API
    def create_project(self, name: str = "untitled") -> Any:
        if self._project:
            self._project.name = name
            return self._project
        return None

    def render_track(self, instrument: str, pattern: list) -> Optional[Any]:
        if not self._daw:
            return None
        return self._daw.render_pattern(instrument, pattern)

    def export_mixdown(self, path: str) -> bool:
        if not self._daw:
            return False
        try:
            self._daw.export(path)
            return True
        except Exception as e:
            self.log(f"export failed: {e}", "ERROR")
            return False

    def health_check(self) -> Dict[str, Any]:
        return {"daw_ready": self._daw is not None}