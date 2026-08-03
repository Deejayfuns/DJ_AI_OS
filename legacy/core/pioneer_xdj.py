"""
Pioneer XDJ RR control skeleton.
- Provides a small abstraction for MIDI-based control using `mido` if available.
- For Rekordbox-level integration, a proper SDK/driver is required; this module is a starting point.
"""

import logging

try:
    import mido
except Exception:
    mido = None


logger = logging.getLogger("pioneer_xdj")


class PioneerXDJ:
    def __init__(self, port_name=None):
        self.port_name = port_name
        self.outport = None
        self.inport = None
        self.mapping = {
            "play": {"type": "note", "note": 0x3C, "velocity": 127},
            "cue": {"type": "note", "note": 0x3D, "velocity": 127},
            "hotcue_1": {"type": "note", "note": 0x20, "velocity": 127},
            "tempo": {"type": "cc", "control": 14},
        }
        self._listening = False
        if mido:
            self.open_ports()

    def set_mapping(self, mapping):
        """Provide a custom mapping dict to override defaults."""
        if isinstance(mapping, dict):
            self.mapping.update(mapping)

    def open_ports(self):
        if not mido:
            logger.warning("mido not installed; Pioneer MIDI disabled")
            return
        try:
            # If a specific port_name is provided, try to open it
            if self.port_name:
                self.outport = mido.open_output(self.port_name)
                self.inport = mido.open_input(self.port_name)
                return

            # else pick the first output that looks like Pioneer
            outputs = mido.get_output_names()
            for name in outputs:
                if "Pioneer" in name or "XDJ" in name:
                    self.outport = mido.open_output(name)
                    break
            inputs = mido.get_input_names()
            for name in inputs:
                if "Pioneer" in name or "XDJ" in name:
                    self.inport = mido.open_input(name)
                    break
        except Exception as exc:
            logger.exception("Failed to open MIDI ports: %s", exc)

    def send_midi(self, message):
        if not self.outport:
            logger.debug("No MIDI outport available")
            return
        try:
            if isinstance(message, mido.Message):
                self.outport.send(message)
            else:
                self.outport.send(mido.Message.from_bytes(message))
        except Exception as exc:
            logger.exception("MIDI send failed: %s", exc)

    def play(self):
        # send mapped play message
        if not mido or not self.outport:
            logger.info("Play requested but MIDI not available")
            return
        cfg = self.mapping.get("play")
        try:
            if cfg and cfg.get("type") == "note":
                msg = mido.Message("note_on", note=cfg.get("note", 60), velocity=cfg.get("velocity", 127))
                self.outport.send(msg)
            elif cfg and cfg.get("type") == "cc":
                msg = mido.Message("control_change", control=cfg.get("control", 0), value=127)
                self.outport.send(msg)
            else:
                logger.info("No valid play mapping configured")
        except Exception as exc:
            logger.exception("Failed to send play message: %s", exc)

    def load_track(self, deck, track_index):
        logger.info("Load track to deck %s index %s (placeholder)", deck, track_index)
        # In many Pioneer setups, loading is a higher-level action via Rekordbox;
        # here we emit a generic note for load action so external mapping tools can pick it up.
        if not mido or not self.outport:
            return
        try:
            cfg = self.mapping.get("load")
            if cfg and cfg.get("type") == "note":
                msg = mido.Message("note_on", note=cfg.get("note", 0x40 + (deck or 0)), velocity=127)
                self.outport.send(msg)
        except Exception:
            pass

    def set_hotcue(self, hotcue_index, action="jump"):
        """Trigger or set a hotcue. action can be 'jump' or 'set'."""
        if not mido or not self.outport:
            return
        try:
            key = f"hotcue_{hotcue_index}"
            cfg = self.mapping.get(key) or self.mapping.get("hotcue_1")
            if cfg and cfg.get("type") == "note":
                msg = mido.Message("note_on", note=cfg.get("note", 0x20 + hotcue_index - 1), velocity=127)
                self.outport.send(msg)
        except Exception:
            pass

    def start_listening(self, callback=None):
        """Start a basic listener thread that invokes callback on incoming messages."""
        if not mido or not self.inport:
            logger.info("MIDI input not available for listening")
            return
        if self._listening:
            return
        self._listening = True

        def _loop():
            for msg in self.inport:
                try:
                    if callback:
                        callback(msg)
                except Exception:
                    logger.exception("Listener callback failed")
                if not self._listening:
                    break

        import threading

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def stop_listening(self):
        self._listening = False

    def close(self):
        try:
            if self.outport:
                self.outport.close()
            if self.inport:
                self.inport.close()
        except Exception:
            pass
