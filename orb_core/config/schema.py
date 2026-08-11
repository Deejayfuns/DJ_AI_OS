"""
ORB Config — Pydantic Schemas & Validation
==========================================
Centralized configuration with schema validation.
"""
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, Field, ValidationError


class ConfigSource(str, Enum):
    """Where config value came from."""
    DEFAULT = "default"
    FILE = "file"
    ENV = "env"
    REGISTRY = "registry"
    RUNTIME = "runtime"


class AppConfig(BaseModel):
    """Base application config schema."""
    app_name: str = "DJ AI OS"
    version: str = "0.1.0"
    debug: bool = False
    data_dir: str = "./data"
    log_level: str = "INFO"


class AudioConfig(BaseModel):
    """Audio engine config."""
    sample_rate: int = 44100
    buffer_size: int = 1024
    channels: int = 2
    device: str = "default"
    use_vlc: bool = True


class MidiConfig(BaseModel):
    """MIDI configuration."""
    auto_discover: bool = True
    default_port: str = ""
    min_message_interval_ms: int = 5


class UiConfig(BaseModel):
    """UI configuration."""
    theme: str = "neon"  # neon, dark, light
    window_width: int = 1280
    window_height: int = 800
    fps_limit: int = 60
    glow_intensity: float = 0.6


class NetworkConfig(BaseModel):
    """Network configuration."""
    use_cloud: bool = False
    portal_url: str = "https://portal.astra.ai"
    telemetry_enabled: bool = False
    sync_interval_minutes: int = 30


class OrmConfig(BaseModel):
    """Database configuration."""
    db_path: str = "./dj_ai_library.db"
    max_connections: int = 10
    auto_backup: bool = True


class CompleteConfig(BaseModel):
    """Full application config combining all sections."""
    app: AppConfig = AppConfig()
    audio: AudioConfig = AudioConfig()
    midi: MidiConfig = MidiConfig()
    ui: UiConfig = UiConfig()
    network: NetworkConfig = NetworkConfig()
    orm: OrmConfig = OrmConfig()

    @classmethod
    def merge(cls, base: "CompleteConfig", overrides: Dict[str, Any]) -> "CompleteConfig":
        """Merge overrides into base config."""
        merged = base.model_dump(mode="json")
        _deep_merge(merged, overrides)
        return cls(**merged)


def _deep_merge(base: Dict, override: Dict) -> None:
    """Deep merge dicts."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


class Schema:
    """Schema manager for all module configs."""

    _schemas: Dict[str, Type[BaseModel]] = {
        "app": AppConfig,
        "audio": AudioConfig,
        "midi": MidiConfig,
        "ui": UiConfig,
        "network": NetworkConfig,
        "orm": OrmConfig,
        "complete": CompleteConfig,
    }

    @classmethod
    def register(cls, name: str, schema_class: Type[BaseModel]) -> None:
        """Register a new schema."""
        cls._schemas[name] = schema_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseModel]]:
        """Get schema by name."""
        return cls._schemas.get(name)

    @classmethod
    def validate(cls, name: str, data: Dict[str, Any]) -> Any:
        """Validate data against schema."""
        schema_class = cls._schemas.get(name)
        if not schema_class:
            raise ValueError(f"Unknown schema: {name}")
        try:
            return schema_class(**data)
        except ValidationError as e:
            raise ValueError(f"Config validation failed for {name}: {e}")

    @classmethod
    def list(cls) -> List[str]:
        """List registered schemas."""
        return list(cls._schemas.keys())