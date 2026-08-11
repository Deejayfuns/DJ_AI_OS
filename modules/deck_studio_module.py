"""
ORB Module — Deck Studio (4-Deck Virtual DJ)
============================================
Wraps the 4-deck DJ engine + MIDI/HID routing.
"""
from typing import Any, Dict, Optional

from .base import OrbModule


class DeckStudioModule(OrbModule):
    """Deck studio module."""

    EVENT_TOPICS = ["deck.play", "deck.pause", "deck.sync", "deck.hotcue"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="deck_studio")
        self._engine = None

    def start(self) -> None:
        try:
            from app.ai.four_deck_engine import FourDeckEngine
            self._engine = FourDeckEngine()
            self.log("4-deck engine ready")
        except ImportError as e:
            self.log(f"four_deck_engine not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    # Public API — called by UI and MIDI/HID modules
    def play_deck(self, deck: str) -> None:
        d = self._engine.decks.get(deck) if self._engine else None
        if d:
            d.play()
            self.publish("deck.play", {"deck": deck})

    def pause_deck(self, deck: str) -> None:
        d = self._engine.decks.get(deck) if self._engine else None
        if d:
            d.pause()
            self.publish("deck.pause", {"deck": deck})

    def sync_deck(self, deck: str) -> None:
        d = self._engine.decks.get(deck) if self._engine else None
        if d and self._engine:
            self._engine._sync_deck(d)

    def trigger_hotcue(self, deck: str, idx: int) -> None:
        d = self._engine.decks.get(deck) if self._engine else None
        if d:
            if idx in d.hot_cues:
                d.trigger_hot_cue(idx)
            else:
                d.set_hot_cue(idx)
            self.publish("deck.hotcue", {"deck": deck, "idx": idx})

    def health_check(self) -> Dict[str, Any]:
        return {
            "engine_ready": self._engine is not None,
            "decks": list(self._engine.decks.keys()) if self._engine else [],
        }