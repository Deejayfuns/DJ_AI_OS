"""
Headless tests for the HID engine + four-deck engine. No hardware needed.
"""

import time

from app.ai.hid_engine import PioneerReportParser, discover_devices
from app.ai.four_deck_engine import FourDeckEngine


def test_discover_returns_list():
    assert isinstance(discover_devices(), list)


def test_parser_jog():
    p = PioneerReportParser()
    evts = p.parse(bytes([1, 10, 0, 251, 255, 64, 96, 80, 100, 60]))
    jogs = [e for e in evts if e["type"] == "jog"]
    assert len(jogs) == 2
    assert jogs[0]["deck"] == "A" and jogs[0]["delta"] == 10
    assert jogs[1]["deck"] == "B" and jogs[1]["delta"] == -5


def test_parser_tempo_fader_cross():
    p = PioneerReportParser()
    evts = p.parse(bytes([1, 0, 0, 0, 0, 64, 96, 80, 100, 60]))
    tempos = {e["deck"]: e["value"] for e in evts if e["type"] == "tempo"}
    assert abs(tempos["A"] - 64 / 127) < 0.001
    assert abs(tempos["B"] - 96 / 127) < 0.001
    cross = [e for e in evts if e["type"] == "crossfader"]
    assert cross and abs(cross[0]["value"] - 60 / 127) < 0.001


def test_parser_buttons():
    p = PioneerReportParser()
    evts = p.parse(bytes([2, 0x01, 0x00]))
    assert any(e["type"] == "button" and e["control"] == "play" for e in evts)


def test_parser_pads():
    p = PioneerReportParser()
    evts = p.parse(bytes([3, 0x09, 0x00]))  # pad 0 + pad 3
    pads = [e for e in evts if e["type"] == "pad"]
    assert {e["pad"] for e in pads} == {0, 3}


def test_parser_layer():
    p = PioneerReportParser()
    evts = p.parse(bytes([10, 0x80, 0x01]))
    assert any(e["type"] == "layer" for e in evts)


def test_four_deck_creation():
    eng = FourDeckEngine(use_vlc=False)
    assert list(eng.decks.keys()) == ["A", "B", "C", "D"]
    assert eng.active_pair == ("A", "B")


def test_layer_mapping():
    eng = FourDeckEngine(use_vlc=False)
    eng.toggle_layer()
    assert eng.active_pair == ("C", "D")
    eng.fader("A", 1.0)
    assert eng.decks["C"].volume == 1.0
    eng.toggle_layer()
    eng.fader("A", 0.5)
    assert eng.decks["A"].volume == 0.5


def test_crossfade_routes_active_pair():
    eng = FourDeckEngine(use_vlc=False)
    eng.toggle_layer()
    eng.crossfade(0.0)
    assert eng.decks["C"].volume > 0 and eng.decks["D"].volume == 0
    eng.crossfade(1.0)
    assert eng.decks["D"].volume > 0 and eng.decks["C"].volume == 0


def test_deck_transport_simulated():
    eng = FourDeckEngine(use_vlc=False)
    d = eng.decks["A"]
    d.load({"path": "x.mp3", "length": 300})
    d.play()
    time.sleep(0.15)
    assert d.playing
    assert d.position > 0
    d.set_hot_cue(0)
    d.seek(50)
    d.trigger_hot_cue(0)
    assert d.position < 5, f"should jump back to cue, got {d.position}"


def test_hid_event_dispatch():
    eng = FourDeckEngine(use_vlc=False)
    eng.decks["A"].load({"path": "x.mp3", "length": 300})
    eng.decks["A"].play()
    eng.handle_hid_event({"type": "button", "deck": "A", "control": "play", "pressed": True})
    assert eng.decks["A"].paused  # toggled to pause
