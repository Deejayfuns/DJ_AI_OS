"""
DJ AI OS — Style Scene (Astra-managed setup scene)

Astra's handle on a live-performance setup. A scene is a curated list of
tracks; Astra "listens" to each one (analyzes it) and writes a fresh beat
style for it. The DJ can then play through the scene, each track swapping
the engine to its generated style.

This module is code-driven — Astra calls the methods directly, no UI needed.
The LivePerformancePanel can mount the same scene for manual control.

Usage (Astra / scripts):
    scene = StyleScene(sample_rate=44100)
    scene.add_track(r"C:/Music/track1.mp3")
    scene.add_track(r"C:/Music/track2.mp3")
    scene.build()                       # analyze all (background)
    scene.wait()                        # block until done
    scene.play_index(0)                 # mount style 0 onto the engine
    scene.next() / scene.prev()
    scene.current_summary()
"""

import os
import threading

from .style_generator import StyleGenerator, describe_style


class StyleScene:
    """Ordered list of tracks with their generated styles."""

    def __init__(self, sample_rate=44100):
        self.sr = sample_rate
        self._entries = []       # list of dict: {path, name, style, analysis, error}
        self._generator = StyleGenerator(sample_rate=sample_rate)
        self._engine = None
        self._current = -1
        self._build_thread = None
        self._lock = threading.Lock()

    # ============================================================
    # TRACK MANAGEMENT
    # ============================================================

    def add_track(self, path):
        """Add a track to the scene (not yet analyzed)."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self._entries.append({
            "path": path,
            "name": os.path.basename(path),
            "style": None,
            "analysis": None,
            "error": None,
        })

    def add_folder(self, folder, recursive=True):
        """Add all audio files from a folder."""
        exts = (".mp3", ".wav", ".flac", ".m4a", ".aiff", ".aif", ".ogg")
        added = 0
        if recursive:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(exts):
                        self.add_track(os.path.join(root, f))
                        added += 1
        else:
            for f in os.listdir(folder):
                p = os.path.join(folder, f)
                if os.path.isfile(p) and f.lower().endswith(exts):
                    self.add_track(p)
                    added += 1
        return added

    def tracks(self):
        """Read-only track list."""
        return [dict(e, style=e["style"]) for e in self._entries]

    def analyzed_count(self):
        return sum(1 for e in self._entries if e["style"] is not None)

    def failed_count(self):
        return sum(1 for e in self._entries if e["error"])

    def is_ready(self):
        return bool(self._entries) and self.analyzed_count() == len(self._entries)

    # ============================================================
    # ANALYSIS
    # ============================================================

    def build(self, on_progress=None, on_done=None):
        """
        Analyze every un-analyzed track in the background.
        on_progress(idx, total, name) and on_done(scene) fire on worker thread —
        UI callers should marshal with .after().
        """
        targets = [i for i, e in enumerate(self._entries) if e["style"] is None]
        total = len(self._entries)

        def _work():
            for idx in targets:
                e = self._entries[idx]
                try:
                    analysis = self._generator.analyze_file(e["path"])
                    style = self._generator.generate(analysis)
                    with self._lock:
                        e["analysis"] = analysis
                        e["style"] = style
                except Exception as exc:
                    with self._lock:
                        e["error"] = str(exc)
                if on_progress:
                    on_progress(idx, total, e["name"])
            if on_done:
                on_done(self)

        self._build_thread = threading.Thread(target=_work, daemon=True)
        self._build_thread.start()
        return self._build_thread

    def wait(self, timeout=None):
        if self._build_thread:
            self._build_thread.join(timeout=timeout)

    # ============================================================
    # PLAYBACK HANDLE
    # ============================================================

    def mount_engine(self, engine):
        """Attach a LivePerformanceEngine that scenes swap styles onto."""
        self._engine = engine

    def play_index(self, idx):
        """Load style[idx] onto the attached engine. Returns summary or None."""
        if not (0 <= idx < len(self._entries)):
            return None
        e = self._entries[idx]
        if e["style"] is None:
            return None
        if self._engine is None:
            raise RuntimeError("StyleScene: no engine mounted (mount_engine)")
        style = e["style"]
        new_engine = self._generator.build_engine(style=style)
        # hand over state
        self._engine.channels = new_engine.channels
        self._engine.order = new_engine.order
        self._engine.bpm = new_engine.bpm
        self._engine.swing = new_engine.swing
        self._current = idx
        return self.current_summary()

    def next(self):
        if self._current + 1 < len(self._entries):
            return self.play_index(self._current + 1)
        return None

    def prev(self):
        if self._current > 0:
            return self.play_index(self._current - 1)
        return None

    def current_index(self):
        return self._current

    def current_summary(self):
        """Human-readable summary of the current track's style."""
        if not (0 <= self._current < len(self._entries)):
            return ""
        e = self._entries[self._current]
        if e["style"] is None:
            return f"{e['name']}: analiz edilmedi"
        return f"[{self._current + 1}/{len(self._entries)}] {e['name']} — {describe_style(e['style'])}"
