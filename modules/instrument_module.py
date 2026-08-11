"""
ORB Module — Instruments
========================
Wraps synth instruments: drums, melodic, melodic tech, serum-style.
"""
from typing import Any, Dict, List, Optional

from .base import OrbModule


class InstrumentModule(OrbModule):
    """Instrument plugin registry module."""

    EVENT_TOPICS = ["instrument.registered"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="instruments")
        self._registry = {}
        self._synth = None

    def start(self) -> None:
        try:
            from app.ai import instruments as inst
            self._synth = inst
            self._registry = {
                name: inst.get_instrument(name)
                for name in inst.list_instruments()
            }
            self.log(f"{len(self._registry)} instruments registered")
        except (ImportError, AttributeError) as e:
            self.log(f"instruments not available: {e}", "WARN")
            self._registry = {}
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    # Public API
    def list_instruments(self) -> List[str]:
        return list(self._registry.keys())

    def get_instrument(self, name: str):
        return self._registry.get(name)

    def render(self, name: str, note=None, velocity=1.0):
        plugin = self._registry.get(name)
        if not plugin:
            return None
        return plugin.render(note=note, velocity=velocity)

    def health_check(self) -> Dict[str, Any]:
        return {"instrument_count": len(self._registry)}