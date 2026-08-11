"""
ORB IPC — Protocol Definitions
==============================
Message protocol and serialization.
"""
import time
import msgpack
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from datetime import datetime


def _now() -> float:
    """Wall-clock timestamp that works with or without an event loop."""
    try:
        import asyncio
        return asyncio.get_event_loop().time()
    except Exception:
        return time.time()


@dataclass
class Message:
    """IPC message envelope."""
    id: str
    method: str
    params: Dict[str, Any]
    reply_to: Optional[str] = None
    timestamp: float = 0.0
    source: Optional[str] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = _now()

    def to_bytes(self) -> bytes:
        return msgpack.packb(asdict(self), use_bin_type=True)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        return cls(**msgpack.unpackb(data, raw=False))

    @classmethod
    def request(cls, method: str, params: Dict[str, Any], reply_to: str = None) -> "Message":
        return cls(
            id=str(uuid.uuid4()),
            method=method,
            params=params,
            reply_to=reply_to,
            timestamp=_now()
        )

    @classmethod
    def response(cls, request_id: str, result: Any = None, error: str = None) -> "Message":
        return cls(
            id=request_id,
            method="response",
            params={"result": result, "error": error},
            timestamp=_now()
        )

    @classmethod
    def event(cls, topic: str, data: Any, source: str = None) -> "Message":
        return cls(
            id=str(uuid.uuid4()),
            method="event",
            params={"topic": topic, "data": data},
            source=source,
            timestamp=_now()
        )


class Protocol:
    """Message serialization/deserialization with framing."""

    MAGIC = b"ORB1"
    HEADER_SIZE = 4 + 4  # magic + length

    @staticmethod
    def encode(message: Message) -> bytes:
        payload = message.to_bytes()
        length = len(payload)
        return Protocol.MAGIC + length.to_bytes(4, "little") + payload

    @staticmethod
    def decode(data: bytes) -> Optional[Message]:
        if len(data) < Protocol.HEADER_SIZE:
            return None
        if data[:4] != Protocol.MAGIC:
            return None
        length = int.from_bytes(data[4:8], "little")
        if len(data) < Protocol.HEADER_SIZE + length:
            return None
        payload = data[8:8+length]
        return Message.from_bytes(payload)

    @staticmethod
    def decode_stream(buffer: bytearray) -> list[Message]:
        """Decode multiple messages from a stream buffer."""
        messages = []
        i = 0
        while i + Protocol.HEADER_SIZE <= len(buffer):
            if buffer[i:i+4] != Protocol.MAGIC:
                i += 1
                continue
            if i + Protocol.HEADER_SIZE > len(buffer):
                break
            length = int.from_bytes(buffer[i+4:i+8], "little")
            if i + Protocol.HEADER_SIZE + length > len(buffer):
                break
            payload = buffer[i+8:i+8+length]
            try:
                msg = Message.from_bytes(payload)
                messages.append(msg)
            except Exception:
                pass
            i += Protocol.HEADER_SIZE + length
        # Remove processed bytes
        if messages:
            del buffer[:i]
        return messages