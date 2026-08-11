"""
ORB IPC — Protocol & Discovery
==============================
Message protocol definitions and service discovery.
"""
import asyncio
import socket
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

try:
    import zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    zeroconf = None
    ZEROCONF_AVAILABLE = False


@dataclass
class ServiceInfo:
    """Discovered service information."""
    name: str
    type: str  # e.g., "_orb._tcp.local."
    host: str
    port: int
    properties: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Discovery:
    """Service discovery using mDNS (zeroconf) + local registry."""

    def __init__(self, service_name: str = "orb", service_type: str = "_orb._tcp.local."):
        self.service_name = service_name
        self.service_type = service_type
        self._zeroconf = None
        self._service_info = None
        self._browser = None
        self._discovered: Dict[str, ServiceInfo] = {}
        self._callbacks: List[callable] = []

    async def start(self, port: int, properties: Dict[str, str] = None) -> None:
        """Register this service and start browsing."""
        if not ZEROCONF_AVAILABLE:
            print("Discovery disabled (zeroconf not installed)")
            return
        try:
            self._zeroconf = zeroconf.Zeroconf()
            self._service_info = zeroconf.ServiceInfo(
                self.service_type,
                f"{self.service_name}.{self.service_type}",
                addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
                port=port,
                properties=properties or {},
                server=f"{socket.gethostname()}.local.",
            )
            await asyncio.get_event_loop().run_in_executor(
                None, self._zeroconf.register_service, self._service_info
            )

            # Start browser
            self._browser = zeroconf.ServiceBrowser(
                self._zeroconf, self.service_type, handlers=[self._on_service_state_change]
            )
        except Exception as e:
            print(f"Discovery start failed: {e}")

    def _on_service_state_change(self, zeroconf, service_type: str, name: str, state_change: int) -> None:
        """Callback for service state changes."""
        if state_change == zeroconf.ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                svc = ServiceInfo(
                    name=name,
                    type=service_type,
                    host=socket.inet_ntoa(info.addresses[0]),
                    port=info.port,
                    properties={k.decode(): v.decode() for k, v in (info.properties or {}).items()},
                )
                self._discovered[name] = svc
                for cb in self._callbacks:
                    try:
                        cb(svc)
                    except Exception:
                        pass
        elif state_change == zeroconf.ServiceStateChange.Removed:
            self._discovered.pop(name, None)

    def on_discover(self, callback: callable) -> None:
        """Register callback for new service discovery."""
        self._callbacks.append(callback)

    def get_services(self) -> List[ServiceInfo]:
        """Get all discovered services."""
        return list(self._discovered.values())

    def find_service(self, name: str) -> Optional[ServiceInfo]:
        """Find specific service by name."""
        return self._discovered.get(name)

    async def stop(self) -> None:
        """Stop discovery and unregister."""
        if not ZEROCONF_AVAILABLE:
            return
        if self._browser:
            self._browser.cancel()
        if self._service_info and self._zeroconf:
            await asyncio.get_event_loop().run_in_executor(
                None, self._zeroconf.unregister_service, self._service_info
            )
        if self._zeroconf:
            self._zeroconf.close()


class LocalRegistry:
    """Local in-process service registry for modules."""

    def __init__(self):
        self._services: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, metadata: Dict[str, Any]) -> None:
        """Register a local service."""
        self._services[name] = {
            "name": name,
            "metadata": metadata,
            "pid": None,  # In-process
        }

    def unregister(self, name: str) -> None:
        """Unregister a local service."""
        self._services.pop(name, None)

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get service by name."""
        return self._services.get(name)

    def list(self) -> List[Dict[str, Any]]:
        """List all services."""
        return list(self._services.values())


# Global registry instance
_registry = LocalRegistry()


def get_registry() -> LocalRegistry:
    return _registry