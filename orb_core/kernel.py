"""
ORB Kernel — Module Runtime & Event Bus
=======================================
Central kernel managing module lifecycle, event routing, and system services.
"""
import asyncio
import importlib
import sys
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from .manifest import Manifest, ModuleManifest, Capability, ModuleType


class ModuleState(str, Enum):
    """Module lifecycle states."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModuleSpec:
    """Runtime module specification."""
    manifest: ModuleManifest
    state: ModuleState = ModuleState.UNLOADED
    instance: Any = None
    module_ref: Any = None  # The imported module
    load_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    error: Optional[str] = None
    reload_count: int = 0
    event_subscriptions: Set[str] = field(default_factory=set)


class EventBus:
    """Async event bus with pub/sub and request/reply patterns."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._pending_replies: Dict[str, asyncio.Future] = {}
        self._reply_counter = 0

    def subscribe(self, topic: str, handler: Callable) -> None:
        """Subscribe to a topic."""
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        """Unsubscribe from a topic."""
        if handler in self._subscribers.get(topic, []):
            self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, data: Any = None, source: str = None) -> None:
        """Publish event to all subscribers (fire-and-forget)."""
        event = Event(topic=topic, data=data, source=source, timestamp=datetime.now())
        for handler in self._subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception:
                pass  # Log but don't break other handlers

    async def request(self, topic: str, data: Any = None, timeout: float = 5.0) -> Any:
        """Request-reply pattern with timeout."""
        self._reply_counter += 1
        reply_id = f"{topic}_reply_{self._reply_counter}"
        future = asyncio.get_event_loop().create_future()
        self._pending_replies[reply_id] = future

        event = Event(topic=topic, data=data, reply_to=reply_id, timestamp=datetime.now())
        for handler in self._subscribers.get(topic, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception:
                pass

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request to {topic} timed out")
        finally:
            self._pending_replies.pop(reply_id, None)

    def reply(self, reply_id: str, data: Any) -> None:
        """Send reply to a request."""
        future = self._pending_replies.pop(reply_id, None)
        if future and not future.done():
            future.set_result(data)


@dataclass
class Event:
    """Event data structure."""
    topic: str
    data: Any = None
    source: str = None
    reply_to: str = None
    timestamp: datetime = None


class Kernel:
    """ORB Kernel - Central runtime manager."""

    def __init__(self, manifest_path: Optional[Path] = None):
        self.manifest: Optional[Manifest] = None
        self.modules: Dict[str, ModuleSpec] = {}
        self.event_bus = EventBus()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._capability_providers: Dict[Capability, str] = {}  # cap -> module_name

        if manifest_path:
            self.load_manifest(manifest_path)

    def load_manifest(self, path: Path) -> None:
        """Load and validate manifest."""
        self.manifest = Manifest.from_file(path)
        errors = self.manifest.validate()
        if errors:
            raise ValueError(f"Manifest validation errors:\n" + "\n".join(errors))

        # Create ModuleSpec for each module
        for name, mod_manifest in self.manifest.modules.items():
            self.modules[name] = ModuleSpec(manifest=mod_manifest)

    async def start(self) -> None:
        """Start kernel and all modules in dependency order."""
        if not self.manifest:
            raise RuntimeError("No manifest loaded")

        self._running = True
        load_order = self.manifest.get_load_order()

        # Load modules
        for name in load_order:
            await self._load_module(name)

        # Start modules
        for name in load_order:
            await self._start_module(name)

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._config_watch_loop()),
        ]

    async def stop(self) -> None:
        """Stop kernel and all modules."""
        self._running = False

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Stop modules in reverse order
        load_order = self.manifest.get_load_order()
        for name in reversed(load_order):
            await self._stop_module(name)

        # Unload modules
        for name in reversed(load_order):
            await self._unload_module(name)

    async def _load_module(self, name: str) -> None:
        """Load a single module."""
        spec = self.modules[name]
        spec.state = ModuleState.LOADING

        try:
            # Import module
            module_path, class_name = spec.manifest.entry_point.split(":")
            module_ref = importlib.import_module(module_path)
            module_class = getattr(module_ref, class_name)

            # Instantiate with kernel reference
            instance = module_class(kernel=self)
            spec.instance = instance
            spec.module_ref = module_ref
            spec.load_time = datetime.now()
            spec.state = ModuleState.LOADED

            # Register capabilities (shared read caps are normal; provider = first module)
            for cap in spec.manifest.capabilities:
                self._capability_providers.setdefault(cap, name)

            # Auto-subscribe to module's event topics if it has handlers
            if hasattr(instance, "on_event"):
                for topic in getattr(instance, "EVENT_TOPICS", []):
                    self.event_bus.subscribe(topic, instance.on_event)
                    spec.event_subscriptions.add(topic)

        except Exception as e:
            spec.state = ModuleState.ERROR
            spec.error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            raise

    async def _start_module(self, name: str) -> None:
        """Start a loaded module. Failures are contained (crash isolation):
        a module that fails to start is marked ERROR but the rest keep going."""
        spec = self.modules[name]
        if spec.state != ModuleState.LOADED:
            return

        spec.state = ModuleState.STARTING
        try:
            if hasattr(spec.instance, "start"):
                if asyncio.iscoroutinefunction(spec.instance.start):
                    await spec.instance.start()
                else:
                    spec.instance.start()
            spec.state = ModuleState.RUNNING
            spec.start_time = datetime.now()
        except Exception as e:
            spec.state = ModuleState.ERROR
            spec.error = f"Start failed: {type(e).__name__}: {e}"
            print(f"[kernel] module '{name}' failed to start: {spec.error}")
            traceback.print_exc()
            # Do NOT re-raise — crash containment: keep the rest of the system running

    async def _stop_module(self, name: str) -> None:
        """Stop a running module."""
        spec = self.modules[name]
        if spec.state != ModuleState.RUNNING:
            return

        spec.state = ModuleState.STOPPING
        try:
            if hasattr(spec.instance, "stop"):
                if asyncio.iscoroutinefunction(spec.instance.stop):
                    await spec.instance.stop()
                else:
                    spec.instance.stop()
            spec.state = ModuleState.STOPPED
        except Exception as e:
            spec.error = f"Stop failed: {type(e).__name__}: {e}"
            traceback.print_exc()

    async def _unload_module(self, name: str) -> None:
        """Unload a module."""
        spec = self.modules[name]
        if spec.state == ModuleState.UNLOADED:
            return

        # Unsubscribe events
        for topic in spec.event_subscriptions:
            if hasattr(spec.instance, "on_event"):
                self.event_bus.unsubscribe(topic, spec.instance.on_event)

        # Clear capabilities
        for cap in spec.manifest.capabilities:
            if self._capability_providers.get(cap) == name:
                del self._capability_providers[cap]

        spec.instance = None
        spec.module_ref = None
        spec.state = ModuleState.UNLOADED

    async def reload_module(self, name: str) -> None:
        """Hot-reload a module."""
        spec = self.modules[name]
        if not spec.manifest.hot_reload:
            raise RuntimeError(f"Module {name} does not support hot reload")

        await self._stop_module(name)
        await self._unload_module(name)
        spec.reload_count += 1
        await self._load_module(name)
        await self._start_module(name)

    def get_module(self, name: str) -> Optional[Any]:
        """Get module instance by name."""
        spec = self.modules.get(name)
        return spec.instance if spec else None

    def get_capability_provider(self, cap: Capability) -> Optional[str]:
        """Get module name providing a capability."""
        return self._capability_providers.get(cap)

    def get_status(self) -> Dict[str, Any]:
        """Get kernel status."""
        return {
            "running": self._running,
            "modules": {
                name: {
                    "state": spec.state.value,
                    "type": spec.manifest.type.value,
                    "version": spec.manifest.version,
                    "load_time": spec.load_time.isoformat() if spec.load_time else None,
                    "start_time": spec.start_time.isoformat() if spec.start_time else None,
                    "error": spec.error,
                    "reload_count": spec.reload_count,
                }
                for name, spec in self.modules.items()
            },
            "capabilities": {cap.value: mod for cap, mod in self._capability_providers.items()},
        }

    async def _health_check_loop(self) -> None:
        """Periodic health checks."""
        while self._running:
            await asyncio.sleep(30)
            for name, spec in self.modules.items():
                if spec.state == ModuleState.RUNNING and hasattr(spec.instance, "health_check"):
                    try:
                        if asyncio.iscoroutinefunction(spec.instance.health_check):
                            await spec.instance.health_check()
                        else:
                            spec.instance.health_check()
                    except Exception:
                        spec.state = ModuleState.ERROR

    async def _config_watch_loop(self) -> None:
        """Watch for config changes."""
        while self._running:
            await asyncio.sleep(5)
            # Config watching handled by config.Watch module

    @asynccontextmanager
    async def lifespan(self):
        """Context manager for kernel lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()