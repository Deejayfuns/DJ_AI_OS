import json
import os
import shutil
from datetime import datetime

from app.ai.mix_master_doctor import MixMasterDoctor
from app.core.paths import get_exports_dir


class FLStudioBridge:

    def __init__(self, output_folder=None):

        self.output_folder = output_folder or str(get_exports_dir())
        self.mix_master_doctor = MixMasterDoctor()

    def status(self):

        paths = self.find_fl_studio_paths()

        return {
            "mode": "MASTERING_HANDOFF",
            "fl_studio_found": bool(paths),
            "fl_studio_paths": paths,
            "direct_project_edit": False,
            "note": (
                "Guvenli mod: DJ AI OS mix/mastering hazirlik paketi uretir. "
                "FL Studio icinde son duyum ve render DJ/producer tarafindadir."
            ),
        }

    def prepare_mastering_pack(self, track, output_folder=None):

        folder = os.path.abspath(output_folder or self.output_folder)
        os.makedirs(folder, exist_ok=True)
        name = self.safe_name(track.get("name", "mastering_pack"))
        pack_folder = os.path.join(folder, f"{name}_fl_mastering")
        os.makedirs(pack_folder, exist_ok=True)

        report = self.mastering_report(track)
        json_path = os.path.abspath(os.path.join(pack_folder, "mastering_report.json"))
        txt_path = os.path.abspath(os.path.join(pack_folder, "fl_studio_notes.txt"))

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=True)

        with open(txt_path, "w", encoding="utf-8") as handle:
            handle.write(self.notes_text(report))

        return {
            "ok": True,
            "pack_folder": os.path.abspath(pack_folder),
            "report_path": json_path,
            "notes_path": txt_path,
            "headline": report["headline"],
        }

    def export_stems(self, track, stems, output_folder=None):
        """Create stem files and return a mapping. `stems` is a dict name->path or buffer.

        This is a helper to collect stems into a package compatible with FL Studio project import.
        """
        folder = os.path.abspath(output_folder or self.output_folder)
        name = self.safe_name(track.get("name", "stems"))
        stems_folder = os.path.join(folder, f"{name}_stems")
        os.makedirs(stems_folder, exist_ok=True)

        written = {}
        for label, path in (stems or {}).items():
            try:
                dest = os.path.join(stems_folder, f"{self.safe_name(label)}{os.path.splitext(path)[1]}")
                shutil.copy(path, dest)
                written[label] = dest
            except Exception:
                written[label] = None

        return {"ok": True, "stems_folder": stems_folder, "stems": written}

    def create_project_template(self, track, stems_folder, output_folder=None):
        """Generate a small README and project notes for manual import into FL Studio.

        Full programmatic FLP generation isn't supported here; instead we provide guidance
        and prepared stems that FL Studio can import.
        """
        folder = os.path.abspath(output_folder or self.output_folder)
        project_folder = os.path.join(folder, f"{self.safe_name(track.get('name','project'))}_fl_project")
        os.makedirs(project_folder, exist_ok=True)

        readme = os.path.join(project_folder, "import_readme.txt")
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "FL Studio import steps:\n"
                "1) Open FL Studio and create new project.\n"
                "2) Drag stems from the stems folder into the Playlist.\n"
                "3) Route each stem to its own Mixer track.\n"
                "4) Set project BPM to the track BPM and align grid.\n"
            )

        # copy stems folder as a reference
        try:
            dest_stems = os.path.join(project_folder, "stems")
            if os.path.exists(dest_stems):
                shutil.rmtree(dest_stems)
            shutil.copytree(stems_folder, dest_stems)
        except Exception:
            pass

        return {"ok": True, "project_folder": project_folder, "readme": readme}

    def mastering_report(self, track):

        energy = self.number(track.get("energy"), 0.5)
        brightness = self.number(track.get("brightness"), 0.5)
        roughness = self.number(track.get("roughness"), 0.1)
        danceability = self.number(track.get("danceability"), 0.7)
        vocal_risk = self.number(track.get("vocal_risk"), 0.35)
        mixability = self.number(track.get("intro_outro_mixability"), 0.5)
        heart = self.number(track.get("heart_score"), 0.55)
        role = str(track.get("role", "")).upper()
        genre = track.get("genre", "UNKNOWN")

        target_lufs = -8.5 if role == "PEAK TIME" else -10.0
        limiter_ceiling = -1.0
        headroom = -6.0
        club_score = self.club_translation_score(
            energy,
            brightness,
            roughness,
            danceability,
            mixability,
            heart
        )
        mono_risk = self.mono_risk(track)
        kick_bass_risk = self.kick_bass_risk(energy, roughness, genre)
        vocal_clarity = self.vocal_clarity_score(vocal_risk, brightness, roughness)
        eq_notes = []

        if brightness > 0.72:
            eq_notes.append("Ust frekanslari sertlestirme; 8-12 kHz bolgesini kontrollu tut.")
        elif brightness < 0.35:
            eq_notes.append("Ust frekanslarda hafif aciklik gerekebilir; hi-shelf'i dikkatli kullan.")

        if roughness > 0.35:
            eq_notes.append("2-5 kHz bolgesinde yorucu sertlik olabilir; dinleyerek dar EQ uygula.")

        if energy < 0.45:
            eq_notes.append("Master'da fazla limiter basma; groove nefes alsin.")

        if not eq_notes:
            eq_notes.append("Ton dengesi normal; buyuk EQ yerine kucuk dokunuslar yeterli.")

        chain = [
            "Gain staging: master oncesi yaklasik -6 dB headroom",
            "Temizleyici EQ: gereksiz sub rumble icin 25-30 Hz altini kontrol et",
            "Glue compressor: 1-2 dB gain reduction, yavas attack",
            "Ton EQ: mix karakterine gore kucuk dokunuslar",
            "Saturation: cok az, groove ve algilanan ses yuksekligi icin",
            f"Limiter: true peak ceiling {limiter_ceiling} dB, hedef {target_lufs} LUFS civari",
        ]
        ai_decisions = self.ai_mastering_decisions(
            club_score,
            mono_risk,
            kick_bass_risk,
            vocal_clarity
        )
        doctor_report = self.mix_master_doctor.diagnose(track)

        headline = (
            f"{track.get('name', 'Track')} icin FL Studio mastering paketi hazir. "
            f"Hedef {target_lufs} LUFS, headroom {headroom} dB, "
            f"club translation {club_score}/100, "
            f"mix-master doktor {doctor_report['score']}/100."
        )

        return {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "track": track.get("name", "UNKNOWN"),
            "genre": genre,
            "role": role,
            "energy": energy,
            "danceability": danceability,
            "target_lufs": target_lufs,
            "limiter_ceiling_db": limiter_ceiling,
            "pre_master_headroom_db": headroom,
            "club_translation_score": club_score,
            "mono_risk": mono_risk,
            "kick_bass_risk": kick_bass_risk,
            "vocal_clarity_score": vocal_clarity,
            "eq_notes": eq_notes,
            "recommended_chain": chain,
            "ai_mastering_decisions": ai_decisions,
            "mix_master_doctor": doctor_report,
            "reference_targets": self.reference_targets(role, genre),
            "fl_studio_steps": self.fl_studio_steps(),
            "headline": headline,
        }

    def fl_studio_steps(self):

        return [
            "FL Studio'da yeni proje ac.",
            "Audio/stem dosyalarini Playlist'e surukle.",
            "Her stem'i ayri mixer kanalina route et.",
            "Master kanalinda once gain staging yap; limiteri en sona koy.",
            "Notlardaki hedef LUFS ve ceiling degerleriyle render oncesi kontrol et.",
            "Final render'i WAV olarak al, sonra MP3/AAC kopya uret.",
        ]

    def notes_text(self, report):

        lines = [
            "DJ AI OS - FL STUDIO MIX/MASTERING NOTLARI",
            "",
            report["headline"],
            "",
            "Onerilen mastering zinciri:",
        ]
        lines.extend(f"- {item}" for item in report["recommended_chain"])
        lines.extend(["", "EQ notlari:"])
        lines.extend(f"- {item}" for item in report["eq_notes"])
        lines.extend(["", "AI mastering kararlari:"])
        lines.extend(f"- {item}" for item in report["ai_mastering_decisions"])
        doctor = report.get("mix_master_doctor", {})
        if doctor:
            lines.extend([
                "",
                "Mix Master Doctor:",
                f"- Skor: {doctor['score']} / 100",
                f"- Karar: {doctor['verdict']}",
                f"- Not: {doctor['doctor_note']}",
                "",
                "Acil mudahaleler:",
            ])
            lines.extend(f"- {item}" for item in doctor["urgent_fixes"])
            lines.extend(["", "Suno / AI cikti kurtarma zinciri:"])
            lines.extend(f"- {item}" for item in doctor["suno_rescue_chain"])
            lines.extend(["", "Stem stratejisi:"])
            for key, value in doctor["stem_strategy"].items():
                lines.append(f"- {key}: {value}")
        lines.extend(["", "Referans hedefleri:"])
        for key, value in report["reference_targets"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "FL Studio adimlari:"])
        lines.extend(f"- {item}" for item in report["fl_studio_steps"])

        return "\n".join(lines)

    def club_translation_score(
        self,
        energy,
        brightness,
        roughness,
        danceability,
        mixability,
        heart
    ):

        score = (
            energy * 26 +
            danceability * 24 +
            mixability * 18 +
            heart * 16 +
            (1 - abs(brightness - 0.55)) * 10 +
            (1 - min(1, roughness * 2)) * 6
        )

        return round(max(0, min(100, score)), 1)

    def mono_risk(self, track):

        width = self.number(track.get("stereo_width"), 0.5)
        phase = self.number(track.get("phase_correlation"), 0.6)

        if width > 0.82 or phase < 0.25:
            return "HIGH"

        if width > 0.65 or phase < 0.45:
            return "MEDIUM"

        return "LOW"

    def kick_bass_risk(self, energy, roughness, genre):

        genre = str(genre or "").upper()

        if energy >= 0.82 and roughness >= 0.28:
            return "HIGH"

        if "TECH" in genre and energy >= 0.72:
            return "MEDIUM"

        return "LOW"

    def vocal_clarity_score(self, vocal_risk, brightness, roughness):

        score = (
            (1 - vocal_risk) * 45 +
            (1 - abs(brightness - 0.58)) * 35 +
            (1 - min(1, roughness * 2)) * 20
        )

        return round(max(0, min(100, score)), 1)

    def ai_mastering_decisions(
        self,
        club_score,
        mono_risk,
        kick_bass_risk,
        vocal_clarity
    ):

        decisions = []

        if club_score < 65:
            decisions.append("Club translation zayif; limiter yerine mix balansini duzelt.")
        else:
            decisions.append("Club translation guclu; master'da sadece kontrollu loudness ekle.")

        if mono_risk != "LOW":
            decisions.append("Mono uyumlulugu kontrol et; 120 Hz alti mono tut.")

        if kick_bass_risk == "HIGH":
            decisions.append("Kick-bass carpismasi riski yuksek; sidechain ve low-end EQ kontrolu yap.")
        elif kick_bass_risk == "MEDIUM":
            decisions.append("Kick ve bass alanini spectrum analyzer ile ayir.")

        if vocal_clarity < 55:
            decisions.append("Vokal netligi dusuk; 2-5 kHz sertlestirmeden presence ac.")
        else:
            decisions.append("Vokal/lead netligi yeterli; master EQ'da abartma.")

        return decisions

    def reference_targets(self, role, genre):

        genre = str(genre or "").upper()

        if role == "PEAK TIME":
            lufs = "-8 ile -7 LUFS kulup hedefi"
        elif "AFRO" in genre or "ORGANIC" in genre:
            lufs = "-10 ile -8.5 LUFS, groove nefes alsin"
        else:
            lufs = "-10 ile -9 LUFS guvenli DJ master"

        return {
            "loudness": lufs,
            "true_peak": "-1.0 dBTP",
            "headroom_before_master": "-6 dB civari",
            "low_end": "25-30 Hz alti temiz, 120 Hz alti mono kontrol",
            "export": "WAV 24-bit master, ayrica 320 kbps MP3 kopya",
        }

    def find_fl_studio_paths(self):

        candidates = [
            shutil.which("FL64"),
            shutil.which("FL"),
            r"C:\Program Files\Image-Line\FL Studio 2024\FL64.exe",
            r"C:\Program Files\Image-Line\FL Studio 21\FL64.exe",
            r"C:\Program Files\Image-Line\FL Studio 20\FL64.exe",
            r"C:\Program Files (x86)\Image-Line\FL Studio 20\FL.exe",
        ]

        return [
            os.path.abspath(path)
            for path in candidates
            if path and os.path.exists(path)
        ]

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def safe_name(self, value):

        keep = []

        for char in str(value or "mastering_pack"):
            if char.isalnum() or char in ("-", "_"):
                keep.append(char)
            elif char.isspace():
                keep.append("_")

        return "".join(keep).strip("_") or "mastering_pack"
