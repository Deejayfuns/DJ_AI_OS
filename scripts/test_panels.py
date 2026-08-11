"""Dev tool: construct the AI panels in a hidden widget tree (smoke test).

Run from repo root:
    python scripts/test_panels.py

Verifies NeuralSynthPanel, NeuralBridgePanel and PioneerLinkPanel all
build without crashing, then drives the PioneerLinkPanel's HardwareCoach
with synthetic hardware events (real MIDI loopback is unavailable on
this Windows machine — see memory: midi-hardware-env).
"""

import sys
import os
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = tk.Tk()
ROOT.withdraw()


class StubWin:
    """Minimal stand-in for MainWindow: what the panels touch at build."""
    library = []
    current_set = []
    saved_tracks = []
    daw_panel = None

    def log(self, *a, **k):
        pass


def test_neural_synth():
    # subclass skips the VAE warm thread so the test stays fast/deterministic
    import app.ui.neural_synth_panel as m

    class Quiet(m.NeuralSynthPanel):
        def _warm_vae(self):
            pass

    p = Quiet(ROOT, win=StubWin())
    assert p.plugin is not None
    p.on_close()
    print("  NeuralSynthPanel    OK")


def test_neural_bridge():
    import app.ui.neural_bridge_panel as m
    p = m.NeuralBridgePanel(ROOT, win=StubWin())
    assert p is not None
    print("  NeuralBridgePanel   OK")


def test_pioneer_link():
    import app.ui.pioneer_link_panel as m
    p = m.PioneerLinkPanel(ROOT, win=StubWin())

    # coach section must exist and have its labels
    for attr in ("coach_sum_lbl", "coach_sug_lbl", "coach_set_lbl"):
        assert getattr(p, attr, None) is not None, f"missing {attr}"
    assert p.coach is not None

    # synthetic hardware events feed the coach (as _on_hardware_event does)
    p.coach.feed({"type": "filter", "deck": "A", "value": 0.8})
    p.coach.feed({"type": "jog", "deck": "B", "delta": -8})
    p.coach.feed({"type": "crossfader", "deck": "mixer", "value": 0.72})
    line, deck = p.coach.summary()
    sugs = p.coach.suggest(set_tracks=[])
    assert sugs, "coach returned no suggestions"
    print(f"  summary: {line} | deck: {deck}")
    print(f"  top: {sugs[0][0]} [{sugs[0][1]:.0%}]")

    # one tick must refresh the labels without raising
    p._coach_job = None
    p._coach_tick()
    ROOT.update()
    p.on_close()
    print("  PioneerLinkPanel    OK")


if __name__ == "__main__":
    test_neural_synth()
    test_neural_bridge()
    test_pioneer_link()
    ROOT.destroy()
    print("\nALL PANELS OK")
