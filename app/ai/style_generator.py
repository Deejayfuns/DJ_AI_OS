"""
DJ AI OS — Style Generator

The brain that listens to a track and writes a NEW beat pattern from
scratch to match it. Drop any song -> analyze -> this generates a
LivePerformanceEngine config that sounds like a fresh take on that
track's vibe.

Mapping logic:
  BPM            -> engine tempo
  key            -> melodic root note + scale
  energy         -> pattern density (how many hits per bar)
  danceability   -> swing + kick style (4-to-floor vs syncopated)
  brightness     -> instrument palette (dark sub vs bright hats/pluck)
  roughness      -> bass drive (soft sine vs distorted saw)
  vocal_risk     -> lean rhythmic vs melodic space
  mood           -> genre hints
"""

import numpy as np

from .music_intelligence import MusicIntelligence
from .live_performance import LivePerformanceEngine, SCALES

# genre keywords -> melodic techno hint (matched in _build_channels)
MELODIC_TECH_KEYWORDS = (
    "melodic", "tech", "techno", "progressive", "melodic techno",
    "prog", "afterlife", "tale of us", "innellea", "kevin de vries",
    "mind against", "adam port", "spinnin", "diynamic",
)
# mood labels that map to the melodic techno kit
MELODIC_TECH_MOODS = {"epic", "dark", "tense", "nervous", "sad_moody", "dreamy"}

# key name -> MIDI root (C4 = 60)
KEY_MIDI = {
    "C": 60, "C#": 61, "D": 62, "D#": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "G#": 68, "A": 57, "A#": 58, "B": 59,
    "Bb": 58, "Db": 61, "Eb": 63, "Gb": 66, "Ab": 68,
}

# mood -> preferred scale
MOOD_SCALE = {
    "dark": "phrygian",
    "tense": "dorian",
    "aggressive": "phrygian",
    "calm": "aeolian",
    "happy": "major",
    "energetic": "major",
    "chill": "aeolian",
    "sad": "harmonic",
    "dreamy": "major",
    "epic": "harmonic",
    "nervous": "dorian",
    "sad_moody": "harmonic",
}


