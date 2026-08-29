"""
DJ AI OS — DAW Project Model

A DAW-style project for Beat Studio: tracks with step patterns AND piano-roll
note clips, an arrangement timeline of blocks, and a mixer bus. Everything
is plain JSON so projects save/load/share like DAW project files.

    project = DAWProject(bpm=128)
    tr = project.add_track("bass", instrument="bass_roll", pattern=[1,1,0,1,...])
    tr.add_note(pitch=36, start=0.0, dur=0.5, vel=0.9)
    project.add_block("pattern", "bass", start=0, length=4)   # bars
    project.add_block("midi", "lead", start=4, length=4)
    project.save("DJ_EXPORTS/projects/my_song.json")
"""

import json
import os

from app.core.paths import get_exports_dir

# Default 16-step on/off (kick pattern) used by new tracks
DEFAULT_PATTERN = [1, 0, 0, 0] * 4


class DAWTrack:
    """One track: instrument + pattern + piano-roll notes + mixer strip."""

    def __init__(self, name, instrument="bass_roll", pattern=None):
        self.name = name
        self.instrument = instrument
        self.steps = list(pattern) if pattern else list(DEFAULT_PATTERN)
        self.velocities = [1.0] * len(self.steps)
        self.notes = []            # [{pitch,start,dur,vel}]
        self.note_root = 36        # C2 — pitch for pattern hits
        self.note_octave = 1
        self.volume = 0.9
        self.pan = 0.0             # -1..1
        self.eq = {"hi": 0.0, "mid": 0.0, "low": 0.0}
        self.muted = False
        self.solo = False
        self.color = "#E63946"

    def add_note(self, pitch, start, dur, vel=0.9):
        self.notes.append({"pitch": int(pitch), "start": float(start),
                           "dur": float(dur), "vel": float(vel)})
        self.notes.sort(key=lambda n: n["start"])

    def set_pattern(self, steps):
        self.steps = [int(bool(s)) for s in steps]
        self.velocities = self.velocities[:len(self.steps)]
        while len(self.velocities) < len(self.steps):
            self.velocities.append(1.0)

    def to_dict(self):
        return {
            "name": self.name, "instrument": self.instrument,
            "steps": self.steps, "velocities": self.velocities,
            "notes": self.notes, "volume": self.volume, "pan": self.pan,
            "eq": self.eq, "muted": self.muted, "solo": self.solo,
            "color": self.color, "note_root": self.note_root,
            "note_octave": self.note_octave,
        }

    @classmethod
    def from_dict(cls, d):
        tr = cls(d.get("name", "track"), d.get("instrument", "bass_roll"),
                 d.get("steps"))
        tr.velocities = list(d.get("velocities", [1.0] * len(tr.steps)))
        tr.notes = list(d.get("notes", []))
        tr.volume = float(d.get("volume", 0.9))
        tr.pan = float(d.get("pan", 0.0))
        tr.eq = dict(d.get("eq", {"hi": 0.0, "mid": 0.0, "low": 0.0}))
        tr.muted = bool(d.get("muted", False))
        tr.solo = bool(d.get("solo", False))
        tr.color = d.get("color", "#E63946")
        tr.note_root = int(d.get("note_root", 36))
        tr.note_octave = int(d.get("note_octave", 1))
        return tr


class DAWProject:
    """A full DAW project."""

    def __init__(self, bpm=128, signature=(4, 4)):
        self.bpm = bpm
        self.signature = list(signature)
        self.tracks = []           # list[DAWTrack]
        self.blocks = []           # [{type:'pattern'|'midi', track, start, length}]
        self.master = {"volume": 0.9, "limiter": True}
        self.name = "untitled"

    # ---- tracks ----
    def add_track(self, name, instrument="bass_roll", pattern=None):
        tr = DAWTrack(name, instrument, pattern)
        self.tracks.append(tr)
        return tr

    def get_track(self, name):
        for tr in self.tracks:
            if tr.name == name:
                return tr
        return None

    def remove_track(self, name):
        self.tracks = [t for t in self.tracks if t.name != name]
        self.blocks = [b for b in self.blocks if b["track"] != name]

    def ensure_steps(self, steps):
        """Extend all tracks to `steps` long."""
        for tr in self.tracks:
            if len(tr.steps) < steps:
                tr.steps += [0] * (steps - len(tr.steps))
                tr.velocities += [1.0] * (steps - len(tr.velocities))

    # ---- arrangement ----
    def add_block(self, btype, track, start=0, length=4):
        blk = {"type": btype, "track": track, "start": float(start),
               "length": float(length)}
        self.blocks.append(blk)
        self.blocks.sort(key=lambda b: b["start"])
        return blk

    def blocks_in_range(self, start, end):
        """Blocks overlapping [start, end) in bars."""
        return [b for b in self.blocks
                if b["start"] < end and b["start"] + b["length"] > start]

    def arrangement_length(self):
        if not self.blocks:
            return 4
        return max(b["start"] + b["length"] for b in self.blocks)

    # ---- serialization ----
    def to_dict(self):
        return {
            "name": self.name, "bpm": self.bpm,
            "signature": self.signature,
            "tracks": [t.to_dict() for t in self.tracks],
            "blocks": self.blocks, "master": self.master,
        }

    def from_dict(self, d):
        self.name = d.get("name", "untitled")
        self.bpm = float(d.get("bpm", 128))
        self.signature = list(d.get("signature", [4, 4]))
        self.tracks = [DAWTrack.from_dict(t) for t in d.get("tracks", [])]
        self.blocks = list(d.get("blocks", []))
        self.master = dict(d.get("master", {"volume": 0.9, "limiter": True}))
        return self

    def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)
        return path

    def load(self, path):
        with open(path, "r", encoding="utf-8") as fh:
            return self.from_dict(json.load(fh))

    # ---- export summary ----
    def summary(self):
        return {
            "name": self.name, "bpm": self.bpm,
            "tracks": [t.name for t in self.tracks],
            "blocks": len(self.blocks),
            "length_bars": self.arrangement_length(),
        }
