"""
DJ AI OS — Instrument Plugin System

Astra Nexus-ready modular instruments. Register new sounds by subclassing
InstrumentPlugin and decorating with @register — the registry does the rest.

Usage:
    from app.ai.instruments import list_instruments, get_instrument
    kick = get_instrument("kick")
    sample = kick.hit(velocity=0.9)
"""

from .base import (
    InstrumentPlugin,
    register,
    get_instrument,
    has_instrument,
    list_instruments,
    instrument_catalog,
    SR_DEFAULT,
)

# Import plugin modules so their @register decorators run
from . import synth_core    # noqa: F401  (sound source)
from . import drums         # noqa: F401  (percussion plugins)
from . import melodic       # noqa: F401  (melodic plugins)
from . import melodic_tech  # noqa: F401  (melodic techno kit)
from . import synth_patch   # noqa: F401  (Serum-style patch synth)
from . import neural_synth  # noqa: F401  (neural timbre VAE / spectral morph / RAVE)

__all__ = [
    "InstrumentPlugin",
    "register",
    "get_instrument",
    "has_instrument",
    "list_instruments",
    "instrument_catalog",
    "SR_DEFAULT",
]
