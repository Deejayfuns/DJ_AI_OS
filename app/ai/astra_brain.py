"""
DJ AI OS — Astra Brain (Central Intelligence)

The unified AI brain that connects ALL modules:
- Music Intelligence (BPM, key, energy)
- Beat Grid Engine (beat detection)
- Stem Engine (vocal/instrumental separation)
- Audio Quality (clipping, dynamic range)
- Set Flow AI (set optimization)
- DJ Brain (emotional analysis)
- Track Analyzer (DNA, similarity, profile)

Astra speaks through this brain.
Every command routes through here.
"""

import os
from typing import Dict, List, Any, Optional

from app.core.paths import get_exports_dir


class AstraBrain:
    """
    Central intelligence hub — the brain behind Astra AI assistant.
    Connects all analysis modules into one unified interface.
    """

    def __init__(self):
        # Lazy-load modules (heavy imports)
        self._music_intelligence = None
        self._beat_grid = None
        self._stem_engine = None
        self._audio_quality = None
        self._set_flow = None
        self._dj_brain = None
        self._track_analyzer = None

    @property
    def music_intelligence(self):
        if self._music_intelligence is None:
            from app.ai.music_intelligence import MusicIntelligence
            self._music_intelligence = MusicIntelligence()
        return self._music_intelligence

    @property
    def beat_grid(self):
        if self._beat_grid is None:
            from app.ai.beat_grid_engine import BeatGridEngine
            self._beat_grid = BeatGridEngine()
        return self._beat_grid

    @property
    def stem_engine(self):
        if self._stem_engine is None:
            from app.ai.stem_engine import StemEngine
            self._stem_engine = StemEngine()
        return self._stem_engine

    @property
    def audio_quality(self):
        if self._audio_quality is None:
            from app.ai.audio_quality import AudioQuality
            self._audio_quality = AudioQuality()
        return self._audio_quality

    @property
    def set_flow(self):
        if self._set_flow is None:
            from app.ai.set_flow_ai import SetFlowAI
            self._set_flow = SetFlowAI()
        return self._set_flow

    @property
    def dj_brain(self):
        if self._dj_brain is None:
            from app.ai.dj_brain import DJBrain
            self._dj_brain = DJBrain()
        return self._dj_brain

    @property
    def track_analyzer(self):
        if self._track_analyzer is None:
            from app.ai.track_analyzer import TrackAnalyzer
            self._track_analyzer = TrackAnalyzer()
        return self._track_analyzer

    # ============================================================
    # UNIFIED COMMAND INTERFACE
    # ============================================================

    def process_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process any natural language command through the unified brain.

        Routes to the appropriate module based on intent.
        Logs all actions for telemetry and debugging.
        """
        cmd = command.lower().strip()
        context = context or {}

        # Log the command
        try:
            from app.core.logger import get_logger
            log = get_logger()
            log.info(f"ASTRA COMMAND: {command}", category="astra")
        except Exception:
            pass

        # ============================================================
        # GENERATE COMMANDS (check BEFORE analysis)
        # ============================================================
        if any(w in cmd for w in ["beat yap", "uret", "generate", "create"]):
            return self._handle_generate(cmd, context)

        # ============================================================
        # ANALYSIS COMMANDS
        # ============================================================
        if any(w in cmd for w in ["analyze", "analiz", "tara", "scan"]):
            return self._handle_analyze(cmd, context)

        if any(w in cmd for w in ["quality", "kalite", "ses", "audio"]):
            return self._handle_quality(cmd, context)

        # ============================================================
        # BEAT GRID COMMANDS
        # ============================================================
        if any(w in cmd for w in ["grid", "downbeat", "beat grid"]):
            return self._handle_beat(cmd, context)

        # ============================================================
        # BPM COMMANDS (only for file analysis, not generation)
        # ============================================================
        if any(w in cmd for w in ["bpm", "tempo", "ritim"]) and "yap" not in cmd:
            return self._handle_bpm(cmd, context)

        if any(w in cmd for w in ["key", "ton", "camelot", "harmonic", "karis", "uyum"]):
            return self._handle_key(cmd, context)

        # ============================================================
        # STEM COMMANDS
        # ============================================================
        if any(w in cmd for w in ["vocal", "ayir", "separate", "stem", "drums", "bass"]):
            return self._handle_stem(cmd, context)

        # ============================================================
        # SET COMMANDS
        # ============================================================
        if any(w in cmd for w in ["set", "mix", "playlist", "optimize", "sirala"]):
            return self._handle_set(cmd, context)

        # ============================================================
        # SIMILARITY COMMANDS
        # ============================================================
        if any(w in cmd for w in ["similar", "benzer", "like", "ayni"]):
            return self._handle_similar(cmd, context)

        # ============================================================
        # COACHING COMMANDS
        # ============================================================
        if any(w in cmd for w in ["coach", "coaching", "feedback", "degerlendir"]):
            return self._handle_coaching(cmd, context)

        # ============================================================
        # LIBRARY COMMANDS
        # ============================================================
        if any(w in cmd for w in ["library", "arsiv", "kutuphane", "health", "saglik"]):
            return self._handle_library(cmd, context)

        # ============================================================
        # GENERATE COMMANDS
        # ============================================================
        if any(w in cmd for w in ["beat yap", "uret", "generate", "create"]):
            return self._handle_generate(cmd, context)

        return {
            "action": "unknown",
            "reply": (
                "Komut anlayamadim. Soyleyebilecegin seyler:\n"
                "- 'Bu parcayi analiz et'\n"
                "- '128 BPM house beat yap'\n"
                "- 'Vocal'lari ayir'\n"
                "- 'Seti optimize et'\n"
                "- 'Kalite kontrolu yap'\n"
                "- 'Bu parcaya benzer olanlari bul'\n"
                "- 'Setimi degerlendir'\n"
            ),
        }

    # ============================================================
    # HANDLERS
    # ============================================================

    def _handle_analyze(self, cmd, context):
        track = context.get("track")
        path = context.get("path")

        if path:
            result = self.music_intelligence.analyze_file(path)
            return {
                "action": "analysis",
                "result": result,
                "reply": (
                    f"BPM: {result.get('bpm', '?')} | "
                    f"Key: {result.get('key', '?')} ({result.get('camelot', '?')}) | "
                    f"Energy: {result.get('energy', 0):.0%} | "
                    f"Mood: {result.get('mood', '?')}"
                ),
            }

        if track:
            # Analyze from metadata
            result = {
                "bpm": track.get("bpm", 0),
                "key": track.get("key", ""),
                "camelot": track.get("camelot", ""),
                "energy": track.get("energy", 0.5),
                "mood": self.dj_brain.analyze_track(track).get("emotional_color", "unknown"),
            }
            return {"action": "analysis", "result": result, "reply": f"Metadata analizi: {result}"}

        return {"action": "error", "reply": "Analiz edilecek dosya veya parca gerekli."}

    def _handle_bpm(self, cmd, context):
        path = context.get("path")
        if path:
            result = self.music_intelligence.analyze_file(path)
            return {
                "action": "bpm_detection",
                "result": {"bpm": result.get("bpm"), "stability": result.get("tempo_stability")},
                "reply": f"BPM: {result.get('bpm', '?')} (stabilite: {result.get('tempo_stability', 0):.0%})",
            }
        return {"action": "error", "reply": "BPM icin dosya gerekli."}

    def _handle_key(self, cmd, context):
        # Check for two keys to compare
        import re
        keys = re.findall(r"\d{1,2}[AB]", cmd.upper())
        if len(keys) >= 2:
            result = self.music_intelligence.key_compatibility(keys[0], keys[1])
            return {
                "action": "key_compatibility",
                "result": result,
                "reply": f"{keys[0]} <-> {keys[1]}: {'Uyumlu' if result['compatible'] else 'Uzak'} ({result['advice']})",
            }

        path = context.get("path")
        if path:
            result = self.music_intelligence.analyze_file(path)
            return {
                "action": "key_detection",
                "result": {"key": result.get("key"), "camelot": result.get("camelot"), "confidence": result.get("key_confidence")},
                "reply": f"Key: {result.get('key', '?')} (Camelot: {result.get('camelot', '?')}, guven: {result.get('key_confidence', 0):.0%})",
            }

        return {"action": "error", "reply": "Key analizi icin dosya veya iki Camelot tani gerekli."}

    def _handle_quality(self, cmd, context):
        path = context.get("path")
        if path:
            import numpy as np
            try:
                y, sr = __import__("librosa").load(path, sr=22050, mono=False, duration=180)
                result = self.audio_quality.analyze(y, sr)
                return {
                    "action": "quality_check",
                    "result": result,
                    "reply": f"Ses kalitesi: {result['score']}/100 ({result['grade']}) | Sorunlar: {len(result['issues'])}",
                }
            except Exception as e:
                return {"action": "error", "reply": f"Kalite analizi hatasi: {e}"}

        return {"action": "error", "reply": "Kalite kontrolu icin dosya gerekli."}

    def _handle_beat(self, cmd, context):
        path = context.get("path")
        if path:
            import numpy as np
            try:
                y, sr = __import__("librosa").load(path, sr=22050, mono=True, duration=180)
                result = self.beat_grid.analyze_beat_grid(y, sr)
                return {
                    "action": "beat_grid",
                    "result": result,
                    "reply": (
                        f"Beat Grid: {result['bpm']} BPM | "
                        f"{result['beat_count']} beat | "
                        f"{result['downbeat_count']} downbeat | "
                        f"{result['time_signature']} | "
                        f"Stabilite: {result['tempo_stability']:.0%}"
                    ),
                }
            except Exception as e:
                return {"action": "error", "reply": f"Beat grid hatasi: {e}"}

        return {"action": "error", "reply": "Beat grid analizi icin dosya gerekli."}

    def _handle_stem(self, cmd, context):
        path = context.get("path")
        if not path:
            return {"action": "error", "reply": "Stem ayirma icin dosya gerekli."}

        # Determine which stems to extract
        stems = ["vocals", "drums", "bass", "other"]
        if "vocal" in cmd:
            stems = ["vocals"]
        elif "drum" in cmd or "davul" in cmd:
            stems = ["drums"]
        elif "bass" in cmd:
            stems = ["bass"]

        result = self.stem_engine.separate(path, stems)
        if "error" in result:
            return {"action": "error", "reply": f"Stem hatasi: {result['error']}"}

        # Export
        output_dir = os.path.join(str(get_exports_dir()), "stems")
        paths = self.stem_engine.export_stems(result, output_dir)

        return {
            "action": "stem_separation",
            "result": result,
            "paths": paths,
            "reply": f"Stem'ler ayirildi ({result.get('engine', '?')}): {', '.join(paths.keys())} -> {output_dir}",
        }

    def _handle_set(self, cmd, context):
        tracks = context.get("tracks", [])
        if not tracks:
            return {"action": "error", "reply": "Set optimizasyonu icin parca listesi gerekli."}

        # Parse duration
        import re
        hours = 2
        m = re.search(r"(\d+)\s*(?:saat|hour|s)", cmd)
        if m:
            hours = int(m.group(1))

        # Parse style
        style = "classic"
        if "peak" in cmd or "zirve" in cmd:
            style = "peak_first"
        elif "journey" in cmd or "yolculuk" in cmd:
            style = "journey"
        elif "wedding" in cmd or "dugun" in cmd:
            style = "wedding"

        result = self.set_flow.optimize_set(tracks, duration_minutes=hours * 60, style=style)

        return {
            "action": "set_optimization",
            "result": result,
            "reply": (
                f"Set optimize edildi: {len(result['tracks'])} parca, "
                f"stil: {style}, "
                f"ortalama enerji: {result['avg_energy']:.0%}"
            ),
        }

    def _handle_similar(self, cmd, context):
        track = context.get("track")
        library = context.get("library", [])

        if not track or not library:
            return {"action": "error", "reply": "Benzerlik icin referans parca ve kutuphane gerekli."}

        similar = self.track_analyzer.find_similar(track, library, limit=5)
        return {
            "action": "similarity",
            "result": similar,
            "reply": f"{len(similar)} benzer parca bulundu: " + ", ".join(
                t.get("name", "?")[:20] for t in similar[:3]
            ),
        }

    def _handle_coaching(self, cmd, context):
        tracks = context.get("tracks", [])
        venue = context.get("venue", "CLUB")
        hours = context.get("hours", 4)

        if not tracks:
            return {"action": "error", "reply": "Coaching icin set verisi gerekli."}

        result = self.dj_brain.analyze_set(tracks, venue=venue, hours=hours)
        return {
            "action": "coaching",
            "result": result,
            "reply": f"Set skoru: {result['score']}/100 | Sorunlar: {len(result['issues'])} | Tavsiye: {result['advice'][:80]}",
        }

    def _handle_library(self, cmd, context):
        tracks = context.get("library", [])
        if not tracks:
            return {"action": "error", "reply": "Kutuphane bilgisi gerekli."}

        if "health" in cmd or "saglik" in cmd:
            from app.ai.library_ai import LibraryAI
            ai = LibraryAI(tracks)
            health = ai.health_report()
            return {
                "action": "health",
                "result": health,
                "reply": f"Kutuphane sagligi: {health['score']}/100 | Tur: {health.get('unique_genres', 0)} | Ton: {health.get('unique_keys', 0)}",
            }

        return {"action": "error", "reply": "Kutuphane komutu anlayamadim."}

    def _handle_generate(self, cmd, context):
        from app.ai.beat_studio import BeatStudio
        studio = BeatStudio()
        result = studio.generate(cmd)
        return {
            "action": "beat_generated",
            "result": result,
            "reply": f"Beat uretildi: {result['genre']} @ {result['bpm']} BPM, {result['bars']} bar, {result['duration']:.1f}s",
        }

    # ============================================================
    # STATUS
    # ============================================================

    def get_status(self) -> Dict[str, Any]:
        """Get status of all brain modules."""
        return {
            "music_intelligence": "ready" if self._music_intelligence else "idle",
            "beat_grid": "ready" if self._beat_grid else "idle",
            "stem_engine": "ready" if self._stem_engine else "idle",
            "audio_quality": "ready" if self._audio_quality else "idle",
            "set_flow": "ready" if self._set_flow else "idle",
            "dj_brain": "ready" if self._dj_brain else "idle",
            "track_analyzer": "ready" if self._track_analyzer else "idle",
        }
