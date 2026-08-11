"""
ORB IPC — Cross-Platform Inter-Process Communication Layer.

Transports:
    Windows   -> Named Pipes (\\\\.\\pipe\\...)
    Linux/mac -> Unix Domain Sockets (/tmp/orb.sock)
    Fallback  -> gRPC (cross-language)

Also includes:
    Protocol   — msgpack message framing
    Discovery  — mDNS (zeroconf) service discovery
    LocalRegistry — in-process service registry
"""
from .protocol import Message, Protocol
from .transport import (
    Transport,
    NamedPipeTransport,
    UnixSocketTransport,
    GRPCTransport,
    create_transport,
)
from .discovery import Discovery, ServiceInfo, LocalRegistry, get_registry

__all__ = [
    "Message", "Protocol",
    "Transport", "NamedPipeTransport", "UnixSocketTransport", "GRPCTransport",
    "create_transport",
    "Discovery", "ServiceInfo", "LocalRegistry", "get_registry",
]