class StyleGenerator:
    """Turn audio analysis into a brand-new beat style."""

    def __init__(self, sample_rate=44100):
        self.sr = sample_rate
        self.analyzer = MusicIntelligence()
        self.last_analysis = None
        self.last_engine = None

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze_file(self, path: str) -> dict:
        """Analyze an audio file -> feature dict."""
        analysis = self.analyzer.analyze_file(path)
        if analysis.get("error"):
            raise RuntimeError(analysis["error"])
        self.last_analysis = analysis
        return analysis

    def generate(self, analysis: dict) -> dict:
        """
        Generate a style config from an analysis dict.
        Returns {bpm, swing, key_root, scale, mood, channels:{...}}.
        """
        a = analysis or {}
        bpm = self._clamp_bpm(float(a.get("bpm") or 128))
        energy = float(a.get("energy") or 0.5)
        brightness = float(a.get("brightness") or 0.5)
        danceability = float(a.get("danceability") or 0.5)
        roughness = float(a.get("roughness") or 0.3)
        vocal_risk = float(a.get("vocal_risk") or 0.2)
        mood = a.get("mood", "chill")
        key_name = a.get("key", "C")

        # ---- key -> root + scale ----
        scale = MOOD_SCALE.get(str(mood).lower(), "aeolian")
        root = self._key_root(key_name, scale)
        bass_root = self._bass_root(root)

        # ---- swing from danceability ----
        # groovy tracks swing more; straight 4-to-floor swings less
        if danceability > 0.75:
            swing = 0.0 if bpm >= 118 else 0.25   # danceable fast = straight
        elif danceability > 0.45:
            swing = 0.08 if bpm >= 118 else 0.3   # mid = some groove
        else:
            swing = 0.35                           # head-nod, heavy swing

        # ---- pattern density from energy ----
        density = self._density(energy)

        # ---- MELODIC TECHNO detection ----
        # If the track's mood or source hints at melodic techno, use the kit.
        mt = self._is_melodic_techno(a)
        if mt:
            # melodic techno: straight roll, minor/dark scale, no swing
            scale = "aeolian" if str(mood).lower() not in ("happy", "energetic") else "dorian"
            swing = 0.0
            channels = self._build_melodic_techno(
                bpm=bpm, energy=energy, brightness=brightness,
                vocal_risk=vocal_risk, bass_root=bass_root, density=density,
                root=root,
            )
        else:
            # ---- instrument palette from brightness ----
            channels = self._build_channels(
                bpm=bpm, energy=energy, brightness=brightness,
                roughness=roughness, vocal_risk=vocal_risk,
                bass_root=bass_root, density=density,
            )

        style = {
            "bpm": bpm,
            "swing": round(swing, 2),
            "key": key_name,
            "key_root": root,
            "bass_root": bass_root,
            "scale": scale,
            "kit": "melodic_techno" if mt else "standard",
            "energy": round(energy, 3),
            "brightness": round(brightness, 3),
            "danceability": round(danceability, 3),
            "mood": mood,
            "channels": channels,
        }
        self.last_style = style
        return style

    def build_engine(self, analysis: dict = None, style: dict = None) -> LivePerformanceEngine:
        """Build a playable engine from a style config."""
        if style is None:
            style = self.generate(analysis or self.last_analysis)
        engine = LivePerformanceEngine(bpm=style["bpm"], swing=style["swing"], sample_rate=self.sr)
        for name, cfg in style["channels"].items():
            ch = engine.add_channel(name, pattern=cfg["pattern"])
            if "level" in cfg:
                ch.level = cfg["level"]
            if "note_root" in cfg:
                ch.note_root = cfg["note_root"]
            for pkey, pval in cfg.get("params", {}).items():
                ch.set_param(pkey, pval)
        self.last_engine = engine
        return engine

    def style_from_file(self, path: str) -> dict:
        """One-shot: analyze file + generate style."""
        analysis = self.analyze_file(path)
        style = self.generate(analysis)
        style["_source"] = path
        return style

    # ============================================================
    # FEATURE MAPPING
    # ============================================================

    def _clamp_bpm(self, bpm):
        return int(max(60, min(180, bpm)))

    def _key_root(self, key_name, scale):
        """Map key name to a MIDI root for the given scale mode."""
        base = key_name
        minor = base.endswith("m")
        if minor:
            base = base[:-1]
        root = KEY_MIDI.get(base, 60)
        if minor and scale not in ("minor", "aeolian", "harmonic"):
            # keep the tonic stable even if we pick a different mode
            pass
        return root

    def _bass_root(self, root):
        """Push root into bass register (MIDI ~28-43, E1-G2)."""
        while root > 43:
            root -= 12
        while root < 28:
            root += 12
        return root

    def _density(self, energy):
        """Map energy 0-1 to a hit-density profile label."""
        if energy > 0.75:
            return "dense"
        if energy > 0.5:
            return "full"
        if energy > 0.3:
            return "mid"
        return "sparse"

    def _is_melodic_techno(self, analysis):
        """Heuristic: does this track feel like melodic techno?"""
        a = analysis or {}
        mood = str(a.get("mood", "")).lower()
        if mood in MELODIC_TECH_MOODS:
            return True
        # source path / title hints
        src = str(a.get("_source", "")).lower() + " " + str(a.get("title", "")).lower()
        if any(k in src for k in MELODIC_TECH_KEYWORDS):
            return True
        # dark + driving + moderate energy profile
        bpm = float(a.get("bpm") or 0)
        energy = float(a.get("energy") or 0.5)
        brightness = float(a.get("brightness") or 0.5)
        if 116 <= bpm <= 132 and energy > 0.55 and brightness < 0.6:
            return True
        return False

    def _build_melodic_techno(self, bpm, energy, brightness, vocal_risk,
                              bass_root, density, root):
        """
        The melodic techno kit: dark roll kick, rolling bass on 16ths,
        tech hats, metallic ticks, bright arp, wide pad, drone bed.
        """
        channels = {}

        # kick: 4-to-floor dark
        channels["kick_tech"] = {"pattern": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                                 "level": 1.0, "params": {"freq": 45, "decay": 0.55}}

        # rolling bass: 16ths, rooted on the track's key
        bass = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        channels["bass_roll"] = {"pattern": bass, "level": 0.95,
                                 "note_root": bass_root,
                                 "params": {"cutoff": 280 + energy * 200, "drive": 1.8}}

        # tech hats offbeat
        channels["hat_tech"] = {"pattern": [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
                                "level": 0.5, "params": {"bright": 0.7}}

        # metallic tick on the 4th 16th of each beat (perkyon glue)
        tick_pat = [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1]
        channels["tick"] = {"pattern": tick_pat, "level": 0.4, "params": {"freq": 2100}}

        # clap backbeat for energy
        if energy > 0.6:
            channels["clap_tech"] = {"pattern": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                                     "level": 0.8, "params": {"body": 0.4}}

        # arp pluck: repetitive melodic hook on the key
        arp_pat = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        channels["arp_pluck"] = {"pattern": arp_pat, "level": 0.55,
                                 "note_root": bass_root + 24,
                                 "params": {"bright": 0.9 + brightness * 0.6}}

        # wide pad — only when vocal space is open
        if vocal_risk < 0.6:
            channels["pad_tech"] = {"pattern": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                                    "level": 0.4,
                                    "note_root": bass_root + 24,
                                    "params": {"width": 7.0, "cutoff": 1000}}

        # drone bed for atmosphere
        channels["drone"] = {"pattern": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             "level": 0.25,
                             "note_root": bass_root,
                             "params": {"cutoff": 400}}

        return channels

    # ============================================================
    # CHANNEL GENERATION
    # ============================================================

    def _build_channels(self, bpm, energy, brightness, roughness,
                        vocal_risk, bass_root, density):
        channels = {}

        # ---------- KICK ----------
        # Danceable 4-to-floor for club BPMs, syncopated for slow
        if bpm >= 118:
            kick = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
            if energy > 0.85:  # heavy drop: double kick
                kick = [1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0]
        elif energy > 0.7:  # slow but energetic: half-time thump
            kick = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
        else:  # slow/chill: sparse
            kick = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]

        # dark + slow -> 808 (sub), bright/fast -> punchy kick
        if brightness < 0.4 and bpm < 118:
            channels["kick_808"] = {"pattern": kick, "level": 1.0,
                                    "params": {"freq": 50, "decay": 5.0}}
        else:
            punch = 1.5 + roughness * 2
            channels["kick"] = {"pattern": kick, "level": 1.0,
                                "params": {"punch": round(punch, 2)}}

        # ---------- SNARE / CLAP ----------
        # backbeat on 2 & 4 for most genres
        clap = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
        if density == "sparse":
            clap = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        if brightness < 0.35:
            channels["snare"] = {"pattern": clap, "level": 0.8,
                                 "params": {"tone": 160, "snappy": 0.7}}
        else:
            channels["clap"] = {"pattern": clap, "level": 0.85,
                                "params": {"bursts": 3, "bright": 1.0}}

        # ---------- HATS ----------
        # density drives hat pattern
        if density == "dense":
            hat = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
            if bpm >= 140:
                hat = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        elif density == "full":
            hat = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]
        elif density == "mid":
            hat = [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]
        else:
            hat = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]

        channels["hat"] = {"pattern": hat, "level": 0.6,
                           "params": {"bright": round(0.6 + brightness, 2)}}

        # open hat accents on 8th for brightness
        if brightness > 0.6 and density in ("full", "dense"):
            oh = [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
            channels["hat_open"] = {"pattern": oh, "level": 0.4}

        # shaker for bright + groovy tracks
        if brightness > 0.55:
            shk = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0] if density != "sparse" else \
                  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
            channels["shaker"] = {"pattern": shk, "level": 0.35}

        # ---------- BASS ----------
        # root->fifth movement on 1 & 3-ish; density raises activity
        if density == "dense":
            bass_pat = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0]
        elif density == "full":
            bass_pat = [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0]
        elif density == "mid":
            bass_pat = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]
        else:
            bass_pat = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]

        if brightness < 0.35 or bpm < 118:
            channels["bass_sub"] = {"pattern": bass_pat, "level": 0.95,
                                    "note_root": bass_root,
                                    "params": {"decay": 3.0}}
        else:
            drive = 1.0 + roughness * 3
            channels["bass_saw"] = {"pattern": bass_pat, "level": 0.9,
                                    "note_root": bass_root,
                                    "params": {"cutoff": 350 + roughness * 600,
                                               "drive": round(drive, 2)}}

        # ---------- MELODIC (pluck arp when bright; pad when calm/low vocal) ----------
        # arp when bright + not too sparse; pad when calm / vocal space open
        if brightness > 0.5 and density != "sparse":
            arp = [1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0]
            channels["pluck"] = {"pattern": arp, "level": 0.5,
                                 "note_root": bass_root + 24,
                                 "params": {"damp": 0.975}}
        elif density in ("sparse", "mid") or vocal_risk < 0.3:
            pad = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
            channels["pad"] = {"pattern": pad, "level": 0.35,
                               "note_root": bass_root + 24,
                               "params": {"detune": 0.3, "cutoff": 900}}

        return channels


def describe_style(style: dict) -> str:
    """Human-readable summary of a generated style."""
    c = style["channels"]
    names = list(c.keys())
    return (
        f"BPM {style['bpm']} | {style['key']} ({style['scale']}) | "
        f"{style['mood'].title()} | energy {style['energy']} | "
        f"bright {style['brightness']} | swing {style['swing']} | "
        f"channels: {', '.join(names)}"
    )
