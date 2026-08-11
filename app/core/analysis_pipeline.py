"""
Analysis Pipeline — Async audio analysis with persistent SQLite cache.

Features:
- Job queue with ThreadPoolExecutor (configurable workers)
- Persistent cache keyed by file_hash + mtime + size
- Waveform, phrase points, hot cues pre-computed
- Progress callbacks for UI
- Batch processing with concurrency control
- Retry/fallback logic (librosa → ffmpeg → stdlib)
"""

import os
import sqlite3
import hashlib
import msgpack
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime


@dataclass
class TrackAnalysis:
    """Complete analysis result for a track."""
    # Identity
    file_hash: str
    path: str
    mtime: float
    size: int

    # Core audio
    bpm: float = 0.0
    key: str = ""
    camelot: str = ""
    duration: float = 0.0
    sample_rate: int = 44100

    # AI features
    energy: float = 0.5
    brightness: float = 0.5
    danceability: float = 0.5
    drop_strength: float = 0.0
    vocal_risk: float = 0.0
    stereo_width: float = 0.0
    phase_correlation: float = 0.0

    # Mix features
    intro_outro_mixability: float = 0.0
    role: str = "UTILITY"

    # Visual data (msgpack serialized in DB)
    waveform: List[float] = field(default_factory=list)
    phrase_points: List[Dict[str, Any]] = field(default_factory=list)
    hot_cues: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    engine: str = "UNKNOWN"
    analyzed_at: float = field(default_factory=lambda: datetime.now().timestamp())
    analysis_note: str = ""

    # Doctor report
    doctor_report: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage/transport."""
        return {
            "file_hash": self.file_hash,
            "path": self.path,
            "mtime": self.mtime,
            "size": self.size,
            "bpm": self.bpm,
            "key": self.key,
            "camelot": self.camelot,
            "duration": self.duration,
            "sample_rate": self.sample_rate,
            "energy": self.energy,
            "brightness": self.brightness,
            "danceability": self.danceability,
            "drop_strength": self.drop_strength,
            "vocal_risk": self.vocal_risk,
            "stereo_width": self.stereo_width,
            "phase_correlation": self.phase_correlation,
            "intro_outro_mixability": self.intro_outro_mixability,
            "role": self.role,
            "waveform": self.waveform,
            "phrase_points": self.phrase_points,
            "hot_cues": self.hot_cues,
            "engine": self.engine,
            "analyzed_at": self.analyzed_at,
            "analysis_note": self.analysis_note,
            "doctor_report": self.doctor_report,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "TrackAnalysis":
        """Reconstruct from database row."""
        return cls(
            file_hash=row["file_hash"],
            path=row["path"],
            mtime=row["mtime"],
            size=row["size"],
            bpm=row["bpm"] or 0.0,
            key=row["key"] or "",
            camelot=row["camelot"] or "",
            duration=row["duration"] or 0.0,
            sample_rate=row["sample_rate"] or 44100,
            energy=row["energy"] or 0.5,
            brightness=row["brightness"] or 0.5,
            danceability=row["danceability"] or 0.5,
            drop_strength=row["drop_strength"] or 0.0,
            vocal_risk=row["vocal_risk"] or 0.0,
            stereo_width=row["stereo_width"] or 0.0,
            phase_correlation=row["phase_correlation"] or 0.0,
            intro_outro_mixability=row["intro_outro_mixability"] or 0.0,
            role=row["role"] or "UTILITY",
            waveform=msgpack.unpackb(row["waveform"], raw=False) if row["waveform"] else [],
            phrase_points=msgpack.unpackb(row["phrase_points"], raw=False) if row["phrase_points"] else [],
            hot_cues=msgpack.unpackb(row["hot_cues"], raw=False) if row["hot_cues"] else [],
            engine=row["engine"] or "UNKNOWN",
            analyzed_at=row["analyzed_at"] or 0.0,
            analysis_note=row["analysis_note"] or "",
            doctor_report=msgpack.unpackb(row["doctor_report"], raw=False) if row["doctor_report"] else {},
        )


class AnalysisPipeline:
    """
    Async analysis pipeline with persistent SQLite cache.

    Usage:
        pipeline = AnalysisPipeline(cache_path="data/analysis.db", max_workers=4)

        # Single track
        result = await pipeline.analyze(Path("track.mp3"))

        # Batch with progress
        results = await pipeline.analyze_batch(
            [Path("a.mp3"), Path("b.mp3")],
            progress_cb=lambda done, total: print(f"{done}/{total}")
        )
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS analysis_cache (
        file_hash TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        mtime REAL NOT NULL,
        size INTEGER NOT NULL,
        bpm REAL,
        key TEXT,
        camelot TEXT,
        duration REAL,
        sample_rate INTEGER,
        energy REAL,
        brightness REAL,
        danceability REAL,
        drop_strength REAL,
        vocal_risk REAL,
        stereo_width REAL,
        phase_correlation REAL,
        intro_outro_mixability REAL,
        role TEXT,
        waveform BLOB,
        phrase_points BLOB,
        hot_cues BLOB,
        engine TEXT,
        analyzed_at REAL,
        analysis_note TEXT,
        doctor_report BLOB
    );
    CREATE INDEX IF NOT EXISTS idx_cache_path ON analysis_cache(path);
    CREATE INDEX IF NOT EXISTS idx_cache_bpm ON analysis_cache(bpm);
    CREATE INDEX IF NOT EXISTS idx_cache_camelot ON analysis_cache(camelot);
    CREATE INDEX IF NOT EXISTS idx_cache_energy ON analysis_cache(energy);
    """

    def __init__(
        self,
        cache_path: str = "data/analysis.db",
        max_workers: int = 4,
        sample_rate: int = 44100,
        max_duration: int = 420,
    ):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.sample_rate = sample_rate
        self.max_duration = max_duration

        self._executor: Optional[ThreadPoolExecutor] = None
        self._init_db()
        self._local_engine = None  # Lazy init MixMasterEngine

    def _init_db(self):
        with sqlite3.connect(self.cache_path) as conn:
            conn.executescript(self.SCHEMA)
            conn.commit()

    def _get_engine(self):
        """Lazy-load MixMasterEngine (heavy imports)."""
        if self._local_engine is None:
            from app.ai.mix_master_engine import MixMasterEngine
            self._local_engine = MixMasterEngine(
                sample_rate=self.sample_rate,
                max_duration=self.max_duration
            )
        return self._local_engine

    def _compute_file_hash(self, path: Path) -> str:
        """Fast hash: first 64KB + last 64KB + size + mtime."""
        stat = path.stat()
        hasher = hashlib.blake2b(digest_size=16)
        hasher.update(str(stat.st_size).encode())
        hasher.update(str(int(stat.st_mtime)).encode())

        with open(path, "rb") as f:
            # First 64KB
            hasher.update(f.read(65536))
            # Last 64KB
            f.seek(max(0, stat.st_size - 65536))
            hasher.update(f.read(65536))

        return hasher.hexdigest()

    def _check_cache(self, path: Path) -> Optional[TrackAnalysis]:
        """Check if valid cached analysis exists."""
        try:
            stat = path.stat()
            file_hash = self._compute_file_hash(path)

            with sqlite3.connect(self.cache_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM analysis_cache WHERE file_hash = ? AND mtime = ? AND size = ?",
                    (file_hash, stat.st_mtime, stat.st_size)
                ).fetchone()

                if row:
                    return TrackAnalysis.from_row(row)
        except Exception:
            pass
        return None

    def _store_cache(self, analysis: TrackAnalysis):
        """Store analysis result in cache."""
        try:
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO analysis_cache (
                        file_hash, path, mtime, size,
                        bpm, key, camelot, duration, sample_rate,
                        energy, brightness, danceability, drop_strength,
                        vocal_risk, stereo_width, phase_correlation,
                        intro_outro_mixability, role,
                        waveform, phrase_points, hot_cues,
                        engine, analyzed_at, analysis_note, doctor_report
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        analysis.file_hash,
                        analysis.path,
                        analysis.mtime,
                        analysis.size,
                        analysis.bpm,
                        analysis.key,
                        analysis.camelot,
                        analysis.duration,
                        analysis.sample_rate,
                        analysis.energy,
                        analysis.brightness,
                        analysis.danceability,
                        analysis.drop_strength,
                        analysis.vocal_risk,
                        analysis.stereo_width,
                        analysis.phase_correlation,
                        analysis.intro_outro_mixability,
                        analysis.role,
                        msgpack.packb(analysis.waveform),
                        msgpack.packb(analysis.phrase_points),
                        msgpack.packb(analysis.hot_cues),
                        analysis.engine,
                        analysis.analyzed_at,
                        analysis.analysis_note,
                        msgpack.packb(analysis.doctor_report),
                    )
                )
                conn.commit()
        except Exception as e:
            print(f"[CACHE WRITE ERROR] {analysis.path}: {e}")

    def _analyze_sync(self, path: Path) -> TrackAnalysis:
        """Synchronous analysis (runs in thread pool)."""
        engine = self._get_engine()
        result = engine.analyze_file(str(path))

        if not result.get("ok"):
            # Return minimal fallback
            return TrackAnalysis(
                file_hash=self._compute_file_hash(path),
                path=str(path),
                mtime=path.stat().st_mtime,
                size=path.stat().st_size,
                engine="FAILED",
                analysis_note=result.get("reason", "UNKNOWN_ERROR"),
            )

        # Build TrackAnalysis from engine result
        transient = result.get("transient", {})
        spectrum = result.get("spectrum", {})
        dynamics = result.get("dynamics", {})
        stereo = result.get("stereo", {})

        # Extract waveform and phrase points
        waveform = result.get("waveform", [])
        phrase_points = result.get("phrase_points", [])

        # Generate hot cues from phrase points
        hot_cues = self._generate_hot_cues(phrase_points, result.get("duration", 0))

        return TrackAnalysis(
            file_hash=self._compute_file_hash(path),
            path=str(path),
            mtime=path.stat().st_mtime,
            size=path.stat().st_size,
            bpm=transient.get("tempo", 0.0) or 0.0,
            key=result.get("key", ""),
            camelot=result.get("camelot", ""),
            duration=result.get("duration", 0.0),
            sample_rate=result.get("sample_rate", self.sample_rate),
            energy=dynamics.get("energy", 0.5),
            brightness=spectrum.get("brightness", 0.5),
            danceability=transient.get("groove_confidence", 0.5),
            drop_strength=transient.get("punch", 0.0),
            vocal_risk=spectrum.get("mid_presence", 0.0),
            stereo_width=stereo.get("width", 0.0),
            phase_correlation=stereo.get("correlation", 0.0),
            intro_outro_mixability=dynamics.get("dynamic_range_score", 0.0),
            role="PEAK TIME" if dynamics.get("energy", 0) > 0.72 else "GROOVE",
            waveform=waveform,
            phrase_points=phrase_points,
            hot_cues=hot_cues,
            engine=result.get("engine", "UNKNOWN"),
            analysis_note=result.get("analysis_note", ""),
            doctor_report=result.get("doctor", {}),
        )

    def _generate_hot_cues(self, phrase_points: List[Dict], duration: float) -> List[Dict]:
        """Generate hot cue suggestions from phrase points."""
        cues = []
        colors = {
            "START": "#00FFA3",   # neon green
            "BUILD": "#FFB020",   # amber
            "PEAK": "#FF3DF2",    # magenta
            "DROP": "#22D3FF",    # cyan
            "BREAK": "#9B5CFF",   # purple
            "OUTRO": "#FF4D6D",   # red
        }
        for i, point in enumerate(phrase_points[:8]):  # Max 8 hot cues
            label = str(point.get("label", f"CUE{i+1}")).upper()
            pos = float(point.get("position", 0))
            cues.append({
                "index": i,
                "label": label,
                "position": pos,
                "time": round(duration * pos, 2),
                "color": colors.get(label, "#00FFA3"),
            })
        return cues

    # ============================================================
    # PUBLIC API
    # ============================================================

    def analyze(self, path: Path) -> TrackAnalysis:
        """Synchronous single-track analysis (blocking)."""
        # Check cache first
        cached = self._check_cache(path)
        if cached:
            return cached

        # Analyze
        result = self._analyze_sync(path)
        self._store_cache(result)
        return result

    async def analyze_async(self, path: Path) -> TrackAnalysis:
        """Async single-track analysis."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._get_executor(), self.analyze, path)

    def _get_executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    async def analyze_batch(
        self,
        paths: List[Path],
        progress_cb: Optional[Callable[[int, int], None]] = None,
        skip_cached: bool = True,
    ) -> List[TrackAnalysis]:
        """
        Analyze multiple tracks with progress callback.

        Args:
            paths: List of audio file paths
            progress_cb: Callback(done, total) called after each completion
            skip_cached: If True, return cached results immediately without re-analyzing

        Returns:
            List of TrackAnalysis in same order as input paths
        """
        if not paths:
            return []

        # Phase 1: Check cache for all
        results: Dict[int, TrackAnalysis] = {}
        to_analyze: List[tuple[int, Path]] = []

        for idx, path in enumerate(paths):
            if skip_cached:
                cached = self._check_cache(path)
                if cached:
                    results[idx] = cached
                    continue
            to_analyze.append((idx, path))

        # Phase 2: Analyze missing in parallel
        total = len(to_analyze)
        done = len(results)

        if progress_cb:
            progress_cb(done, len(paths))

        if total == 0:
            return [results[i] for i in range(len(paths))]

        # Submit all jobs
        executor = self._get_executor()
        future_to_idx = {
            executor.submit(self._analyze_sync, path): idx
            for idx, path in to_analyze
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                self._store_cache(result)
                results[idx] = result
            except Exception as e:
                # Create error result
                path = to_analyze[[i for i, p in to_analyze if p == path][0]][1]
                results[idx] = TrackAnalysis(
                    file_hash=self._compute_file_hash(path),
                    path=str(path),
                    mtime=path.stat().st_mtime,
                    size=path.stat().st_size,
                    engine="ERROR",
                    analysis_note=str(e),
                )

            done += 1
            if progress_cb:
                progress_cb(done, len(paths))

        # Return in original order
        return [results[i] for i in range(len(paths))]

    def analyze_batch_sync(
        self,
        paths: List[Path],
        progress_cb: Optional[Callable[[int, int], None]] = None,
        skip_cached: bool = True,
    ) -> List[TrackAnalysis]:
        """Synchronous batch analysis (blocks until done)."""
        # Check cache first
        results: Dict[int, TrackAnalysis] = {}
        to_analyze: List[tuple[int, Path]] = []

        for idx, path in enumerate(paths):
            if skip_cached:
                cached = self._check_cache(path)
                if cached:
                    results[idx] = cached
                    continue
            to_analyze.append((idx, path))

        total = len(to_analyze)
        done = len(results)

        if progress_cb:
            progress_cb(done, len(paths))

        if total == 0:
            return [results[i] for i in range(len(paths))]

        executor = self._get_executor()
        future_to_idx = {
            executor.submit(self._analyze_sync, path): idx
            for idx, path in to_analyze
        }

        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                self._store_cache(result)
                results[idx] = result
            except Exception as e:
                path = to_analyze[[i for i, p in to_analyze if p == path][0]][1]
                results[idx] = TrackAnalysis(
                    file_hash=self._compute_file_hash(path),
                    path=str(path),
                    mtime=path.stat().st_mtime,
                    size=path.stat().st_size,
                    engine="ERROR",
                    analysis_note=str(e),
                )

            done += 1
            if progress_cb:
                progress_cb(done, len(paths))

        return [results[i] for i in range(len(paths))]

    # ============================================================
    # CACHE MANAGEMENT
    # ============================================================

    def clear_cache(self, older_than_days: Optional[int] = None):
        """Clear cache entries."""
        with sqlite3.connect(self.cache_path) as conn:
            if older_than_days:
                cutoff = datetime.now().timestamp() - (older_than_days * 86400)
                conn.execute(
                    "DELETE FROM analysis_cache WHERE analyzed_at < ?",
                    (cutoff,)
                )
            else:
                conn.execute("DELETE FROM analysis_cache")
            conn.commit()

    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.cache_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count, SUM(size) as total_size FROM analysis_cache"
            ).fetchone()
            return {
                "entries": row[0] or 0,
                "total_size_bytes": row[1] or 0,
                "cache_path": str(self.cache_path),
            }

    def get_cached_tracks(
        self,
        min_bpm: Optional[float] = None,
        max_bpm: Optional[float] = None,
        camelot: Optional[str] = None,
        min_energy: Optional[float] = None,
        limit: int = 1000,
    ) -> List[TrackAnalysis]:
        """Query cached tracks with filters (fast, no re-analysis)."""
        query = "SELECT * FROM analysis_cache WHERE 1=1"
        params = []

        if min_bpm is not None:
            query += " AND bpm >= ?"
            params.append(min_bpm)
        if max_bpm is not None:
            query += " AND bpm <= ?"
            params.append(max_bpm)
        if camelot:
            query += " AND camelot = ?"
            params.append(camelot)
        if min_energy is not None:
            query += " AND energy >= ?"
            params.append(min_energy)

        query += " ORDER BY analyzed_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.cache_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [TrackAnalysis.from_row(row) for row in rows]

    def shutdown(self):
        """Clean shutdown of thread pool."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

_default_pipeline: Optional[AnalysisPipeline] = None


def get_pipeline(
    cache_path: str = "data/analysis.db",
    max_workers: int = 4,
) -> AnalysisPipeline:
    """Get or create default pipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = AnalysisPipeline(cache_path, max_workers)
    return _default_pipeline


async def analyze_tracks(
    paths: List[Path],
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> List[TrackAnalysis]:
    """Quick async batch analysis using default pipeline."""
    pipeline = get_pipeline()
    return await pipeline.analyze_batch(paths, progress_cb)


def analyze_tracks_sync(
    paths: List[Path],
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> List[TrackAnalysis]:
    """Quick sync batch analysis using default pipeline."""
    pipeline = get_pipeline()
    return pipeline.analyze_batch_sync(paths, progress_cb)