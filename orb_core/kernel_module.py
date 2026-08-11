"""
ORB Kernel Module — Core Module Wrapper
=======================================
Standard lifecycle for the kernel itself so it can participate
in the module system like any other module.
"""
from typing import Any, Dict


class KernelModule:
    """Core kernel module with standard lifecycle."""

    EVENT_TOPICS = ["orb.status", "orb.module_changed", "orb.error"]

    def __init__(self, kernel=None):
        self.kernel = kernel
        self._running = False

    def start(self):
        """Start kernel module."""
        self._running = True
        print("ORB Kernel module started")

    def stop(self):
        """Stop kernel module."""
        self._running = False
        print("ORB Kernel module stopped")

    def health_check(self):
        """Health check callback."""
        return {"running": self._running, "modules": len(self.kernel.modules) if self.kernel else 0}

    def on_event(self, event):
        """Handle events."""
        pass