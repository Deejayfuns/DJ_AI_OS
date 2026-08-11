"""
ORB Manifest System
===================
Module declarations, capabilities, dependencies, and validation.
Uses Pydantic for schema validation.
"""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator
import yaml


class Capability(str, Enum):
    """System capabilities a module can request."""
    AUDIO_PLAYBACK = "audio.playback"
    AUDIO_RECORD = "audio.record"
    AUDIO_ANALYSIS = "audio.analysis"
    MIDI_INPUT = "midi.input"
    MIDI_OUTPUT = "midi.output"
    HID_INPUT = "hid.input"
    HID_OUTPUT = "hid.output"
    FILESYSTEM_READ = "fs.read"
    FILESYSTEM_WRITE = "fs.write"
    NETWORK_CLIENT = "net.client"
    NETWORK_SERVER = "net.server"
    GPU_ACCESS = "gpu.access"
    PROCESS_SPAWN = "process.spawn"
    UI_RENDER = "ui.render"
    CONFIG_READ = "config.read"
    CONFIG_WRITE = "config.write"
    EVENT_BUS_PUB = "events.publish"
    EVENT_BUS_SUB = "events.subscribe"
    IPC_CLIENT = "ipc.client"
    IPC_SERVER = "ipc.server"


class ModuleType(str, Enum):
    """Module categories."""
    CORE = "core"           # Kernel modules (always loaded)
    AUDIO = "audio"         # Playback, analysis, stems
    MIDI = "midi"           # MIDI I/O, mapping
    HID = "hid"             # Hardware controllers
    AI = "ai"               # DJ Brain, coach, profile
    UI = "ui"               # Visual components
    CLOUD = "cloud"         # Portal, sync, telemetry
    INSTRUMENT = "instrument"  # Synth, sampler
    UTILITY = "utility"     # Helpers, bridges


class ModuleManifest(BaseModel):
    """Single module declaration."""
    name: str = Field(..., pattern=r"^[a-z_][a-z0-9_]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(-[a-z0-9]+)?$")
    type: ModuleType
    description: str = ""
    entry_point: str  # e.g., "modules.beat_studio:BeatStudioModule"
    capabilities: List[Capability] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)  # Other module names
    optional_dependencies: List[str] = Field(default_factory=list)
    config_schema: Optional[str] = None  # Path to Pydantic schema class
    config_defaults: Dict[str, Any] = Field(default_factory=dict)
    hot_reload: bool = True
    singleton: bool = True
    priority: int = 100  # Load order (lower = earlier)
    platform: List[str] = Field(default_factory=lambda: ["win32", "linux", "darwin"])
    min_python: str = "3.10"
    tags: List[str] = Field(default_factory=list)

    @field_validator("dependencies", "optional_dependencies", mode="before")
    @classmethod
    def _split_deps(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v


class Manifest(BaseModel):
    """Complete ORB manifest - parsed from orb_manifest.yaml."""
    orb_version: str = "1.0"
    runtime: Dict[str, Any] = Field(default_factory=dict)
    modules: Dict[str, ModuleManifest] = Field(default_factory=dict)

    def get_load_order(self) -> List[str]:
        """Topological sort of modules by dependencies."""
        # Kahn's algorithm
        in_degree = {name: 0 for name in self.modules}
        adj = {name: [] for name in self.modules}

        for name, mod in self.modules.items():
            for dep in mod.dependencies:
                if dep in self.modules:
                    adj[dep].append(name)
                    in_degree[name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            # Sort by priority for deterministic order
            queue.sort(key=lambda n: self.modules[n].priority)
            name = queue.pop(0)
            result.append(name)
            for neighbor in adj[name]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.modules):
            # Circular dependency - fallback to priority sort
            return sorted(self.modules.keys(),
                          key=lambda n: self.modules[n].priority)
        return result

    def validate(self) -> List[str]:
        """Validate manifest, return list of errors."""
        errors = []
        names = set(self.modules.keys())

        for name, mod in self.modules.items():
            # Check dependencies exist
            for dep in mod.dependencies:
                if dep not in names:
                    errors.append(f"{name}: missing dependency '{dep}'")
            for dep in mod.optional_dependencies:
                if dep not in names:
                    errors.append(f"{name}: missing optional dependency '{dep}'")

            # Check entry point format
            if ":" not in mod.entry_point:
                errors.append(f"{name}: entry_point must be 'module:Class'")

        return errors

    @classmethod
    def from_file(cls, path: Path) -> "Manifest":
        """Load manifest from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_file(self, path: Path) -> None:
        """Write manifest to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(mode="json"), f, sort_keys=False, allow_unicode=True)