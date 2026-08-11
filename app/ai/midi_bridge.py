"""
DJ AI OS — MIDI Controller Bridge

Send/receive MIDI to/from DJ controllers.
Supports: DDJ-400, DDJ-1000, CDJ-2000, XDJ-XZ (via MIDI mapping).
Virtual MIDI port for testing (no hardware needed).

Usage:
    bridge = MIDIBridge()
    bridge.send_bpm_sync("A", 128.5)
    bridge.send_hot_cue("A", 1, "GREEN")
    bridge.start_listening()
"""

import os
import json
import time
import threading
from typing import Callable, Dict, List, Optional, Tuple

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

# MIDI CC numbers for DJ controllers
CC_NUMBERS = {
    "crossfader": 8,
    "volume_a": 0,
    "volume_b": 1,
    "eq_high_a": 7,
    "eq_mid_a": 10,
    "eq_low_a": 14,
    "eq_high_b": 8,
    "eq_mid_b": 11,
    "eq_low_b": 15,
    "filter_a": 16,
    "filter_b": 17,
    "jog_a": 48,
    "jog_b": 49,
    "tempo_a": 50,
    "tempo_b": 51,
    "play_a": 64,
    "play_b": 65,
    "cue_a": 66,
    "cue_b": 67,
    "sync_a": 68,
    "sync_b": 69,
    "loop_in_a": 70,
    "loop_out_a": 71,
    "loop_in_b": 72,
    "loop_out_b": 73,
    "hot_cue_1_a": 74,
    "hot_cue_2_a": 75,
    "hot_cue_3_a": 76,
    "hot_cue_4_a": 77,
    "hot_cue_1_b": 78,
    "hot_cue_2_b": 79,
    "hot_cue_3_b": 80,
    "hot_cue_4_b": 81,
}

# Note numbers for hot cues
HOT_CUE_NOTES = {
    "a": [60, 61, 62, 63, 64, 65, 66, 67],
    "b": [72, 73, 74, 75, 76, 77, 78, 79],
}

# LED colors (Pioneer-style)
LED_COLORS = {
    "OFF": 0,
    "RED": 1,
    "GREEN": 2,
    "YELLOW": 3,
    "BLUE": 4,
    "PURPLE": 5,
    "CYAN": 6,
    "WHITE": 7,
}


