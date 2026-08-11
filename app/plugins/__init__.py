"""
DJ AI OS — Plugin System

Modular plugin architecture for extensible music features.
Plugins can register commands, views, hooks, and AI modules.

Usage:
    from app.plugins import get_registry
    registry = get_registry()
    registry.load_all()
"""

from app.plugins.base import Plugin, PluginMeta
from app.plugins.registry import PluginRegistry, get_registry

__all__ = ["Plugin", "PluginMeta", "PluginRegistry", "get_registry"]
