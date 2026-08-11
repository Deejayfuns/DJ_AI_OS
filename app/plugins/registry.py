"""
DJ AI OS — Plugin Registry

Manages plugin loading, lifecycle, and event dispatch.
"""

import os
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from app.plugins.base import Plugin, PluginMeta


class PluginRegistry:
    """
    Central plugin registry.
    Discovers, loads, and manages all plugins.
    """

    def __init__(self, plugin_dirs: List[str] = None):
        self._plugins: Dict[str, Plugin] = {}
        self._commands: Dict[str, Any] = {}
        self._views: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._ai_modules: Dict[str, Any] = {}
        self._midi_handlers: Dict[str, Dict[str, Callable]] = {}
        self._plugin_dirs = plugin_dirs or [
            str(Path(__file__).parent / "builtin"),
        ]

    def discover(self) -> List[str]:
        """Discover available plugins from plugin directories."""
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue

            for filename in os.listdir(plugin_dir):
                if filename.startswith("_") or not filename.endswith(".py"):
                    continue

                module_name = filename[:-3]
                module_path = os.path.join(plugin_dir, filename)

                # Check if it has a Plugin subclass
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"app.plugins.builtin.{module_name}",
                        module_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, Plugin) and
                            attr is not Plugin):
                            discovered.append(f"app.plugins.builtin.{module_name}")
                            break
                except Exception:
                    pass

        return discovered

    def load(self, plugin_class_or_path) -> Optional[Plugin]:
        """Load a single plugin."""
        try:
            if isinstance(plugin_class_or_path, str):
                # Import from path
                module = importlib.import_module(plugin_class_or_path)
                # Find Plugin subclass
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Plugin) and
                        attr is not Plugin):
                        plugin_class = attr
                        break
                else:
                    return None
            else:
                plugin_class = plugin_class_or_path

            # Instantiate
            plugin = plugin_class()

            # Check name
            if not plugin.meta or not plugin.meta.name:
                return None

            # Check if already loaded
            if plugin.meta.name in self._plugins:
                return self._plugins[plugin.meta.name]

            # Store
            self._plugins[plugin.meta.name] = plugin

            # Register its commands, views, hooks, etc.
            self._register_plugin(plugin)

            return plugin

        except Exception as e:
            print(f"[PLUGIN] Failed to load {plugin_class_or_path}: {e}")
            return None

    def load_all(self, app=None) -> int:
        """Discover and load all available plugins."""
        count = 0

        # Load built-in plugins
        for plugin_dir in self._plugin_dirs:
            if not os.path.isdir(plugin_dir):
                continue

            for filename in os.listdir(plugin_dir):
                if filename.startswith("_") or not filename.endswith(".py"):
                    continue

                module_name = f"app.plugins.builtin.{filename[:-3]}"
                result = self.load(module_name)
                if result:
                    count += 1

        # Call on_load for all loaded plugins
        for plugin in self._plugins.values():
            try:
                plugin.on_load(app)
            except Exception as e:
                print(f"[PLUGIN] {plugin.meta.name}.on_load failed: {e}")

        return count

    def unload(self, name: str):
        """Unload a plugin by name."""
        if name in self._plugins:
            plugin = self._plugins[name]
            try:
                plugin.on_unload()
            except Exception:
                pass

            # Remove its registrations
            self._unregister_plugin(plugin)
            del self._plugins[name]

    def _register_plugin(self, plugin: Plugin):
        """Register a plugin's commands, views, hooks, etc."""
        for name, cmd in plugin.get_commands().items():
            self._commands[name] = cmd

        for name, view in plugin.get_views().items():
            self._views[name] = view

        for event, handlers in plugin.get_hooks().items():
            if event not in self._hooks:
                self._hooks[event] = []
            self._hooks[event].extend(handlers)

        for name, module in plugin.get_ai_modules().items():
            self._ai_modules[name] = module

        for event, handler in plugin.get_midi_handlers().items():
            self._midi_handlers[plugin.meta.name] = self._midi_handlers.get(plugin.meta.name, {})
            self._midi_handlers[plugin.meta.name][event] = handler

    def _unregister_plugin(self, plugin: Plugin):
        """Remove a plugin's registrations."""
        for name in list(plugin.get_commands().keys()):
            self._commands.pop(name, None)

        for name in list(plugin.get_views().keys()):
            self._views.pop(name, None)

        for event, handlers in plugin.get_hooks().items():
            if event in self._hooks:
                self._hooks[event] = [h for h in self._hooks[event] if h not in handlers]

        for name in list(plugin.get_ai_modules().keys()):
            self._ai_modules.pop(name, None)

        self._midi_handlers.pop(plugin.meta.name, None)

    # ============================================================
    # COMMAND DISPATCH
    # ============================================================

    def dispatch_command(self, command: str, text: str) -> Optional[Dict]:
        """Dispatch a command to the registered handler."""
        if command in self._commands:
            handler = self._commands[command]["handler"]
            try:
                return handler(text)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return None

    def dispatch_hook(self, event: str, *args, **kwargs):
        """Dispatch an event to all registered hooks."""
        for handler in self._hooks.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception:
                pass

    # ============================================================
    # QUERIES
    # ============================================================

    def get_plugin(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict]:
        return [
            {
                "name": p.meta.name,
                "version": p.meta.version,
                "author": p.meta.author,
                "description": p.meta.description,
                "category": p.meta.category,
                "enabled": p.meta.enabled,
                "commands": len(p.get_commands()),
                "views": len(p.get_views()),
            }
            for p in self._plugins.values()
        ]

    def get_all_commands(self) -> Dict[str, Any]:
        return dict(self._commands)

    def get_all_views(self) -> Dict[str, Any]:
        return dict(self._views)

    def get_all_hooks(self) -> Dict[str, List[Callable]]:
        return dict(self._hooks)

    def get_all_ai_modules(self) -> Dict[str, Any]:
        return dict(self._ai_modules)


# ============================================================
# SINGLETON
# ============================================================

_registry = None


def get_registry() -> PluginRegistry:
    """Get or create the global plugin registry."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
