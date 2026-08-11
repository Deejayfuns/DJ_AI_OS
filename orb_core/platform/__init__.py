"""
ORB Platform — Cross-Platform Abstraction Layer
===============================================
Unified audio, MIDI, HID, filesystem, and process APIs.
Works on Windows, Linux, and macOS.
"""
import os
import sys
import platform as _platform
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Platform(str, Enum):
    WINDOWS = "win32"
    LINUX = "linux"
    MACOS = "darwin"
    OTHER = "other"


def current_platform() -> Platform:
    """Get current platform."""
    sysname = _platform.system()
    if sysname == "Windows":
        return Platform.WINDOWS
    elif sysname == "Linux":
        return Platform.LINUX
    elif sysname == "Darwin":
        return Platform.MACOS
    return Platform.OTHER


def is_windows() -> bool:
    return current_platform() == Platform.WINDOWS


def is_linux() -> bool:
    return current_platform() == Platform.LINUX


def is_macos() -> bool:
    return current_platform() == Platform.MACOS


class Audio:
    """Cross-platform audio abstraction."""

    @staticmethod
    def backends() -> List[str]:
        """Detect available audio backends."""
        backends = []
        try:
            import vlc
            backends.append("vlc")
        except ImportError:
            pass
        try:
            import pyaudio
            backends.append("portaudio")
        except ImportError:
            pass
        try:
            import sounddevice
            backends.append("sounddevice")
        except ImportError:
            pass
        return backends

    @staticmethod
    def create_player(backend: str = "auto", **kwargs) -> Any:
        """Create audio player using specified backend."""
        if backend == "auto":
            available = Audio.backends()
            if not available:
                raise RuntimeError("No audio backend available")
            backend = available[0]

        if backend == "vlc":
            import vlc
            return vlc.Instance(**kwargs)
        elif backend == "portaudio":
            import pyaudio
            return pyaudio.PyAudio()
        elif backend == "sounddevice":
            import sounddevice as sd
            return sd
        else:
            raise ValueError(f"Unknown audio backend: {backend}")


class MIDI:
    """Cross-platform MIDI abstraction."""

    @staticmethod
    def backends() -> List[str]:
        """Detect available MIDI backends."""
        backends = []
        try:
            import mido
            backends.append("mido")
        except ImportError:
            pass
        try:
            import rtmidi
            backends.append("rtmidi")
        except ImportError:
            pass
        return backends

    @staticmethod
    def get_input_names() -> List[str]:
        """List MIDI input ports."""
        try:
            import mido
            return mido.get_input_names()
        except ImportError:
            return []

    @staticmethod
    def get_output_names() -> List[str]:
        """List MIDI output ports."""
        try:
            import mido
            return mido.get_output_names()
        except ImportError:
            return []


class HID:
    """Cross-platform HID abstraction."""

    @staticmethod
    def backends() -> List[str]:
        """Detect available HID backends."""
        backends = []
        try:
            import hid
            backends.append("hidapi")
        except ImportError:
            pass
        try:
            import pywinusb.hid
            backends.append("pywinusb")
        except ImportError:
            pass
        return backends

    @staticmethod
    def enumerate(vendor_id: int = None, product_id: int = None) -> List[Dict]:
        """Enumerate HID devices."""
        try:
            import hid
            devices = hid.enumerate(vendor_id, product_id)
            return devices
        except ImportError:
            return []


class FS:
    """Cross-platform filesystem utilities."""

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize path for current platform."""
        if is_windows():
            return path.replace("/", "\\")
        else:
            return path.replace("\\", "/")

    @staticmethod
    def file_url_to_path(url: str) -> str:
        """Convert file:// URL to native path."""
        from urllib.parse import unquote, urlparse
        if not url.startswith("file://"):
            return url
        parsed = urlparse(url)
        path = unquote(parsed.path)
        if is_windows():
            # "file:///C:/music/song.mp3" -> "C:/music/song.mp3"
            # "file://server/share/song.mp3" -> "//server/share/song.mp3"
            if parsed.netloc:
                path = f"//{parsed.netloc}{path}"
            elif path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path.lstrip("/")
        return path

    @staticmethod
    def is_relative(path: str) -> bool:
        """Check if path is relative."""
        return not os.path.isabs(path)

    @staticmethod
    def get_drives() -> List[str]:
        """List available drives (Windows) or mount points (Unix)."""
        if is_windows():
            import string
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return drives
        else:
            return ["/"]

    @staticmethod
    def ensure_dir(path: str) -> str:
        """Ensure directory exists, return normalized path."""
        Path(path).mkdir(parents=True, exist_ok=True)
        return FS.normalize_path(path)


class Process:
    """Cross-platform process management."""

    @staticmethod
    def spawn(command: List[str], cwd: str = None, background: bool = False) -> Any:
        """Spawn a process."""
        import subprocess
        if background:
            flags = subprocess.CREATE_NO_WINDOW if is_windows() else 0
            return subprocess.Popen(
                command, cwd=cwd,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        else:
            return subprocess.run(command, cwd=cwd)

    @staticmethod
    def kill(pid: int) -> bool:
        """Kill a process by PID."""
        import signal
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except Exception:
            return False

    @staticmethod
    def set_affinity(pid: int, cpus: List[int]) -> bool:
        """Set CPU affinity for a process."""
        try:
            import psutil
            p = psutil.Process(pid)
            p.cpu_affinity(cpus)
            return True
        except Exception:
            return False

    @staticmethod
    def get_process_info(pid: int) -> Dict[str, Any]:
        """Get process info."""
        try:
            import psutil
            p = psutil.Process(pid)
            return {
                "pid": pid,
                "name": p.name(),
                "cpu_percent": p.cpu_percent(),
                "memory_mb": p.memory_info().rss / 1024 / 1024,
                "threads": p.num_threads(),
            }
        except Exception:
            return {"pid": pid, "name": "unknown", "cpu_percent": 0, "memory_mb": 0, "threads": 0}