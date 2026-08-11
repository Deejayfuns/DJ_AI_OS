"""
ORB Demo Module — Reference Implementation
==========================================
Shows the standard module lifecycle: start/stop/health_check/on_event.
Any module can copy this pattern and register in orb_manifest.yaml.
"""
import asyncio
from typing import Any, Dict, List


class DemoModule:
    """Reference ORB module demonstrating the lifecycle contract."""

    # Topics this module subscribes to (via kernel auto-subscribe)
    EVENT_TOPICS = ["orb.hello", "demo.command"]

    def __init__(self, kernel=None):
        self.kernel = kernel
        self._running = False
        self.counter = 0
        self.config = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self):
        """Called when kernel starts this module."""
        self._running = True
        print("[DemoModule] started")
        # Read config if kernel provides it
        if self.kernel:
            provider = self.kernel.get_capability_provider(
                __import__("orb_core.manifest", fromlist=["Capability"]).Capability.CONFIG_READ
            )
        return True

    def stop(self):
        """Called when kernel stops this module."""
        self._running = False
        print("[DemoModule] stopped")

    def health_check(self):
        """Called periodically by kernel health loop."""
        return {"running": self._running, "counter": self.counter}

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    async def on_event(self, event):
        """Handle subscribed events (auto-wired by kernel)."""
        if event.topic == "orb.hello":
            print(f"[DemoModule] got hello: {event.data}")
        elif event.topic == "demo.command":
            self.counter += 1
            print(f"[DemoModule] command #{self.counter}: {event.data}")
            # Optionally reply via event bus
            if event.reply_to and self.kernel:
                self.kernel.event_bus.reply(event.reply_to, {"ack": self.counter})

    # ------------------------------------------------------------------
    # Public API (callable from other modules via kernel.get_module)
    # ------------------------------------------------------------------
    def greet(self, name: str) -> str:
        """Sample public method."""
        return f"Hello {name} from DemoModule (count={self.counter})"

    def render_placeholder(self, canvas) -> None:
        """Sample UI hook a host module could call."""
        canvas.delete("all")
        canvas.create_text(
            canvas.winfo_width() // 2, canvas.winfo_height() // 2,
            text="◢ DEMO MODULE ◣",
            fill="#00f0ff", font=("Consolas", 14, "bold"),
        )