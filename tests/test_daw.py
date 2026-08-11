"""
Headless tests for the DAW project model + engine.
"""

import os
import tempfile

import numpy as np

from app.ai.daw_project import DAWProject
from app.ai.daw_engine import DAWEngine, bpm_to_bar_seconds


def make_project():
    proj = DAWProject(bpm=126)
    kick = proj.add_track("kick", "kick_tech",
                          pattern=[1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
    bass = proj.add_track("bass", "bass_roll",
                          pattern=[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0])
    bass.note_root = 36
    lead = proj.add_track("lead", "arp_pluck")
    lead.add_note(60, 0.0, 0.5)
    lead.add_note(64, 1.0, 0.5)
    proj.add_block("pattern", "kick", 0, 4)
    proj.add_block("pattern", "bass", 0, 4)
    proj.add_block("midi", "lead", 2, 2)
    return proj


def test_project_model():
    proj = make_project()
    assert proj.bpm == 126
    assert len(proj.tracks) == 3
    assert proj.arrangement_length() == 4.0
    assert proj.get_track("bass").note_root == 36


def test_blocks_in_range():
    proj = make_project()
    in_bar0 = proj.blocks_in_range(0, 1)
    assert {b["track"] for b in in_bar0} == {"kick", "bass"}
    # kick/bass blocks span bars 0-4, so they overlap bar 2 too
    in_bar2 = proj.blocks_in_range(2, 3)
    assert {b["track"] for b in in_bar2} == {"kick", "bass", "lead"}


def test_engine_renders_bars():
    eng = DAWEngine(make_project())
    bar = eng.render_bar(0)
    assert bar.shape == (2, eng._bar_samples())
    assert bar.dtype == np.float32
    assert np.isfinite(bar).all()
    assert np.max(np.abs(bar)) > 0


def test_engine_stems():
    eng = DAWEngine(make_project())
    mix, stems = eng.render_bar(0, stems=True)
    assert "kick" in stems and "bass" in stems
    assert np.max(np.abs(stems["lead"])) == 0  # lead block starts at bar 2
    mix2, stems2 = eng.render_bar(2, stems=True)
    assert np.max(np.abs(stems2["lead"])) > 0


def test_muted_track_silent():
    proj = make_project()
    proj.get_track("kick").muted = True
    eng = DAWEngine(proj)
    _, stems = eng.render_bar(0, stems=True)
    assert np.max(np.abs(stems["kick"])) == 0
    assert np.max(np.abs(stems["bass"])) > 0


def test_project_roundtrip():
    proj = make_project()
    proj.name = "rt"
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "rt.json")
        proj.save(path)
        loaded = DAWProject().load(path)
    assert loaded.name == "rt"
    assert [t.name for t in loaded.tracks] == ["kick", "bass", "lead"]
    assert loaded.get_track("lead").notes[0]["pitch"] == 60
    assert len(loaded.blocks) == 3


def test_bpm_to_bar_seconds():
    assert abs(bpm_to_bar_seconds(120) - 2.0) < 1e-6
    assert abs(bpm_to_bar_seconds(126, 4) - 240.0 / 126) < 1e-6


def test_export_wav():
    eng = DAWEngine(make_project())
    with tempfile.TemporaryDirectory() as tmp:
        res = eng.export_wav(os.path.join(tmp, "mix.wav"),
                             bars=2, stems_dir=os.path.join(tmp, "stems"))
        assert os.path.getsize(res["mix"]) > 1000
        assert set(res["stems"].keys()) >= {"kick", "bass"}
        for sp in res["stems"].values():
            assert os.path.getsize(sp) > 1000
