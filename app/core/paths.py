"""
DJ AI OS — Frozen-aware path resolution

Provides consistent paths for user data (database, logs, cache) that work both
in development (repo root) and in PyInstaller frozen builds (APPDATA).
"""
import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True if running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_app_data_dir() -> Path:
    """
    Get the per-user application data directory.
    - Frozen: %APPDATA%/DJ_AI_OS (Windows) or ~/.local/share/DJ_AI_OS (Linux/macOS)
    - Dev: repo root
    """
    if is_frozen():
        # Windows: APPDATA is set; fallback to LOCALAPPDATA then home
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "DJ_AI_OS"
        # Linux/macOS fallback
        return Path.home() / ".local" / "share" / "DJ_AI_OS"
    # Development: use repo root (where main.py lives)
    return Path(__file__).resolve().parent.parent.parent


def get_db_path() -> Path:
    """Get the database file path, creating parent directory if needed."""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "dj_ai_library.db"


def get_log_dir() -> Path:
    """Get the log directory, creating it if needed."""
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_cache_dir() -> Path:
    """Get the cache directory, creating it if needed."""
    cache_dir = get_app_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_updates_dir() -> Path:
    """Get the updates directory (used by update_engine)."""
    updates_dir = get_app_data_dir() / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    return updates_dir


def get_license_path() -> Path:
    """Get the license file path, creating parent directory if needed."""
    data_dir = get_app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "license.key"


def get_library_output_dir() -> Path:
    """Get the DJ_LIBRARY_OUTPUT directory, creating it if needed."""
    output_dir = get_app_data_dir() / "DJ_LIBRARY_OUTPUT"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_song_vault_dir() -> Path:
    """Get the DJ_SONG_VAULT directory, creating it if needed."""
    output_dir = get_app_data_dir() / "DJ_SONG_VAULT"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_remix_lab_dir() -> Path:
    """Get the DJ_REMIX_LAB directory, creating it if needed."""
    output_dir = get_app_data_dir() / "DJ_REMIX_LAB"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_exports_dir() -> Path:
    """Get the DJ_EXPORTS directory, creating it if needed."""
    output_dir = get_app_data_dir() / "DJ_EXPORTS"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir