"""
DJ AI OS — Plugin Base Classes

Abstract base class for all plugins.
Every plugin must subclass Plugin and implement required methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable


@dataclass
class PluginMeta:
    """Plugin metadata."""
    name: str
    version: str
    author: str = "DJ AI OS"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    category: str = "general"  # 'audio', 'ai', 'ui', 'cloud', 'control'
    enabled: bool = True


class Plugin(ABC):
    """
    Abstract base class for all DJ AI OS plugins.

    A plugin can:
    - Register voice commands
    - Register UI views/tabs
    - Register audio hooks (on_track_load, on_play, etc.)
    - Register AI analysis modules
    - Register MIDI handlers

    Example:
        class MyPlugin(Plugin):
            meta = PluginMeta(name="My Plugin", version="1.0")

            def on_load(self, app):
                self.register_command("my_command", self.handle_command)

            def handle_command(self, text):
                return {"ok": True, "reply": "Hello from my plugin!"}
    """

    meta: PluginMeta

    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._views: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._ai_modules: Dict[str, Any] = {}
        self._midi_handlers: Dict[str, Callable] = {}
        self._config: Dict[str, Any] = {}
        self._app = None

    @abstractmethod
    def on_load(self, app):
        """Called when plugin is loaded. Use this to initialize."""
        self._app = app

    def on_unload(self):
        """Called when plugin is unloaded. Use this to cleanup."""
        pass

    def on_enable(self):
        """Called when plugin is enabled."""
        pass

    def on_disable(self):
        """Called when plugin is disabled."""
        pass

    # ============================================================
    # REGISTRATION HELPERS
    # ============================================================

    def register_command(self, name: str, handler: Callable, description: str = ""):
        """Register a voice/text command."""
        self._commands[name] = {
            "handler": handler,
            "description": description,
            "plugin": self.meta.name,
        }

    def register_view(self, name: str, view_class_or_builder):
        """Register a UI view/tab."""
        self._views[name] = {
            "class": view_class_or_builder,
            "plugin": self.meta.name,
        }

    def register_hook(self, event: str, handler: Callable):
        """Register a hook for an event (on_track_load, on_play, etc.)."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    def register_ai_module(self, name: str, module):
        """Register an AI analysis module."""
        self._ai_modules[name] = {
            "module": module,
            "plugin": self.meta.name,
        }

    def register_midi_handler(self, event_type: str, handler: Callable):
        """Register a MIDI event handler."""
        self._midi_handlers[event_type] = handler

    def set_config(self, key: str, value: Any):
        """Set a plugin config value."""
        self._config[key] = value

    def get_config(self, key: str, default=None):
        """Get a plugin config value."""
        return self._config.get(key, default)

    # ============================================================
    # ACCESSORS (called by registry)
    # ============================================================

    def get_commands(self) -> Dict[str, Any]:
        return self._commands

    def get_views(self) -> Dict[str, Any]:
        return self._views

    def get_hooks(self) -> Dict[str, List[Callable]]:
        return self._hooks

    def get_ai_modules(self) -> Dict[str, Any]:
        return self._ai_modules

    def get_midi_handlers(self) -> Dict[str, Callable]:
        return self._midi_handlers
