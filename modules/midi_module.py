"""
ORB Module — MIDI Engine
========================
Wraps MIDI I/O + XDJ-RR mapping. Bridges the existing
app/ai/xdj_rr_midi.py translator into the ORB event bus.
"""
from typing import Any, Dict, List, Optional

from .base import OrbModule


class MidiModule(OrbModule):
    """MIDI I/O + Pioneer XDJ-RR mapping module."""

    EVENT_TOPICS = ["midi.event", "midi.connected", "midi.disconnected"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="midi_engine")
        self._input_port = None
        self._output_port = None
        self._translator = None
        self._layer = 1
        self._poll_task = None
        self._device_name = ""

    def start(self) -> None:
        # Import translator lazily so ORB core can boot without it
        try:
            from app.ai.xdj_rr_midi import translate
            self._translator = translate
        except ImportError:
            self.log("xdj_rr_midi translator not available", "WARN")

        self._connect()
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        if self._input_port:
            try:
                self._input_port.close()
            except Exception:
                pass
            self._input_port = None
        self._running = False
        self._state = "stopped"

    # ------------------------------------------------------------------
    def _connect(self) -> None:
        import mido

        names = mido.get_input_names()
        # Prefer Pioneer device, else first port containing "XDJ" or "MIDI"
        self._device_name = ""
        for n in names:
            if "XDJ" in n.upper() or "PIONEER" in n.upper():
                self._device_name = n
                break
        if not self._device_name and names:
            self._device_name = names[0]

        if self._device_name:
            try:
                self._input_port = mido.open_input(self._device_name)
                self.log(f"connected to {self._device_name}")
                self.publish("midi.connected", {"name": self._device_name})
            except Exception as e:
                self.log(f"midi connect failed: {e}", "ERROR")
                self._input_port = None

    def poll(self) -> None:
        """Poll pending MIDI messages (called from UI loop or background task)."""
        if not self._input_port or not self._translator:
            return
        for msg in self._input_port.iter_pending():
            evt = self._translator(msg, layer=self._layer)
            if evt:
                evt["source"] = self._device_name
                self.publish("midi.event", evt)

    def set_layer(self, layer: int) -> None:
        """Switch pad layer (1 = decks A/B, 2 = decks C/D)."""
        self._layer = 1 if layer == 1 else 2

    # Public API used by UI
    def get_connected_device(self) -> str:
        return self._device_name

    def get_input_names(self) -> List[str]:
        import mido
        return mido.get_input_names()

    def health_check(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "connected": self._input_port is not None,
            "device": self._device_name,
            "layer": self._layer,
        }