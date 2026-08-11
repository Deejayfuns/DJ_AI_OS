"""
ORB Module — Rekordbox Bridge
=============================
Wraps Rekordbox XML import/export.
"""
from typing import Any, Dict, List, Optional

from .base import OrbModule


class RekordboxModule(OrbModule):
    """Rekordbox XML bridge module."""

    def __init__(self, kernel=None):
        super().__init__(kernel, name="rekordbox")
        self._importer = None

    def start(self) -> None:
        try:
            from app.core.rekordbox_import import RekordboxImporter
            self._importer = RekordboxImporter
            self.log("rekordbox importer available")
        except (ImportError, AttributeError) as e:
            self.log(f"rekordbox importer not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    def import_xml(self, xml_path: str) -> List[Dict[str, Any]]:
        if not self._importer:
            return []
        try:
            return self._importer.parse(xml_path)
        except Exception as e:
            self.log(f"import failed: {e}", "ERROR")
            return []

    def health_check(self) -> Dict[str, Any]:
        return {"importer_ready": self._importer is not None}