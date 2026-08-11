"""
DJ AI OS — Instrument Plugin Base & Registry

Modular instrument system. Each instrument is a self-contained plugin
with a name, category, parameter schema and a `hit()` renderer.

This is the Astra Nexus module contract: any plugin here can be mounted
by the future Astra Nexus plugin host with zero code changes.
"""

import numpy as np

SR_DEFAULT = 44100


class InstrumentPlugin:
    """
    Base class for all instrument plugins.

    Subclass contract:
      name     : unique plugin id (registry key)
      category : 'percussion' | 'melodic'
      params   : dict name -> {min, max, default}
      hit()    : render one note/hit -> float32 mono np.ndarray

    A plugin must be registered with @register for discovery.
    """

    name = "base"
    category = "percussion"
    params = {}
    description = ""

    # True = the sound only depends on params (+velocity), so identical
    # param states can be cached. Set False for pads/drones that should
    # always re-render.
    cacheable = True

    def __init__(self, sample_rate=SR_DEFAULT):
        self.sr = sample_rate
        self._params = {k: v["default"] for k, v in self.params.items()}
        self._cache = {}
        self._last_note = None

    # ---- parameter API (live automation target) ----
    def set_param(self, key, value):
        """Set a live parameter (clamped to schema)."""
        if key not in self.params:
            return
        lo, hi = self.params[key]["min"], self.params[key]["max"]
        self._params[key] = float(max(lo, min(hi, value)))
        # parameters changed -> cached sound stale
        if self.cacheable:
            self._cache = {}

    def get_params(self):
        return dict(self._params)

    def param_schema(self):
        return {k: dict(v) for k, v in self.params.items()}

    # ---- rendering API ----
    def hit(self, note=None, velocity=1.0):
        """
        Render one note/hit. `note` is a MIDI note number (melodic only).
        Results are cached per (note, round(velocity*10)) for cacheable
        plugins — huge speedup for pattern playback.
        """
        if self.cacheable:
            key = (note, round(velocity * 10))
            if key in self._cache:
                return self._cache[key]
            raw = self._render(note, velocity)
            self._cache[key] = raw
            return raw
        return self._render(note, velocity)

    def _render(self, note, velocity):
        raise NotImplementedError

    # ---- utilities ----
    def _norm(self, sig, level=0.9):
        if len(sig) == 0:
            return sig
        peak = np.max(np.abs(sig)) or 1.0
        return (sig / peak * level).astype(np.float32)

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.name}'>"


# ============================================================
# REGISTRY
# ============================================================

_REGISTRY = {}


def register(cls):
    """Class decorator: register an instrument plugin."""
    if not cls.name or cls.name == "base":
        raise ValueError("Instrument plugin must define a unique 'name'")
    _REGISTRY[cls.name] = cls
    return cls


def get_instrument(name, sample_rate=SR_DEFAULT):
    """Instantiate a registered instrument plugin by name."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown instrument plugin: {name}. "
                       f"Available: {list_instruments()}")
    return _REGISTRY[name](sample_rate=sample_rate)


def has_instrument(name):
    return name in _REGISTRY


def list_instruments(category=None):
    """List registered instruments, optionally filtered by category."""
    names = []
    for n, cls in _REGISTRY.items():
        if category and cls.category != category:
            continue
        names.append(n)
    return sorted(names)


def instrument_catalog():
    """Full catalog for UI / Astra Nexus discovery."""
    return [
        {"name": n, "category": cls.category, "description": cls.description,
         "params": {k: dict(v) for k, v in cls.params.items()}}
        for n, cls in sorted(_REGISTRY.items())
    ]
