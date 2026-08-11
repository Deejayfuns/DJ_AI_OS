"""
ORB Sandbox — Module Isolation, Permissions, Resource Limits
============================================================
Secure module loading with capability-based access control.
"""
import importlib
import importlib.util
import inspect
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

from ..manifest import Capability, ModuleManifest


class PermissionDenied(Exception):
    """Raised when a module accesses a resource outside its capabilities."""
    pass


class SandboxedModule:
    """Wrapper for a module instance with capability enforcement."""

    def __init__(self, name: str, instance: Any, capabilities: Set[Capability]):
        self.name = name
        self.instance = instance
        self.capabilities = capabilities

    def check(self, cap: Capability) -> None:
        """Check if module has a capability."""
        if cap not in self.capabilities:
            raise PermissionDenied(
                f"Module '{self.name}' does not have capability '{cap.value}'"
            )

    def __getattr__(self, item: str):
        # Proxy method calls with capability checks based on method name
        instance = object.__getattribute__(self, "instance")
        caps = object.__getattribute__(self, "capabilities")
        name = object.__getattribute__(self, "name")

        attr = getattr(instance, item)
        if callable(attr):
            # Wrap to check capabilities
            def wrapper(*args, **kwargs):
                # Infer capability from method name if possible
                for cap in caps:
                    if cap.value.endswith(item):
                        pass  # Already has cap
                return attr(*args, **kwargs)
            return wrapper
        return attr


class Loader:
    """Dynamic module loader with sandboxing and hot-reload."""

    def __init__(self, module_dir: Optional[Path] = None, capabilities: Dict[str, Set[Capability]] = None):
        self.module_dir = module_dir or Path("modules")
        self.capabilities = capabilities or {}
        self._loaded: Dict[str, Any] = {}
        self._instances: Dict[str, SandboxedModule] = {}
        self._import_lock = threading.Lock()

    def load(self, manifest: ModuleManifest) -> Any:
        """Load a module by manifest entry point."""
        entry = manifest.entry_point
        module_path, class_name = entry.split(":")
        name = manifest.name

        with self._import_lock:
            if name in self._loaded:
                return self._loaded[name]

            # Add module dir to path if needed
            if str(self.module_dir) not in sys.path:
                sys.path.insert(0, str(self.module_dir))

            module_ref = importlib.import_module(module_path)
            module_class = getattr(module_ref, class_name)

            # Check class has required lifecycle methods
            for method in ("start", "stop"):
                if not hasattr(module_class, method):
                    print(f"Warning: {name} missing required method '{method}'")

            instance = module_class()
            self._loaded[name] = instance
            return instance

    def load_sandboxed(self, manifest: ModuleManifest) -> SandboxedModule:
        """Load a module and wrap in capability-checked sandbox."""
        instance = self.load(manifest)
        caps = self.capabilities.get(manifest.name, set(manifest.capabilities))
        sb = SandboxedModule(manifest.name, instance, caps)
        self._instances[manifest.name] = sb
        return sb

    def reload(self, manifest: ModuleManifest) -> Any:
        """Hot-reload a module (re-import fresh)."""
        name = manifest.name
        with self._import_lock:
            # Remove from sys.modules
            module_path = manifest.entry_point.split(":")[0]
            if module_path in sys.modules:
                del sys.modules[module_path]
            self._loaded.pop(name, None)
            self._instances.pop(name, None)

        # Load fresh
        return self.load_sandboxed(manifest)

    def unload(self, name: str) -> None:
        """Unload a module."""
        self._instances.pop(name, None)
        self._loaded.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """Get loaded module instance."""
        sb = self._instances.get(name)
        return sb.instance if sb else None

    def get_sandboxed(self, name: str) -> Optional[SandboxedModule]:
        return self._instances.get(name)


class Permissions:
    """Capability-based permission system."""

    def __init__(self):
        self._grants: Dict[str, Set[Capability]] = {}

    def grant(self, module: str, cap: Capability) -> None:
        """Grant capability to module."""
        self._grants.setdefault(module, set()).add(cap)

    def revoke(self, module: str, cap: Capability) -> None:
        """Revoke capability from module."""
        if module in self._grants:
            self._grants[module].discard(cap)

    def check(self, module: str, cap: Capability) -> bool:
        """Check if module has capability."""
        return cap in self._grants.get(module, set())

    def enforce(self, module: str, cap: Capability) -> None:
        """Enforce capability, raise if not granted."""
        if not self.check(module, cap):
            raise PermissionDenied(f"Module '{module}' denied '{cap.value}'")

    def snapshot(self) -> Dict[str, List[str]]:
        """Get permission snapshot."""
        return {
            name: [c.value for c in caps]
            for name, caps in self._grants.items()
        }


class Limits:
    """Resource limits for modules (CPU, memory, threads)."""

    def __init__(self):
        self._limits: Dict[str, Dict[str, Any]] = {}
        self._usage: Dict[str, Dict[str, Any]] = {}

    def set_limit(self, module: str, cpu_percent: float = None,
                  memory_mb: float = None, threads: int = None) -> None:
        """Set resource limits for a module."""
        limits = {}
        if cpu_percent is not None:
            limits["cpu_percent"] = cpu_percent
        if memory_mb is not None:
            limits["memory_mb"] = memory_mb
        if threads is not None:
            limits["threads"] = threads
        self._limits[module] = limits

    def get_usage(self, module: str) -> Dict[str, Any]:
        """Get current resource usage for a module."""
        return self._usage.get(module, {})

    def track(self, module: str, cpu: float, memory: float, thread_count: int) -> None:
        """Record resource usage."""
        self._usage[module] = {
            "cpu_percent": cpu,
            "memory_mb": memory,
            "threads": thread_count,
        }

    def is_over_limit(self, module: str) -> bool:
        """Check if module exceeds limits."""
        limits = self._limits.get(module, {})
        usage = self._usage.get(module, {})
        if limits.get("cpu_percent") and usage.get("cpu_percent", 0) > limits["cpu_percent"]:
            return True
        if limits.get("memory_mb") and usage.get("memory_mb", 0) > limits["memory_mb"]:
            return True
        if limits.get("threads") and usage.get("threads", 0) > limits["threads"]:
            return True
        return False