"""
ORB Modules — AI Brain, DJ Coach, DJ Profile
============================================
Collective AI modules that consume beat/audio events.
"""
from typing import Any, Dict, List, Optional

from .base import OrbModule


class AiBrainModule(OrbModule):
    """DJ Brain — set intelligence, music theory."""

    EVENT_TOPICS = ["beat.analyzed", "deck.play", "deck.sync"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="ai_brain")
        self._brain = None

    def start(self) -> None:
        try:
            from app.ai.dj_brain import DJBrain
            self._brain = DJBrain()
            self.log("DJ Brain ready")
        except (ImportError, AttributeError) as e:
            self.log(f"dj_brain not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    async def on_event(self, event) -> None:
        if self._brain is None:
            return
        if event.topic == "beat.analyzed":
            result = event.data.get("result", {})
            learn = getattr(self._brain, "learn_track", None)
            if learn:
                learn(result)
        elif event.topic == "deck.play":
            note_play = getattr(self._brain, "note_play", None)
            if note_play:
                note_play(event.data.get("deck"))

    def suggest_next_track(self, current: str, library: List[str]) -> Optional[str]:
        if self._brain is None:
            return None
        suggest = getattr(self._brain, "suggest_next", None)
        return suggest(current, library) if suggest else None

    def health_check(self) -> Dict[str, Any]:
        return {"brain_ready": self._brain is not None}


class DjCoachModule(OrbModule):
    """AI coach — live feedback on transitions, timing."""

    EVENT_TOPICS = ["deck.play", "deck.pause", "midi.event"]

    def __init__(self, kernel=None):
        super().__init__(kernel, name="dj_coach")
        self._coach = None

    def start(self) -> None:
        try:
            from app.ai.dj_coach import DJCoach
            self._coach = DJCoach()
            self.log("DJ Coach ready")
        except (ImportError, AttributeError) as e:
            self.log(f"dj_coach not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    async def on_event(self, event) -> None:
        if self._coach is None:
            return
        if event.topic in ("deck.play", "deck.pause"):
            analyze = getattr(self._coach, "analyze_transition", None)
            if analyze:
                tip = analyze(event.data)
                if tip:
                    self.publish("coach.tip", tip)

    def get_tips(self) -> List[str]:
        tips = getattr(self._coach, "get_tips", None)
        return tips() if tips else []

    def health_check(self) -> Dict[str, Any]:
        return {"coach_ready": self._coach is not None}


class DjProfileModule(OrbModule):
    """DJ Style DNA profile, track similarity, style evolution."""

    def __init__(self, kernel=None):
        super().__init__(kernel, name="dj_profile")
        self._profile = None

    def start(self) -> None:
        try:
            from app.ai.dj_profile import DJProfile
            self._profile = DJProfile()
            self.log("DJ Profile ready")
        except (ImportError, AttributeError) as e:
            self.log(f"dj_profile not available: {e}", "WARN")
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        self._running = False
        self._state = "stopped"

    def get_dna(self) -> Dict[str, Any]:
        dna = getattr(self._profile, "get_dna", None)
        return dna() if dna else {}

    def health_check(self) -> Dict[str, Any]:
        return {"profile_ready": self._profile is not None}