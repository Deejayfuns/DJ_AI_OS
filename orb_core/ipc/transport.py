"""
ORB IPC — Cross-Platform Inter-Process Communication
====================================================
Supports:
- Windows: Named Pipes
- Linux/macOS: Unix Domain Sockets
- Fallback: gRPC/HTTP
"""
import asyncio
import json
import os
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, Optional
import msgpack


@dataclass
class Message:
    """IPC message envelope."""
    id: str
    method: str
    params: Dict[str, Any]
    reply_to: Optional[str] = None
    timestamp: float = 0.0


class Transport(ABC):
    """Abstract transport layer."""

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def send(self, message: Message) -> None:
        pass

    @abstractmethod
    async def receive(self) -> AsyncGenerator[Message, None]:
        pass


class NamedPipeTransport(Transport):
    """Windows Named Pipes transport."""

    def __init__(self, pipe_name: str, is_server: bool = True):
        self.pipe_name = pipe_name
        self.is_server = is_server
        self._server = None
        self._reader = None
        self._writer = None
        self._pipe_path = f"\\\\.\\pipe\\{pipe_name}"

    async def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Named pipes only supported on Windows")

        if self.is_server:
            import win32pipe
            import win32file
            import pywintypes

            self._server = win32pipe.CreateNamedPipe(
                self._pipe_path,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                65536, 65536, 0, None
            )
            # Accept connections in background
            asyncio.create_task(self._accept_loop())
        else:
            import win32file
            self._writer = win32file.CreateFile(
                self._pipe_path,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )

    async def _accept_loop(self) -> None:
        import win32pipe
        import win32file
        while True:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, win32pipe.ConnectNamedPipe, self._server, None
                )
                # Handle client connection
            except Exception:
                await asyncio.sleep(0.1)

    async def stop(self) -> None:
        if self._server:
            import win32file
            win32file.CloseHandle(self._server)
        if self._writer:
            import win32file
            win32file.CloseHandle(self._writer)

    async def send(self, message: Message) -> None:
        data = msgpack.packb(message.__dict__, use_bin_type=True)
        length = len(data).to_bytes(4, "little")

        if self.is_server:
            # Server broadcasts to all connected clients
            pass
        else:
            import win32file
            await asyncio.get_event_loop().run_in_executor(
                None, win32file.WriteFile, self._writer, length + data
            )

    async def receive(self) -> AsyncGenerator[Message, None]:
        # Implementation depends on server/client mode
        pass


class UnixSocketTransport(Transport):
    """Unix Domain Socket transport for Linux/macOS."""

    def __init__(self, socket_path: str, is_server: bool = True):
        self.socket_path = Path(socket_path)
        self.is_server = is_server
        self._server = None
        self._reader = None
        self._writer = None

    async def start(self) -> None:
        if self.socket_path.exists():
            self.socket_path.unlink()

        if self.is_server:
            self._server = await asyncio.start_unix_server(
                self._handle_client, str(self.socket_path)
            )
        else:
            self._reader, self._writer = await asyncio.open_unix_connection(
                str(self.socket_path)
            )

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        # Handle client messages
        while True:
            try:
                length_bytes = await reader.readexactly(4)
                length = int.from_bytes(length_bytes, "little")
                data = await reader.readexactly(length)
                message = Message(**msgpack.unpackb(data, raw=False))
                # Process message
            except asyncio.IncompleteReadError:
                break
            except Exception:
                break
        writer.close()

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        if self.socket_path.exists():
            self.socket_path.unlink()

    async def send(self, message: Message) -> None:
        data = msgpack.packb(message.__dict__, use_bin_type=True)
        length = len(data).to_bytes(4, "little")
        if self._writer:
            self._writer.write(length + data)
            await self._writer.drain()

    async def receive(self) -> AsyncGenerator[Message, None]:
        if not self._reader:
            return
        while True:
            try:
                length_bytes = await self._reader.readexactly(4)
                length = int.from_bytes(length_bytes, "little")
                data = await self._reader.readexactly(length)
                yield Message(**msgpack.unpackb(data, raw=False))
            except asyncio.IncompleteReadError:
                break
            except Exception:
                break


class GRPCTransport(Transport):
    """gRPC transport fallback for cross-platform."""

    def __init__(self, host: str = "localhost", port: int = 50051, is_server: bool = True):
        self.host = host
        self.port = port
        self.is_server = is_server
        self._server = None
        self._channel = None
        self._stub = None

    async def start(self) -> None:
        try:
            import grpc
            from . import orb_pb2, orb_pb2_grpc
        except ImportError:
            raise RuntimeError("gRPC not available. Install grpcio and grpcio-tools")

        if self.is_server:
            self._server = grpc.aio.server()
            # Add servicer
            self._server.add_insecure_port(f"{self.host}:{self.port}")
            await self._server.start()
        else:
            self._channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
            self._stub = orb_pb2_grpc.OrbServiceStub(self._channel)

    async def stop(self) -> None:
        if self._server:
            await self._server.stop(grace=5)
        if self._channel:
            await self._channel.close()

    async def send(self, message: Message) -> None:
        if not self.is_server and self._stub:
            import grpc
            from . import orb_pb2
            request = orb_pb2.Message(
                id=message.id,
                method=message.method,
                params=json.dumps(message.params),
                reply_to=message.reply_to or "",
                timestamp=message.timestamp
            )
            await self._stub.SendMessage(request)

    async def receive(self) -> AsyncGenerator[Message, None]:
        # gRPC streaming implementation
        pass


def create_transport(endpoint: str, is_server: bool = True) -> Transport:
    """Factory to create appropriate transport based on platform and endpoint."""
    # endpoint format: "pipe://name", "unix:///path", "grpc://host:port"
    if endpoint.startswith("pipe://") or (sys.platform == "win32" and not endpoint.startswith(("unix://", "grpc://"))):
        name = endpoint.replace("pipe://", "") or "orb_default"
        return NamedPipeTransport(name, is_server)
    elif endpoint.startswith("unix://") or (sys.platform != "win32" and not endpoint.startswith("grpc://")):
        path = endpoint.replace("unix://", "") or "/tmp/orb.sock"
        return UnixSocketTransport(path, is_server)
    elif endpoint.startswith("grpc://"):
        host_port = endpoint.replace("grpc://", "localhost:50051")
        host, port = host_port.split(":") if ":" in host_port else (host_port, "50051")
        return GRPCTransport(host, int(port), is_server)
    else:
        # Default: named pipe on Windows, unix socket on Unix
        if sys.platform == "win32":
            return NamedPipeTransport("orb_default", is_server)
        else:
            return UnixSocketTransport("/tmp/orb.sock", is_server)


class Protocol:
    """Message serialization/deserialization."""

    @staticmethod
    def encode(message: Message) -> bytes:
        return msgpack.packb(message.__dict__, use_bin_type=True)

    @staticmethod
    def decode(data: bytes) -> Message:
        return Message(**msgpack.unpackb(data, raw=False))

    @staticmethod
    def encode_request(method: str, params: Dict[str, Any], reply_to: str = None) -> bytes:
        msg = Message(
            id=str(uuid.uuid4()),
            method=method,
            params=params,
            reply_to=reply_to,
            timestamp=time.time(),
        )
        return Protocol.encode(msg)

    @staticmethod
    def encode_response(request_id: str, result: Any = None, error: str = None) -> bytes:
        msg = Message(
            id=request_id,
            method="response",
            params={"result": result, "error": error},
            timestamp=time.time(),
        )
        return Protocol.encode(msg)