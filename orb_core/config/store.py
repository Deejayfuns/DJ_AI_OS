"""
ORB Config — Store Backend
==========================
Config persistence with file backend + change watching.
"""
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ConfigStore:
    """Config store with file and env backends."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("./orb_config.json")
        self._values: Dict[str, Any] = {}
        self._sources: Dict[str, str] = {}
        self._lock = threading.RLock()
        self._watchers: Dict[str, Callable] = {}
        self._observer = None
        self._loaded = False

    def load(self) -> None:
        """Load config from file + env overrides."""
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                    self._values = file_data
                    for key in file_data:
                        self._sources[key] = "file"
                except Exception as e:
                    print(f"Config load error: {e}")

            # Env overrides (ORB_ prefix)
            prefix = "ORB_"
            for key, value in os.environ.items():
                if key.startswith(prefix):
                    cfg_key = key[len(prefix):].lower().replace("__", ".")
                    self._values[cfg_key] = value
                    self._sources[cfg_key] = "env"

            self._loaded = True

    def save(self) -> None:
        """Persist config to file."""
        with self._lock:
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._values, f, indent=2)
            except Exception as e:
                print(f"Config save error: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value (dot notation supported: audio.sample_rate)."""
        with self._lock:
            if "." in key:
                parts = key.split(".")
                val = self._values
                for part in parts:
                    if isinstance(val, dict) and part in val:
                        val = val[part]
                    else:
                        return default
                return val
            return self._values.get(key, default)

    def set(self, key: str, value: Any, source: str = "runtime") -> None:
        """Set config value and notify watchers."""
        with self._lock:
            if "." in key:
                parts = key.split(".")
                val = self._values
                for part in parts[:-1]:
                    if not isinstance(val.get(part), dict):
                        val[part] = {}
                    val = val[part]
                val[parts[-1]] = value
            else:
                self._values[key] = value
            self._sources[key] = source

        # Notify watchers
        for watch_key, callback in list(self._watchers.items()):
            if watch_key in (key, "*"):
                try:
                    callback(key, value)
                except Exception:
                    pass

    def update(self, updates: Dict[str, Any], source: str = "runtime") -> None:
        """Batch update config."""
        for key, value in updates.items():
            self.set(key, value, source)

    def get_all(self) -> Dict[str, Any]:
        """Get all config values."""
        with self._lock:
            return dict(self._values)

    def get_source(self, key: str) -> str:
        """Get source of a config value."""
        return self._sources.get(key, "default")

    def watch(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """Register a watcher for config changes."""
        self._watchers[key] = callback

    def unwatch(self, key: str) -> None:
        """Remove a watcher."""
        self._watchers.pop(key, None)

    def start_file_watch(self) -> None:
        """Watch config file for external changes (hot-reload)."""
        if self._observer:
            return

        class ConfigHandler(FileSystemEventHandler):
            def __init__(self, store):
                self.store = store

            def on_modified(self, event):
                if Path(event.src_path) == self.store.config_path:
                    time.sleep(0.2)
                    self.store.load()
                    # Notify watchers of any changes
                    for key, cb in list(self.store._watchers.items()):
                        try:
                            cb(key, self.store.get(key))
                        except Exception:
                            pass

        self._observer = Observer()
        self._observer.schedule(ConfigHandler(self), str(self.config_path.parent), recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop_file_watch(self) -> None:
        """Stop watching config file."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None