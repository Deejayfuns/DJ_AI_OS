"""
DJ AI OS — Voice-to-Beat Pipeline

Connects voice commands → BeatStudio → Library AI → Stem Separator → Export.
The unified AI interface for beat generation and music production.

Usage:
    engine = VoiceBeatEngine()
    result = engine.process_command("128 BPM house beat yap")
    engine.process_command("kickleri daha sert yap")
    engine.process_command("WAV olarak kaydet")
"""

import os
import re
import threading
from typing import Dict, Any, Optional, List

from app.ai.beat_studio import BeatStudio
from app.ai.library_ai import LibraryAI
from app.core.stem_separator import StemSeparator


class VoiceBeatEngine:
    """
    Unified voice/beat production pipeline.
    Parses natural language commands and executes them.
    """

    def __init__(self):
        self.beat_studio = BeatStudio()
        self.stem_separator = StemSeparator(method="auto")
        self.library_ai = None  # Initialized when library is loaded
        self.last_beat = None
        self.last_separation = None
        self.last_library = None
        self.output_dir = "DJ_EXPORTS"

    def load_library(self, tracks):
        """Load track library for library AI features."""
        self.library_ai = LibraryAI(tracks)
        self.last_library = tracks

    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language command.

        Returns: dict with action, result, reply
        """
        cmd = command.lower().strip()

        # ============================================================
        # BEAT MODIFICATION (check BEFORE generation)
        # ============================================================
        if self.last_beat and any(w in cmd for w in ["sert", "hard", "soft", "yavas", "hizli", "daha", "change"]):
            return self._handle_modify_command(cmd)

        # ============================================================
        # BEAT GENERATION
        # ============================================================
        if any(w in cmd for w in ["beat", "ritim", "davul", "yap", "uret", "generate", "make", "create"]):
            return self._handle_beat_command(cmd)

        # ============================================================
        # EXPORT
        # ============================================================
        if any(w in cmd for w in ["kaydet", "export", "wav", "save", "disari"]):
            return self._handle_export_command(cmd)

        # ============================================================
        # STEM SEPARATION
        # ============================================================
        if any(w in cmd for w in ["vocal", "ayir", "separate", "stem", "isolate"]):
            return self._handle_stem_command(cmd)

        # ============================================================
        # LIBRARY COMMANDS
        # ============================================================
        if any(w in cmd for w in ["library", "arsiv", "kutuphane", "analyze", "saglik"]):
            return self._handle_library_command(cmd)

        # ============================================================
        # SET GENERATION
        # ============================================================
        if any(w in cmd for w in ["set", "mix", "playlist", "akisi", "flow"]):
            return self._handle_set_command(cmd)

        # ============================================================
        # KEY COMPATIBILITY
        # ============================================================
        if any(w in cmd for w in ["key", "ton", "camelot", "karis", "mix", "compatible"]):
            return self._handle_key_command(cmd)

        # Unknown command
        return {
            "action": "unknown",
            "reply": (
                "Komut anlayamadim. Soyleyebilecegin seyler:\n"
                "- '128 BPM tech house beat yap'\n"
                "- 'kickleri daha sert yap'\n"
                "- 'WAV olarak kaydet'\n"
                "- 'vocal'ı ayir'\n"
                "- 'arsiv sagligini goster'\n"
                "- 'set olustur'\n"
                "- '8A ile hangi tonlar karisir'"
            ),
        }

    def _handle_beat_command(self, cmd):
        """Generate a beat from command."""
        # Extract parameters
        bars = 4
        if m := re.search(r"(\d+)\s*bar", cmd):
            bars = int(m.group(1))
            bars = max(1, min(16, bars))

        result = self.beat_studio.generate(cmd, bars=bars)
        self.last_beat = result

        return {
            "action": "beat_generated",
            "result": result,
            "reply": (
                f"Beat uretildi: {result['genre'].replace('_', ' ').title()} "
                f"@ {result['bpm']} BPM, {result['bars']} bar, "
                f"{result['duration']:.1f}s sure. "
                f"Enstrumanlar: {', '.join(result['stems'].keys())}"
            ),
            "stems_count": len(result["stems"]),
        }

    def _handle_modify_command(self, cmd):
        """Modify the current beat."""
        if not self.last_beat:
            return {
                "action": "error",
                "reply": "Once bir beat olustur: '128 BPM house beat yap'",
            }

        result = self.beat_studio.modify(self.last_beat, cmd)
        self.last_beat = result

        return {
            "action": "beat_modified",
            "result": result,
            "reply": f"Beat guncellendi: {cmd}",
        }

    def _handle_export_command(self, cmd):
        """Export current beat to file."""
        if not self.last_beat:
            return {
                "action": "error",
                "reply": "Once bir beat olustur.",
            }

        os.makedirs(self.output_dir, exist_ok=True)

        if "stem" in cmd:
            # Export individual stems
            stem_dir = os.path.join(self.output_dir, "stems")
            paths = self.beat_studio.export_stems(self.last_beat, stem_dir)
            return {
                "action": "stems_exported",
                "paths": paths,
                "reply": f"Stem'ler kaydedildi: {stem_dir} ({len(paths)} dosya)",
            }
        else:
            # Export mix
            genre = self.last_beat["genre"]
            bpm = self.last_beat["bpm"]
            filename = f"{genre}_{bpm}bpm_mix.wav"
            path = os.path.join(self.output_dir, filename)

            if "pro" in cmd or "kalite" in cmd or "24" in cmd:
                self.beat_studio.export_pro_wav(self.last_beat, path, bit_depth=24)
                reply = f"Pro WAV (24-bit) kaydedildi: {path}"
            else:
                self.beat_studio.export_mix(self.last_beat, path)
                reply = f"Mix kaydedildi: {path}"

            return {
                "action": "mix_exported",
                "path": path,
                "reply": reply,
            }

    def _handle_stem_command(self, cmd):
        """Separate stems from an audio file."""
        # Extract file path if mentioned
        import glob
        search_patterns = ["*.mp3", "*.wav", "*.flac", "*.m4a"]
        recent_files = []
        for pattern in search_patterns:
            recent_files.extend(glob.glob(os.path.join("DJ_EXPORTS", pattern)))
            recent_files.extend(glob.glob(pattern))

        if not recent_files:
            return {
                "action": "error",
                "reply": "Ayirilacak ses dosyasi bulunamadi. DJ_EXPORTS klasorune bir dosya koy.",
            }

        # Use the most recent file
        audio_path = sorted(recent_files, key=os.path.getmtime)[-1]

        result = self.stem_separator.separate(audio_path)
        self.last_separation = result

        if "error" in result:
            return {
                "action": "error",
                "reply": f"Stem ayirma hatasi: {result['error']}",
            }

        # Export stems
        stem_dir = os.path.join(self.output_dir, "separated")
        paths = self.stem_separator.export_stems(result, stem_dir)

        engine = result.get("engine", "unknown")
        return {
            "action": "stems_separated",
            "result": result,
            "paths": paths,
            "reply": (
                f"Stem'ler ayirildi ({engine}): {', '.join(paths.keys())} "
                f"-> {stem_dir}"
            ),
        }

    def _handle_library_command(self, cmd):
        """Library intelligence commands."""
        if not self.library_ai:
            return {
                "action": "error",
                "reply": "Once kutuphane yukle. 'Kutuphane yukle' de.",
            }

        if "saglik" in cmd or "health" in cmd:
            health = self.library_ai.health_report()
            return {
                "action": "health_report",
                "result": health,
                "reply": (
                    f"Kutuphane sagligi: {health['score']}/100 | "
                    f"Tur: {health.get('unique_genres', 0)} | "
                    f"Ton: {health.get('unique_keys', 0)} | "
                    f"BPM: {health.get('bpm_range', 'N/A')}"
                ),
            }

        if "gap" in cmd or "eksik" in cmd:
            gaps = self.library_ai.find_gaps()
            return {
                "action": "gap_analysis",
                "result": gaps,
                "reply": "Eksikler:\n" + "\n".join(f"- {g}" for g in gaps),
            }

        if "mood" in cmd:
            mood_dist = self.library_ai.mood_distribution()
            return {
                "action": "mood_distribution",
                "result": mood_dist,
                "reply": "Mood dagilimi:\n" + "\n".join(
                    f"- {mood}: {count} parca"
                    for mood, count in sorted(mood_dist.items(), key=lambda x: -x[1])
                ),
            }

        # Default: health report
        health = self.library_ai.health_report()
        return {
            "action": "library_info",
            "result": health,
            "reply": f"Kutuphane: {health['total']} parca, saglik {health['score']}/100",
        }

    def _handle_set_command(self, cmd):
        """Generate a DJ set."""
        if not self.library_ai:
            return {
                "action": "error",
                "reply": "Once kutuphane yukle.",
            }

        # Parse duration
        hours = 2
        if m := re.search(r"(\d+)\s*(?:saat|hour|s)", cmd):
            hours = int(m.group(1))
            hours = max(1, min(8, hours))

        # Parse style
        style = "ENERGY_RISE"
        if "wave" in cmd or "dalga" in cmd:
            style = "WAVE"
        elif "sustain" in cmd or "devamli" in cmd:
            style = "SUSTAINED"
        elif "sunrise" in cmd or "gunes" in cmd:
            style = "SUNRISE"

        tracks = self.library_ai.last_library if hasattr(self.library_ai, 'last_library') else []
        if not tracks:
            tracks = self.library_ai.tracks

        flow = self.library_ai.optimize_flow(tracks, style=style, duration_hours=hours)

        # Export as M3U
        from app.core.export_center import ExportCenter
        exporter = ExportCenter(self.output_dir)
        m3u_path = exporter.export_m3u(flow, f"ai_set_{style.lower()}")

        return {
            "action": "set_generated",
            "result": {"tracks": flow, "style": style, "duration_hours": hours},
            "path": m3u_path,
            "reply": (
                f"Set olusturuldu: {len(flow)} parca, {hours} saat, "
                f"stil: {style}. "
                f"Kayit: {m3u_path}"
            ),
        }

    def _handle_key_command(self, cmd):
        """Key compatibility lookup."""
        # Extract Camelot key
        m = re.search(r"(\d{1,2}[AB])", cmd.upper())
        if m:
            key = m.group(1)
            compat = self.beat_studio.last_result  # Placeholder
            from app.ai.library_ai import LibraryAI
            compatible = LibraryAI.key_compatibility(None, key)
            return {
                "action": "key_compatibility",
                "result": compatible,
                "reply": f"{key} ile karisabilen tonlar: {', '.join(compatible)}",
            }

        return {
            "action": "error",
            "reply": "Bir Camelot tani girin: '8A ile hangi tonlar karisir'",
        }

    def get_status(self):
        """Get current engine status."""
        return {
            "beat_studio": "ready",
            "stem_separator": "demucs" if self.stem_separator.is_demucs_available() else "spectral",
            "library_ai": "loaded" if self.library_ai else "empty",
            "last_beat": self.beat_studio.describe(self.last_beat) if self.last_beat else None,
            "output_dir": self.output_dir,
        }
