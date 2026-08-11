"""
Headless tests for the Serum-style patch synth. No audio device needed.
"""

import os
import tempfile
import time

import numpy as np
from numpy.fft import rfft

from app.ai.instruments.synth_patch import (
    render_patch, svf_filter, env_adsr, PATCH_PRESETS, normalize_patch,
    save_patch, load_patch, list_patches,
)
from app.ai.instruments import get_instrument, list_instruments
from app.ai.live_performance import LivePerformanceEngine


def test_all_presets_render_clean():
    for name, patch in PATCH_PRESETS.items():
        sig = render_patch(patch, 55.0, 0.5)
        assert sig.dtype == np.float32
        assert np.isfinite(sig).all()
        assert np.max(np.abs(sig)) <= 1.0
        assert len(sig) == int(0.5 * 44100), name


def test_bass_dominant_at_fundamental():
    sig = render_patch(PATCH_PRESETS["acid_bass"], 55.0, 0.5)
    mag = np.abs(rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1 / 44100)
    dom = freqs[np.argmax(mag)]
    assert 40 <= dom <= 90, f"dominant {dom:.0f}Hz expected ~55Hz"


def test_resonance_boosts_near_cutoff():
    from app.ai.instruments import synth_core as sc
    t = np.arange(0.4 * 44100) / 44100
    saw = sc._oscillator("saw", 220, len(t), 44100)
    a = np.max(np.abs(rfft(svf_filter(saw, 220, 0.0, "lp"))))
    b = np.max(np.abs(rfft(svf_filter(saw, 220, 0.9, "lp"))))
    assert b / (a + 1e-9) > 2.0, "resonance should boost peak near cutoff"


def test_adsr_shape():
    env = env_adsr(0.6 * 44100, 44100, a=0.1, d=0.2, s=0.5, r=0.2)
    assert abs(env.max() - 1.0) < 0.01
    mid = env[int(0.25 * 44100)]
    assert 0.3 < mid < 0.7, "sustain level should be ~0.5"
    assert env[-1] < 0.05, "release should decay toward 0"


def test_registry():
    assert "synth_patch" in list_instruments()
    pl = get_instrument("synth_patch")
    s = pl.hit(note=36)
    assert s.dtype == np.float32 and len(s) > 0


def test_cache_speed():
    pl = get_instrument("synth_patch")
    pl.set_patch(PATCH_PRESETS["pluck_lead"])
    pl.hit(note=48)  # warm
    t0 = time.time()
    pl.hit(note=48)
    t1 = time.time()
    assert (t1 - t0) < 0.005, f"cached hit too slow: {t1-t0:.4f}s"


def test_engine_integration():
    eng = LivePerformanceEngine(bpm=126)
    eng.add_channel("kick_tech", [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    eng.add_channel("synth_patch", [1, 0, 0, 1] * 4, note_root=36)
    eng.channels["synth_patch"].inst.set_patch(PATCH_PRESETS["growl_bass"])
    bar, stems = eng.render_bar()
    assert np.isfinite(bar).all()
    assert np.max(np.abs(bar)) > 0
    assert "synth_patch" in stems


def test_save_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        p = normalize_patch(PATCH_PRESETS["acid_bass"])
        p["name"] = "rt"
        path = save_patch(p, "rt", out_dir=tmp)
        assert os.path.exists(path)
        loaded = load_patch("rt", out_dir=tmp)
        assert loaded["osc1"]["wave"] == p["osc1"]["wave"]
        assert loaded["filter"]["cutoff"] == p["filter"]["cutoff"]
        assert loaded["drive"] == p["drive"]
        assert "rt" in list_patches(out_dir=tmp)


def test_set_patch_live_params():
    pl = get_instrument("synth_patch")
    pl.set_patch(PATCH_PRESETS["tech_kick"])
    assert pl.get_params()["pitch_amt"] > 0, "tech_kick should pitch up"
    pl.set_param("filter_cutoff", 4000)
    assert pl.get_params()["filter_cutoff"] == 4000
    patch = pl.get_patch()
    assert patch["filter"]["cutoff"] == 4000
