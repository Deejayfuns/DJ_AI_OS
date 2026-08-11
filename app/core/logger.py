"""
DJ AI OS — Central Logger

Dual-mode logging system:
- Local: SQLite + rotating files
- Online: Server sync for remote monitoring
- Error tracking with full context
- Performance metrics

Usage:
    from app.core.logger import get_logger
    log = get_logger()
    log.info("Library loaded", tracks=6957)
    log.error("Playback failed", track="song.mp3", error=str(e))
    log.warning("Low disk space", free_mb=245)
"""

import os
import json
import time
import sqlite3
import traceback
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List


class DJLogger:
    """
    Central logging system for DJ AI OS.
    Writes to local SQLite + rotating log files.
    Queues events for server sync.
    """

    LEVELS = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}

    def __init__(self, log_dir: str = "data/logs", max_local_days: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_local_days = max_local_days
        self._db_path = self.log_dir / "events.db"
        self._file_path = self.log_dir / "app.log"
        self._sync_queue: List[Dict] = []
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite log database."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        category TEXT NOT NULL,
                        message TEXT NOT NULL,
                        context TEXT,
                        traceback TEXT,
                        sync_status TEXT DEFAULT 'pending'
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL,
                        tags TEXT
                    )
                """)
                conn.commit()
        except Exception:
            pass

    # ============================================================
    # LOGGING API
    # ============================================================

    def debug(self, message: str, **context):
        self._log("DEBUG", "general", message, context)

    def info(self, message: str, category: str = "general", **context):
        self._log("INFO", category, message, context)

    def warning(self, message: str, category: str = "general", **context):
        self._log("WARNING", category, message, context)

    def error(self, message: str, category: str = "general", exc_info: bool = False, **context):
        tb = traceback.format_exc() if exc_info and sys.exc_info()[1] else None
        self._log("ERROR", category, message, context, traceback_str=tb)

    def critical(self, message: str, category: str = "general", **context):
        self._log("CRITICAL", category, message, context)

    def metric(self, name: str, value: float, tags: Optional[Dict] = None):
        """Record a performance metric."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO metrics (timestamp, metric_name, metric_value, tags) VALUES (?, ?, ?, ?)",
                    (datetime.now().isoformat(), name, value, json.dumps(tags or {}))
                )
                conn.commit()
        except Exception:
            pass

    # ============================================================
    # CATEGORY-SPECIFIC LOGGERS
    # ============================================================

    def log_play(self, track: Dict, context: str = "library"):
        """Log a track play event."""
        self.info(
            f"PLAY: {track.get('name', '?')} | {track.get('bpm', '?')} BPM | {track.get('genre', '?')}",
            category="playback",
            track_name=track.get("name"),
            track_bpm=track.get("bpm"),
            track_genre=track.get("genre"),
            context=context,
        )

    def log_set_start(self, style: str, track_count: int):
        """Log set start."""
        self.info(
            f"SET START: {style} | {track_count} tracks",
            category="performance",
            style=style,
            track_count=track_count,
        )

    def log_error(self, module: str, error: str, details: Optional[Dict] = None):
        """Log an error with module context."""
        self.error(
            f"ERROR in {module}: {error}",
            category="error",
            module=module,
            error_message=error,
            details=details or {},
            exc_info=True,
        )

    def log_sync(self, direction: str, data_type: str, count: int):
        """Log sync event."""
        self.info(
            f"SYNC {direction}: {data_type} | {count} records",
            category="sync",
            direction=direction,
            data_type=data_type,
            count=count,
        )

    def log_plugin(self, plugin_name: str, event: str, details: str = ""):
        """Log plugin event."""
        self.info(
            f"PLUGIN {plugin_name}: {event} {details}".strip(),
            category="plugin",
            plugin=plugin_name,
            event=event,
        )

    # ============================================================
    # QUERY
    # ============================================================

    def get_recent(self, category: Optional[str] = None, level: Optional[str] = None,
                   limit: int = 50) -> List[Dict]:
        """Get recent log entries."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                query = "SELECT * FROM events WHERE 1=1"
                params = []
                if category:
                    query += " AND category = ?"
                    params.append(category)
                if level:
                    query += " AND level = ?"
                    params.append(level)
                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent errors."""
        return self.get_recent(category="error", level="ERROR", limit=limit)

    def get_metrics(self, metric_name: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Get metrics from the last N hours."""
        try:
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                if metric_name:
                    rows = conn.execute(
                        "SELECT * FROM metrics WHERE metric_name = ? AND timestamp > ? ORDER BY id DESC",
                        (metric_name, cutoff)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM metrics WHERE timestamp > ? ORDER BY id DESC",
                        (cutoff,)
                    ).fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def get_sync_queue(self) -> List[Dict]:
        """Get events pending sync to server."""
        with self._lock:
            return list(self._sync_queue)

    def clear_sync_queue(self):
        """Clear sync queue after successful sync."""
        with self._lock:
            self._sync_queue.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                errors = conn.execute("SELECT COUNT(*) FROM events WHERE level IN ('ERROR','CRITICAL')").fetchone()[0]
                today = datetime.now().strftime("%Y-%m-%d")
                today_count = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE timestamp LIKE ?",
                    (f"{today}%",)
                ).fetchone()[0]
                return {
                    "total_events": total,
                    "total_errors": errors,
                    "today_events": today_count,
                    "sync_pending": len(self._sync_queue),
                }
        except Exception:
            return {"total_events": 0, "total_errors": 0, "today_events": 0, "sync_pending": 0}

    # ============================================================
    # INTERNAL
    # ============================================================

    def _log(self, level: str, category: str, message: str,
             context: Dict, traceback_str: str = None):
        timestamp = datetime.now().isoformat()

        # Write to SQLite
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO events (timestamp, level, category, message, context, traceback) VALUES (?, ?, ?, ?, ?, ?)",
                    (timestamp, level, category, message, json.dumps(context), traceback_str)
                )
                conn.commit()
        except Exception:
            pass

        # Write to file
        try:
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] [{category}] {message}\n")
                if context:
                    f.write(f"  Context: {json.dumps(context, ensure_ascii=False)}\n")
                if traceback_str:
                    f.write(f"  Traceback: {traceback_str}\n")
        except Exception:
            pass

        # Queue for server sync (if online)
        with self._lock:
            self._sync_queue.append({
                "timestamp": timestamp,
                "level": level,
                "category": category,
                "message": message,
                "context": context,
            })

        # Print to console for development
        if level in ("ERROR", "CRITICAL"):
            print(f"[{level}] {category}: {message}")
        elif os.getenv("DJ_DEBUG"):
            print(f"[{level}] {category}: {message}")

    def cleanup_old_logs(self):
        """Remove log entries older than max_local_days."""
        try:
            cutoff = (datetime.now() - timedelta(days=self.max_local_days)).isoformat()
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
                conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
                conn.commit()
        except Exception:
            pass


# ============================================================
# SINGLETON
# ============================================================

_logger: Optional[DJLogger] = None


def get_logger() -> DJLogger:
    """Get or create the global logger."""
    global _logger
    if _logger is None:
        _logger = DJLogger()
    return _logger


# Import sys for traceback
import sys
