"""
DJ AI OS — Pioneer Link
=======================
The professional layer between DJ AI OS and Pioneer hardware
(CDJ / XDJ-RR / DJM / DDJ) plus Rekordbox.

What it does:
  • PORT DISCOVERY  — find every MIDI in/out (real Pioneer gear + virtual).
  • TRANSPORT       — PLAY/PAUSE/CUE/SYNC to any deck, using the live-
                      calibrated XDJ-RR mapping from xdj_rr_midi.
  • MIDI CLOCK      — 24 ppqn master clock at your BPM (F8 + FA/FB/FC) so
                      the whole booth — CDJs, FX units, drum machines —
                      locks to DJ AI OS.
  • MIDI LEARN      — arm a target, touch a knob/button on the hardware,
                      and that control now drives a software FX param live.
  • REKORDBOX SYNC  — parse a Rekordbox XML, match it to the AI OS library,
                      light hot-cue pads on the hardware.

Graceful degradation: no mido, no ports? Every method is a safe no-op, so
the panel still works as a pure software FX studio.
"""

import os
import time
import threading

from app.ai.xdj_rr_midi import CHANNEL_TO_DECK, translate

try:
    import mido
    HAS_MIDO = True
except ImportError:
    mido = None
    HAS_MIDO = False

# XDJ-RR note map (live-calibrated): NOTE -> action on deck channels
XDJ_NOTES = {0: "play", 32: "cue", 81: "sync"}
DECK_CHANNEL = {"A": 0, "B": 1, "C": 2, "D": 3}


def list_ports():
    """Return {"inputs": [...], "outputs": [...]}."""
    if not HAS_MIDO:
        return {"inputs": [], "outputs": []}
    try:
        return {"inputs": mido.get_input_names(),
                "outputs": mido.get_output_names()}
    except Exception:
        return {"inputs": [], "outputs": []}


class MIDIClock:
    """24ppqn master clock. Sends start(F8/F8+FA), ticks(F8), stop(FC)."""

    PPQN = 24

    def __init__(self, port=None, bpm=128):
        self._port = port
        self._bpm = float(bpm)
        self._running = False
        self._thread = None

    def set_bpm(self, bpm):
        self._bpm = float(bpm)

    @property
    def running(self):
        return self._running

    def start(self):
        if not HAS_MIDO or self._port is None or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if HAS_MIDO and self._port is not None:
            try:
                self._port.send(mido.Message("stop"))  # FC
            except Exception:
                pass

    def _loop(self):
        try:
            self._port.send(mido.Message("start"))  # FA
        except Exception:
            pass
        interval = 60.0 / self._bpm / self.PPQN
        while self._running:
            t0 = time.time()
            try:
                self._port.send(mido.Message("clock"))  # F8
            except Exception:
                break
            elapsed = time.time() - t0
            # live bpm updates: recompute interval each tick
            interval = 60.0 / self._bpm / self.PPQN
            if elapsed < interval:
                time.sleep(interval - elapsed)


class PioneerLink:
    """Transport + learn + Rekordbox bridge to Pioneer hardware."""

    def __init__(self, in_port=None, out_port=None):
        self._in_name = in_port
        self._out_name = out_port
        self._in = None
        self._out = None
        self._listening = False
        self._listen_thread = None
        self._clock = None
        self._bindings = {}       # (channel, cc|note) -> (slot, param)
        self._armed = None        # target being learned, or None
        self._on_binding = None   # callback(slot, param, value01)
        self._on_event = None     # callback(event_dict)

    # ============================================================
    # PORTS
    # ============================================================
    def connect(self, in_port=None, out_port=None):
        if not HAS_MIDO:
            return False
        if in_port:
            self._in_name = in_port
        if out_port:
            self._out_name = out_port
        try:
            if self._out_name:
                self._out = mido.open_output(self._out_name)
            if self._in_name:
                self._in = mido.open_input(self._in_name)
            self._clock = MIDIClock(self._out)
            self.start_listening()
            return True
        except Exception:
            return False

    def disconnect(self):
        self.stop_clock()
        self._listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=2)
            self._listen_thread = None
        for p in (self._in, self._out):
            if p is not None:
                try:
                    p.close()
                except Exception:
                    pass
        self._in = self._out = None

    @property
    def connected(self):
        return self._in is not None or self._out is not None

    # ============================================================
    # TRANSPORT  (momentary button press -> note_on + delayed note_off)
    # ============================================================
    def _send_note(self, channel, note, vel=127):
        if not HAS_MIDO or self._out is None:
            return False
        try:
            self._out.send(mido.Message("note_on", channel=channel,
                                        note=note, velocity=vel))
            threading.Timer(0.06,
                            lambda: self._note_off(channel, note)).start()
            return True
        except Exception:
            return False

    def _note_off(self, channel, note):
        if HAS_MIDO and self._out is not None:
            try:
                self._out.send(mido.Message("note_off", channel=channel,
                                            note=note, velocity=0))
            except Exception:
                pass

    def play(self, deck="A"):
        return self._send_note(DECK_CHANNEL.get(deck, 0), 0)

    def cue(self, deck="A"):
        return self._send_note(DECK_CHANNEL.get(deck, 0), 32)

    def sync(self, deck="A"):
        return self._send_note(DECK_CHANNEL.get(deck, 0), 81)

    def set_tempo(self, bpm, deck="A"):
        """BPM -> tempo fader CC (60-200 BPM across 0-127)."""
        if not HAS_MIDO or self._out is None:
            return False
        ch = DECK_CHANNEL.get(deck, 0)
        val = int(np_clip((bpm - 60) / 140.0 * 127, 0, 127))
        try:
            self._out.send(mido.Message("control_change", channel=ch,
                                        control=33, value=val))
            return True
        except Exception:
            return False

    # ============================================================
    # MIDI CLOCK
    # ============================================================
    def start_clock(self, bpm=128):
        if self._clock is not None:
            self._clock.set_bpm(bpm)
            self._clock.start()

    def stop_clock(self):
        if self._clock is not None:
            self._clock.stop()

    @property
    def clock_running(self):
        return bool(self._clock and self._clock.running)

    # ============================================================
    # MIDI LEARN
    # ============================================================
    def arm_learn(self, slot, param):
        """Arm learning: the next CC/note from the hardware binds to
        (slot, param)."""
        self._armed = (slot, param)

    def cancel_learn(self):
        self._armed = None

    def clear_binding(self, slot, param):
        for k in [k for k, v in self._bindings.items() if v == (slot, param)]:
            del self._bindings[k]

    def bindings(self):
        return {f"{k[0]}cc{k[1]}": v for k, v in self._bindings.items()}

    # ============================================================
    # LISTEN
    # ============================================================
    def start_listening(self):
        if self._listening or self._in is None:
            return
        self._listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop,
                                               daemon=True)
        self._listen_thread.start()

    def stop_listening(self):
        self._listening = False

    def _listen_loop(self):
        while self._listening and self._in is not None:
            try:
                msg = self._in.receive(timeout=0.05)
            except Exception:
                continue
            if msg is None:
                continue
            self._handle(msg)

    def _handle(self, msg):
        ev = translate(msg)
        if ev is not None and self._on_event:
            try:
                self._on_event(ev)
            except Exception:
                pass

        if msg.type == "control_change":
            key = (msg.channel, msg.control)
            val01 = msg.value / 127.0
            self._route_control(key, val01)
        elif msg.type == "note_on" and msg.velocity > 0:
            key = (msg.channel, msg.note + 1000)
            self._route_control(key, 1.0)

    def _route_control(self, key, value):
        if self._armed is not None:
            self._bindings[key] = self._armed
            self._armed = None
            if self._on_binding:
                try:
                    self._on_binding(key, value)
                except Exception:
                    pass
            return
        target = self._bindings.get(key)
        if target and self._on_binding:
            try:
                self._on_binding(target, value)
            except Exception:
                pass

    # ============================================================
    # REKORDBOX SYNC
    # ============================================================
    def load_rekordbox_xml(self, xml_path):
        """Parse a Rekordbox XML export -> (tracks, playlists)."""
        from app.core.rekordbox_import import RekordboxImporter
        imp = RekordboxImporter()
        return imp.parse(xml_path)

    def light_hot_cue(self, deck, number, color="GREEN"):
        """Light a hot-cue pad on the hardware."""
        if not HAS_MIDO or self._out is None:
            return False
        notes = {"A": [60, 61, 62, 63], "B": [72, 73, 74, 75],
                 "C": [84, 85, 86, 87], "D": [96, 97, 98, 99]}
        colors = {"OFF": 0, "RED": 1, "GREEN": 2, "YELLOW": 3, "BLUE": 4,
                  "PURPLE": 5, "CYAN": 6, "WHITE": 7}
        ns = notes.get(deck.upper(), notes["A"])
        if not (1 <= number <= len(ns)):
            return False
        try:
            self._out.send(mido.Message(
                "note_on", channel=DECK_CHANNEL.get(deck.upper(), 0),
                note=ns[number - 1],
                velocity=colors.get(color.upper(), colors["GREEN"])))
            return True
        except Exception:
            return False


def np_clip(v, lo, hi):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------
# FX presets — the "one button" DJ moves
# ---------------------------------------------------------------------

FX_PRESETS = {
    "CLEAN":     [],
    "ECHO DROP": [("filter", {"cutoff_hz": 3000.0, "lfo_rate": 0.15,
                              "lfo_depth": 0.6, "wet": 0.6}),
                  ("echo", {"time_s": 0.25, "feedback": 0.55, "wet": 0.5})],
    "FILTER SWEEP": [("filter", {"cutoff_hz": 5000.0, "lfo_rate": 0.5,
                                 "lfo_depth": 0.8, "resonance": 1.2,
                                 "wet": 1.0})],
    "GATE STAB": [("gate", {"step": "16", "hold": 0.5, "wet": 1.0}),
                  ("filter", {"cutoff_hz": 9000.0, "lfo_rate": 0.0,
                              "wet": 0.5})],
    "REVERB WASH": [("reverb", {"wet": 0.7, "decay": 0.6})],
    "BEAT MASH": [("gate", {"step": "16", "hold": 0.35, "repeat": True,
                            "wet": 1.0}),
                  ("echo", {"time_s": 0.125, "feedback": 0.5, "wet": 0.4})],
    "DESTROY": [("bitcrush", {"bits": 6, "downsample": 3, "wet": 0.7}),
                ("dist", {"drive": 3.0, "wet": 0.6}),
                ("flanger", {"rate_hz": 0.4, "depth_ms": 5.0, "wet": 0.5})],
    "PHATT": [("dist", {"drive": 2.5, "wet": 0.6}),
              ("filter", {"cutoff_hz": 6000.0, "lfo_rate": 0.0, "wet": 0.4})],
}


def preset_chain(name):
    """Turn a preset name into a rack-ready slot list."""
    return [list(spec) for spec in FX_PRESETS.get(name, [])]
