"""
ORB Module Base — Standard Lifecycle Contract
==============================================
Every module subclasses OrbModule and implements start/stop.
The kernel drives the lifecycle; modules talk via the event bus.
"""
import asyncio
import traceback
from typing import Any, Dict, List, Optional


class OrbModule:
    """Base class for all ORB modules."""

    # Topics this module consumes (kernel auto-subscribes on_event)
    EVENT_TOPICS: List[str] = []

    def __init__(self, kernel=None, name: str = ""):
        self.kernel = kernel
        self.name = name or self.__class__.__name__
        self._running = False
        self._state = "unloaded"

    # ------------------------------------------------------------------
    # Lifecycle — override these
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the module. Override. Set self._running = True."""
        self._running = True
        self._state = "running"

    def stop(self) -> None:
        """Stop the module. Override. Set self._running = False."""
        self._running = False
        self._state = "stopped"

    def health_check(self) -> Dict[str, Any]:
        """Optional — called periodically by kernel health loop."""
        return {"running": self._running}

    # ------------------------------------------------------------------
    # Events — override to consume subscribed topics
    # ------------------------------------------------------------------
    async def on_event(self, event) -> None:
        """Handle an event from the bus. Override."""
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def publish(self, topic: str, data: Any = None) -> None:
        """Publish an event to the bus (fire and forget)."""
        if self.kernel:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    self.kernel.event_bus.publish(topic, data, source=self.name)
                )
            except RuntimeError:
                # No running loop — safe no-op or warn
                pass

    def request(self, topic: str, data: Any = None, timeout: float = 5.0) -> Any:
        """Synchronous request/reply over the event bus."""
        if self.kernel:
            try:
                return asyncio.get_event_loop().run_until_complete(
                    self.kernel.event_bus.request(topic, data, timeout)
                )
            except Exception:
                return None
        return None

    def get_module(self, name: str):
        """Get another module instance from the kernel."""
        return self.kernel.get_module(name) if self.kernel else None

    def log(self, msg: str, level: str = "INFO") -> None:
        """Structured module log line."""
        print(f"[{self.name}] [{level}] {msg}")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._state}>"