class MIDIBridge:
    """
    MIDI bridge for DJ controller integration.
    """

    def __init__(self, input_port=None, output_port=None):
        self.input_port_name = input_port
        self.output_port_name = output_port
        self._input_port = None
        self._output_port = None
        self._listening = False
        self._listener_thread = None
        self._callbacks = {}
        self._mapping = {}

    def connect(self) -> bool:
        """Connect to MIDI ports."""
        if not HAS_MIDO:
            print("MIDI: mido not installed. pip install mido")
            return False

        try:
            if self.input_port_name:
                self._input_port = mido.open_input(self.input_port_name)
                print(f"MIDI: Connected to input '{self.input_port_name}'")

            if self.output_port_name:
                self._output_port = mido.open_output(self.output_port_name)
                print(f"MIDI: Connected to output '{self.output_port_name}'")

            return True

        except Exception as e:
            print(f"MIDI: Connection failed: {e}")
            return False

    def connect_virtual(self) -> bool:
        """Connect to virtual MIDI port (for testing without hardware)."""
        if not HAS_MIDO:
            print("MIDI: mido not installed")
            return False

        try:
            self._input_port = mido.open_input("DJ AI OS Input", virtual=True)
            self._output_port = mido.open_output("DJ AI OS Output", virtual=True)
            print("MIDI: Virtual ports created")
            return True
        except Exception as e:
            print(f"MIDI: Virtual port failed: {e}")
            return False

    def disconnect(self):
        """Disconnect MIDI ports."""
        self._listening = False
        if self._listener_thread:
            self._listener_thread.join(timeout=2)
            self._listener_thread = None

        if self._input_port:
            self._input_port.close()
            self._input_port = None
        if self._output_port:
            self._output_port.close()
            self._output_port = None

    # ============================================================
    # SEND COMMANDS
    # ============================================================

    def send_cc(self, channel, cc, value):
        """Send a MIDI CC message."""
        if not self._output_port:
            return False

        try:
            msg = mido.Message("control_change", channel=channel, control=cc, value=value)
            self._output_port.send(msg)
            return True
        except Exception:
            return False

    def send_note(self, channel, note, velocity=127):
        """Send a MIDI note on message."""
        if not self._output_port:
            return False

        try:
            msg = mido.Message("note_on", channel=channel, note=note, velocity=velocity)
            self._output_port.send(msg)
            return True
        except Exception:
            return False

    def send_note_off(self, channel, note):
        """Send a MIDI note off message."""
        if not self._output_port:
            return False

        try:
            msg = mido.Message("note_off", channel=channel, note=note, velocity=0)
            self._output_port.send(msg)
            return True
        except Exception:
            return False

    def send_bpm_sync(self, deck, bpm):
        """Send BPM sync to controller."""
        cc = CC_NUMBERS.get(f"tempo_{deck.lower()}", 50)
        # BPM mapped to 0-127 range (60-200 BPM)
        value = int((bpm - 60) / 140 * 127)
        value = max(0, min(127, value))
        return self.send_cc(0, cc, value)

    def send_play(self, deck):
        """Send play command."""
        cc = CC_NUMBERS.get(f"play_{deck.lower()}", 64)
        return self.send_cc(0, cc, 127)

    def send_stop(self, deck):
        """Send stop command."""
        cc = CC_NUMBERS.get(f"play_{deck.lower()}", 64)
        return self.send_cc(0, cc, 0)

    def send_cue(self, deck):
        """Send cue command."""
        cc = CC_NUMBERS.get(f"cue_{deck.lower()}", 66)
        return self.send_cc(0, cc, 127)

    def send_sync(self, deck):
        """Send sync command."""
        cc = CC_NUMBERS.get(f"sync_{deck.lower()}", 68)
        return self.send_cc(0, cc, 127)

    def send_crossfader(self, position):
        """Send crossfader position (0.0 - 1.0)."""
        cc = CC_NUMBERS["crossfader"]
        value = int(position * 127)
        return self.send_cc(0, cc, value)

    def send_volume(self, deck, volume):
        """Send volume for deck (0.0 - 1.0)."""
        cc = CC_NUMBERS.get(f"volume_{deck.lower()}", 0)
        value = int(volume * 127)
        return self.send_cc(0, cc, value)

    def send_hot_cue(self, deck, number, color="GREEN"):
        """Set hot cue LED color."""
        channel = 0
        notes = HOT_CUE_NOTES.get(deck.lower(), HOT_CUE_NOTES["a"])
        if 1 <= number <= len(notes):
            note = notes[number - 1]
            velocity = LED_COLORS.get(color, LED_COLORS["GREEN"])
            return self.send_note(channel, note, velocity)
        return False

    def send_loop(self, deck, in_point, out_point):
        """Send loop in/out points."""
        # Simplified: map to CC values
        in_cc = CC_NUMBERS.get(f"loop_in_{deck.lower()}", 70)
        out_cc = CC_NUMBERS.get(f"loop_out_{deck.lower()}", 71)

        in_val = int(max(0, min(127, in_point * 127)))
        out_val = int(max(0, min(127, out_point * 127)))

        self.send_cc(0, in_cc, in_val)
        self.send_cc(0, out_cc, out_val)
        return True

    def send_filter(self, deck, value):
        """Send filter knob value (0.0 - 1.0, 0.5 = center)."""
        cc = CC_NUMBERS.get(f"filter_{deck.lower()}", 16)
        midi_val = int(value * 127)
        return self.send_cc(0, cc, midi_val)

    # ============================================================
    # RECEIVE
    # ============================================================

    def start_listening(self):
        """Start listening for MIDI input in a background thread."""
        if self._listening:
            return

        if not self._input_port:
            print("MIDI: No input port connected")
            return

        self._listening = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        print("MIDI: Listening for input...")

    def stop_listening(self):
        """Stop listening for MIDI input."""
        self._listening = False

    def _listen_loop(self):
        """Background loop for MIDI input."""
        while self._listening and self._input_port:
            try:
                msg = self._input_port.receive(timeout=0.1)
                self._handle_message(msg)
            except Exception:
                continue

    def _handle_message(self, msg):
        """Handle incoming MIDI message."""
        if msg.type == "control_change":
            cc_name = None
            for name, cc_num in CC_NUMBERS.items():
                if cc_num == msg.control:
                    cc_name = name
                    break

            if cc_name:
                value = msg.value / 127.0
                self._dispatch("cc", cc_name, value)

        elif msg.type == "note_on" and msg.velocity > 0:
            self._dispatch("note_on", msg.note, msg.velocity)

        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            self._dispatch("note_off", msg.note, 0)

    def on(self, event_type, callback):
        """Register a callback for MIDI events.

        event_type: 'cc', 'note_on', 'note_off'
        callback: function(name_or_note, value)
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def _dispatch(self, event_type, *args):
        """Dispatch event to registered callbacks."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception:
                pass

    # ============================================================
    # DEVICE MAPPING PROFILES
    # ============================================================

    def load_mapping(self, device_name):
        """Load a controller mapping profile."""
        profiles = {
            "DDJ-400": {"input": "DDJ-400", "output": "DDJ-400"},
            "DDJ-1000": {"input": "DDJ-1000", "output": "DDJ-1000"},
            "XDJ-XZ": {"input": "XDJ-XZ", "output": "XDJ-XZ"},
        }

        profile = profiles.get(device_name)
        if profile:
            self.input_port_name = profile["input"]
            self.output_port_name = profile["output"]
            return True
        return False

    def list_devices(self):
        """List available MIDI devices."""
        if not HAS_MIDO:
            return []

        try:
            return mido.get_input_names()
        except Exception:
            return []

    def get_state(self):
        """Get current bridge state."""
        return {
            "connected": self._input_port is not None or self._output_port is not None,
            "listening": self._listening,
            "input_port": self.input_port_name,
            "output_port": self.output_port_name,
            "device_count": len(self.list_devices()),
        }
