import os
import json
import re
import shutil
import subprocess
import sys
import glob
import math
import struct
import wave
from datetime import datetime


class RemixLab:

    STYLE_BLUEPRINTS = {
        "AFRO HOUSE": {
            "bpm": 122,
            "drum_feel": "organik perkisyon, sicak alt frekans, akici groove",
            "bass": "yuvarlak sub bass, az ama etkili senkop",
            "vocal_treatment": "kisa cevap vokalleri, uzun reverb gecisleri",
            "arrangement": [
                ("GIRIS", 32, "perkisyon ve atmosfer"),
                ("VOKAL IPUCU", 16, "tek cumlelik vokal kesiti"),
                ("GROOVE KILIDI", 32, "tam davul ve bass"),
                ("ARA BOLUM", 16, "vokal cumle ve pad"),
                ("ANA DROP", 64, "ana groove, her 8 barda vokal cevap"),
                ("CIKIS", 32, "DJ mix cikisi icin sade davul"),
            ],
        },
        "TECH HOUSE": {
            "bpm": 126,
            "drum_feel": "siki kick, tok clap, kuru hi-hat",
            "bass": "kisa ve yuruyen bassline",
            "vocal_treatment": "tek hook kesiti, kapili tekrarlar, minimal cumleler",
            "arrangement": [
                ("GIRIS", 16, "kick ve hi-hat"),
                ("HOOK KESITI", 16, "vokal hook ritmi"),
                ("ANA DROP", 64, "bassline ve hook kesiti"),
                ("ARA BOLUM", 16, "filtrelenmis vokal"),
                ("IKINCI DROP", 64, "tam groove"),
                ("CIKIS", 16, "DJ dostu davul cikisi"),
            ],
        },
        "MELODIC HOUSE": {
            "bpm": 123,
            "drum_feel": "yumusa kick, shaker, genis atmosfer",
            "bass": "sicak ve uzayan bass",
            "vocal_treatment": "duygusal vokal cumlesi, delay, armonik pad destegi",
            "arrangement": [
                ("GIRIS", 32, "doku ve nabiz"),
                ("TEMA", 32, "melodi motifi"),
                ("VOKAL ARA", 32, "ana vokal cumlesi"),
                ("ANA DROP", 64, "melodi ve groove"),
                ("SON YUKSELIS", 32, "vokal ve melodi varyasyonu"),
                ("CIKIS", 32, "mix cikisi icin atmosfer"),
            ],
        },
        "REGGAETON": {
            "bpm": 96,
            "drum_feel": "dembow groove, net snare, latin perkisyon",
            "bass": "dembow vurgularini takip eden sade sub",
            "vocal_treatment": "ana vokali daha butun tut, adlib ekle",
            "arrangement": [
                ("GIRIS", 8, "dembow ipucu"),
                ("VERSE", 32, "ana vokal"),
                ("HOOK", 32, "tam ritim"),
                ("ARA BOLUM", 8, "vokal durusu"),
                ("IKINCI HOOK", 32, "ritim ve adlib"),
                ("CIKIS", 16, "DJ mix icin davul"),
            ],
        },
    }

    def capabilities(self):

        python_command = self.find_python_command()
        demucs_info = self.find_demucs_command(python_command)
        ffmpeg_command = shutil.which("ffmpeg")

        return {
            "python_available": bool(python_command),
            "python_command": self.command_text(python_command),
            "demucs_available": bool(demucs_info),
            "demucs_command": self.command_text(demucs_info),
            "demucs_mode": self.demucs_mode(demucs_info),
            "ffmpeg_available": bool(ffmpeg_command),
            "ffmpeg_command": ffmpeg_command or "",
            "output_folder": os.path.abspath("DJ_REMIX_LAB"),
            "install_hint": (
                "Python kurulduktan sonra: py -m pip install -U demucs soundfile. "
                "FFmpeg icin: winget install Gyan.FFmpeg veya manuel kurulum."
            ),
            "install_steps": [
                "1. Python kur: https://www.python.org/downloads/windows/",
                "2. Kurulumda Add python.exe to PATH secenegini isaretle.",
                "3. PowerShell ac ve py --version komutuyla kontrol et.",
                "4. Demucs kur: py -m pip install -U demucs soundfile",
                "5. FFmpeg kur: winget install Gyan.FFmpeg",
                "6. PowerShell'i kapatip yeniden ac, demucs --help veya py -m demucs --help ile kontrol et.",
            ],
        }

    def build_remix_blueprint(self, track, target_style="AFRO HOUSE"):

        style = str(target_style or "AFRO HOUSE").upper()
        blueprint = self.STYLE_BLUEPRINTS.get(
            style,
            self.STYLE_BLUEPRINTS["AFRO HOUSE"]
        )
        source_bpm = self.number(track.get("bpm"), blueprint["bpm"])
        target_bpm = blueprint["bpm"]
        pitch_percent = 0

        if source_bpm:
            pitch_percent = round(((target_bpm - source_bpm) / source_bpm) * 100, 2)

        return {
            "track": track.get("name", "UNKNOWN"),
            "source_path": track.get("path", track.get("id", "")),
            "target_style": style,
            "source_bpm": source_bpm,
            "target_bpm": target_bpm,
            "tempo_change_percent": pitch_percent,
            "key": track.get("camelot", track.get("key", "")),
            "drum_feel": blueprint["drum_feel"],
            "bass": blueprint["bass"],
            "vocal_treatment": blueprint["vocal_treatment"],
            "arrangement": [
                {
                    "section": section,
                    "bars": bars,
                    "instruction": instruction,
                }
                for section, bars, instruction in blueprint["arrangement"]
            ],
            "stem_plan": [
                "Vokal: ayir, nefes ve dip gurultusunu temizle",
                "Davul: hedef tarza uygun groove ile degistir veya guclendir",
                "Bass: hedef tarza ve tona gore yeniden yaz",
                "Diger kanallar: sadece remixe hizmet eden hook ve dokulari kullan",
            ],
            "legal_note": (
                "Telifli sarkilarda remix/stem kullanimi icin hak sahibinden "
                "izin gerekir. Bu modul yaratici/teknik is akisi sunar."
            ),
        }

    def readiness_profile(self, track, target_style="AFRO HOUSE"):

        caps = self.capabilities()
        blueprint = self.build_remix_blueprint(track, target_style)
        source = track.get("path") or track.get("id")

        checks = [
            self.check_item(
                "Kaynak dosya",
                bool(source and os.path.exists(source)),
                "Secili parcada gercek dosya yolu var.",
                "Tablodan bilgisayarda mevcut olan bir parcayi sec."
            ),
            self.check_item(
                "Python",
                caps["python_available"],
                "Python komutu sistemde gorunuyor.",
                "Python kur ve PATH secenegini aktif et."
            ),
            self.check_item(
                "Demucs",
                caps["demucs_available"],
                "Vokal ayirma motoru hazir.",
                "PowerShell: py -m pip install -U demucs soundfile"
            ),
            self.check_item(
                "FFmpeg",
                caps["ffmpeg_available"],
                "Ses donusturme araci hazir.",
                "PowerShell: winget install Gyan.FFmpeg"
            ),
            self.check_item(
                "BPM bilgisi",
                bool(blueprint["source_bpm"]),
                f"Kaynak BPM: {blueprint['source_bpm']}",
                "Once parcayi analiz et veya BPM bilgisini tamamla."
            ),
            self.check_item(
                "Ton bilgisi",
                bool(blueprint.get("key")),
                f"Ton/Camelot: {blueprint.get('key')}",
                "Harmonik remix icin key/Camelot analizi onerilir."
            ),
        ]

        score = round(
            sum(1 for check in checks if check["ok"]) / max(len(checks), 1) * 100
        )
        verdict = "HAZIR" if score >= 80 else "EKSIKLER VAR"

        if not caps["demucs_available"]:
            verdict = "PLAN HAZIR, STEM ICIN DEMUCS GEREKLI"

        return {
            "score": score,
            "verdict": verdict,
            "checks": checks,
            "tempo_note": self.tempo_note(
                blueprint["source_bpm"],
                blueprint["target_bpm"],
                blueprint["tempo_change_percent"]
            ),
            "next_action": self.next_action(checks),
        }

    def creative_brief(self, track, target_style="AFRO HOUSE"):

        blueprint = self.build_remix_blueprint(track, target_style)
        readiness = self.readiness_profile(track, target_style)

        return {
            "title": f"{blueprint['track']} icin {blueprint['target_style']} remix briefi",
            "readiness_score": readiness["score"],
            "tempo_note": readiness["tempo_note"],
            "dj_goal": (
                "DJ mix icin temiz giris/cikis, ana vokali kontrollu kullanan "
                "ve hedef tarzin groove hissini one cikaran bir versiyon hazirla."
            ),
            "production_focus": [
                blueprint["drum_feel"],
                blueprint["bass"],
                blueprint["vocal_treatment"],
            ],
            "next_action": readiness["next_action"],
        }

    def export_blueprint(self, blueprint, readiness, output_folder="DJ_REMIX_LAB"):

        os.makedirs(output_folder, exist_ok=True)
        base = self.safe_name(
            f"{blueprint['track']}_{blueprint['target_style']}_remix_plan"
        )
        json_path = os.path.abspath(os.path.join(output_folder, f"{base}.json"))
        txt_path = os.path.abspath(os.path.join(output_folder, f"{base}.txt"))
        payload = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "blueprint": blueprint,
            "readiness": readiness,
        }

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        with open(txt_path, "w", encoding="utf-8") as handle:
            handle.write(self.blueprint_text(blueprint, readiness))

        return {
            "json_path": json_path,
            "txt_path": txt_path,
        }

    def render_remix_wav(
        self,
        track,
        target_style="AFRO HOUSE",
        output_folder="DJ_REMIX_LAB",
        duration_seconds=96
    ):

        blueprint = self.build_remix_blueprint(track, target_style)
        os.makedirs(output_folder, exist_ok=True)
        base = self.safe_name(
            f"{blueprint['track']}_{blueprint['target_style']}_ai_remix"
        )
        wav_path = os.path.abspath(os.path.join(output_folder, f"{base}.wav"))
        manifest_path = os.path.abspath(os.path.join(output_folder, f"{base}.json"))

        sample_rate = 44100
        bpm = int(blueprint["target_bpm"])
        total_samples = int(sample_rate * max(16, duration_seconds))
        style = blueprint["target_style"]
        vocal_texture = self.load_vocal_texture(
            track.get("path") or track.get("id"),
            sample_rate
        )
        rendered = []

        for index in range(total_samples):
            seconds = index / sample_rate
            beat = seconds * bpm / 60
            bar = int(beat // 4)
            local_beat = beat % 4
            envelope = self.arrangement_envelope(bar, blueprint)
            sample = self.remix_sample(style, seconds, beat, local_beat, envelope)

            if vocal_texture and envelope["vocal"] > 0:
                texture_index = int((index * blueprint["source_bpm"] / bpm) % len(vocal_texture))
                sample += vocal_texture[texture_index] * 0.18 * envelope["vocal"]

            rendered.append(sample)

        rendered = self.master_render(rendered)

        with wave.open(wav_path, "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            frames = []

            for sample in rendered:
                left = int(max(-1, min(1, sample * 0.98)) * 32767)
                right = int(max(-1, min(1, sample * 0.94)) * 32767)
                frames.append(struct.pack("<hh", left, right))

            handle.writeframes(b"".join(frames))

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "render_engine": "DJ_AI_SYNTHETIC_SAMPLE_PACK_V1",
            "wav_path": wav_path,
            "track": blueprint["track"],
            "target_style": style,
            "target_bpm": bpm,
            "duration_seconds": duration_seconds,
            "sample_rate": sample_rate,
            "sample_pack": self.sample_pack_manifest(style),
            "vocal_texture_used": bool(vocal_texture),
            "quality_note": (
                "Bu render telifsiz sentetik sample pack motorudur. "
                "Gercek stem/vokal kaynaklari icin Demucs ile ayrilmis dosyalar "
                "ve lisansli sample pack entegrasyonu sonraki profesyonel katmandir."
            ),
            "legal_note": blueprint["legal_note"],
        }

        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)

        return {
            "ok": True,
            "wav_path": wav_path,
            "manifest_path": manifest_path,
            "engine": manifest["render_engine"],
            "target_style": style,
            "target_bpm": bpm,
            "vocal_texture_used": bool(vocal_texture),
        }

    def remix_sample(self, style, seconds, beat, local_beat, envelope):

        kick = self.kick(local_beat) * envelope["drums"]
        hat = self.hat(beat) * envelope["drums"]
        perc = self.percussion(style, beat) * envelope["drums"]
        bass = self.bassline(style, seconds, beat) * envelope["bass"]
        chord = self.chord_texture(style, seconds, beat) * envelope["music"]
        riser = self.riser(beat) * envelope["fx"]

        return kick + hat + perc + bass + chord + riser

    def kick(self, local_beat):

        phase = local_beat % 1

        if phase > 0.22:
            return 0

        return math.sin(2 * math.pi * (48 + 80 * (1 - phase)) * phase * 0.12) * (1 - phase / 0.22) * 0.95

    def hat(self, beat):

        phase = (beat * 2) % 1

        if phase > 0.12:
            return 0

        noise = math.sin(beat * 911.7) * math.sin(beat * 143.3)
        return noise * (1 - phase / 0.12) * 0.11

    def percussion(self, style, beat):

        phase = beat % 1
        sync = 0.5 if style == "AFRO HOUSE" else 0.25
        accent = abs((beat * (3 if style == "AFRO HOUSE" else 4)) % 1 - sync)

        if accent > 0.08:
            return 0

        tone = 260 if style == "AFRO HOUSE" else 420
        return math.sin(2 * math.pi * tone * phase * 0.035) * (1 - accent / 0.08) * 0.16

    def bassline(self, style, seconds, beat):

        notes = {
            "AFRO HOUSE": [55, 55, 65.4, 49],
            "TECH HOUSE": [49, 49, 55, 58.3],
            "MELODIC HOUSE": [55, 65.4, 73.4, 65.4],
            "REGGAETON": [49, 49, 58.3, 55],
        }.get(style, [55, 55, 65.4, 49])
        note = notes[int(beat) % len(notes)]
        gate = 0.72 if (beat % 1) < 0.62 else 0.12
        return math.sin(2 * math.pi * note * seconds) * gate * 0.32

    def chord_texture(self, style, seconds, beat):

        if int(beat // 8) % 2 == 0:
            return 0

        roots = {
            "AFRO HOUSE": [220, 277.18, 329.63],
            "TECH HOUSE": [196, 246.94, 293.66],
            "MELODIC HOUSE": [220, 261.63, 329.63],
            "REGGAETON": [196, 246.94, 329.63],
        }.get(style, [220, 277.18, 329.63])
        value = sum(math.sin(2 * math.pi * freq * seconds) for freq in roots) / len(roots)
        slow = 0.45 + 0.55 * math.sin(2 * math.pi * 0.12 * seconds) ** 2
        return value * slow * 0.08

    def riser(self, beat):

        bar_position = beat % 32

        if bar_position < 28:
            return 0

        amount = (bar_position - 28) / 4
        return math.sin(2 * math.pi * (440 + 1200 * amount) * beat * 0.002) * amount * 0.08

    def arrangement_envelope(self, bar, blueprint):

        total = 0

        for section in blueprint["arrangement"]:
            start = total
            total += int(section["bars"])

            if bar < total:
                name = section["section"]
                return {
                    "drums": 0.45 if "GIRIS" in name else 0.9,
                    "bass": 0.0 if "GIRIS" in name and bar < start + 8 else 0.78,
                    "music": 0.25 if "GIRIS" in name else 0.55,
                    "vocal": 0.75 if "VOKAL" in name or "HOOK" in name or "DROP" in name else 0.12,
                    "fx": 0.8 if total - bar <= 4 else 0.12,
                }

        return {"drums": 0.55, "bass": 0.25, "music": 0.18, "vocal": 0.0, "fx": 0.05}

    def load_vocal_texture(self, source, sample_rate):

        if not source or not os.path.exists(source) or not str(source).lower().endswith(".wav"):
            return []

        try:
            with wave.open(source, "rb") as handle:
                channels = handle.getnchannels()
                width = handle.getsampwidth()
                frames = min(handle.getnframes(), sample_rate * 8)
                raw = handle.readframes(frames)

            if width != 2:
                return []

            values = struct.unpack("<" + "h" * (len(raw) // 2), raw)
            mono = []

            for index in range(0, len(values), max(1, channels)):
                chunk = values[index:index + channels]
                mono.append(sum(chunk) / max(len(chunk), 1) / 32768.0)

            return self.master_render(mono[:sample_rate * 4])
        except Exception:
            return []

    def master_render(self, samples):

        if not samples:
            return []

        peak = max(abs(value) for value in samples) or 1
        gain = min(1.0, 0.92 / peak)
        smoothed = []
        previous = 0

        for sample in samples:
            value = math.tanh(sample * gain * 1.35)
            value = previous * 0.08 + value * 0.92
            smoothed.append(value)
            previous = value

        return smoothed

    def sample_pack_manifest(self, style):

        return {
            "style": style,
            "kick": "synthetic tuned club kick",
            "hat": "procedural offbeat noise hat",
            "percussion": "procedural afro/club percussion",
            "bass": "target-style synthesized bassline",
            "music": "harmonic pad/chord texture",
            "fx": "bar-aware riser",
        }

    def separate_vocals(self, track, output_folder="DJ_REMIX_LAB"):

        source = track.get("path") or track.get("id")

        if not source or not os.path.exists(source):
            return {
                "ok": False,
                "reason": "SOURCE_FILE_NOT_FOUND",
                "message": "Stem ayirma icin gecerli bir dosya sec.",
            }

        caps = self.capabilities()

        if not caps["demucs_available"]:
            return {
                "ok": False,
                "reason": "DEMUCS_NOT_INSTALLED",
                "message": caps["install_hint"],
                "command": self.demucs_command(source, output_folder),
            }

        os.makedirs(output_folder, exist_ok=True)
        command = self.demucs_command(source, output_folder)

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60 * 30
            )

            return {
                "ok": process.returncode == 0,
                "reason": "DONE" if process.returncode == 0 else "DEMUCS_FAILED",
                "message": process.stdout[-1000:] or process.stderr[-1000:],
                "command": command,
                "output_folder": os.path.abspath(output_folder),
            }
        except Exception as e:
            return {
                "ok": False,
                "reason": "DEMUCS_ERROR",
                "message": str(e),
                "command": command,
            }

    def demucs_command(self, source, output_folder):

        caps = self.capabilities()
        command = caps.get("demucs_command") or "demucs"

        if command == "python -m demucs":
            base = [sys.executable, "-m", "demucs"]
        elif command.endswith(" -m demucs"):
            base = command.split(" ")[:-2] + ["-m", "demucs"]
        else:
            base = [command]

        return base + [
            "--two-stems",
            "vocals",
            "-o",
            output_folder,
            source,
        ]

    def find_python_command(self):

        candidates = [
            sys.executable,
            shutil.which("py"),
            shutil.which("python"),
            shutil.which("python3"),
        ]

        for candidate in candidates:
            if candidate:
                return candidate

        return ""

    def find_demucs_command(self, python_command=""):

        bundled = self.bundled_demucs_command()

        if bundled:
            return bundled

        executable = shutil.which("demucs")

        if executable:
            return executable

        user_script = self.find_user_script("demucs.exe")

        if user_script:
            return user_script

        if self.python_module_available("demucs"):
            return [sys.executable, "-m", "demucs"]

        if python_command and self.external_python_has_demucs(python_command):
            return [python_command, "-m", "demucs"]

        return ""

    def find_user_script(self, executable_name):

        roots = [
            os.environ.get("APPDATA", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.path.expanduser("~"),
        ]

        patterns = []

        for root in roots:
            if not root:
                continue

            patterns.extend([
                os.path.join(root, "Python", "Python*", "Scripts", executable_name),
                os.path.join(root, "Programs", "Python", "Python*", "Scripts", executable_name),
                os.path.join(root, ".local", "bin", executable_name),
            ])

        for pattern in patterns:
            matches = glob.glob(pattern)

            if matches:
                return os.path.abspath(matches[0])

        return ""

    def bundled_demucs_command(self):

        root = os.path.abspath(os.getcwd())
        demucs_exe = os.path.join(root, "tools", "demucs", "demucs.exe")
        bundled_python = os.path.join(root, "tools", "python", "python.exe")

        if os.path.exists(demucs_exe):
            return demucs_exe

        if os.path.exists(bundled_python):
            return [bundled_python, "-m", "demucs"]

        return ""

    def python_module_available(self, module_name):

        try:
            import importlib.util
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False

    def external_python_has_demucs(self, python_command):

        if python_command == sys.executable:
            return False

        try:
            process = subprocess.run(
                [
                    python_command,
                    "-c",
                    "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('demucs') else 1)",
                ],
                capture_output=True,
                text=True,
                timeout=8,
            )
            return process.returncode == 0
        except Exception:
            return False

    def command_text(self, command):

        if isinstance(command, list):
            if len(command) >= 3 and command[-2:] == ["-m", "demucs"]:
                return f"{command[0]} -m demucs"

            return " ".join(command)

        return command or ""

    def demucs_mode(self, command):

        if isinstance(command, list):
            return "PYTHON_MODULE"

        if command:
            return "EXECUTABLE"

        return "MISSING"

    def number(self, value, default):

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def check_item(self, label, ok, ok_text, fix_text):

        return {
            "label": label,
            "ok": bool(ok),
            "status": "tamam" if ok else "eksik",
            "message": ok_text if ok else fix_text,
        }

    def tempo_note(self, source_bpm, target_bpm, percent):

        if not source_bpm:
            return "BPM bilinmiyor; once analiz onerilir."

        if abs(percent) <= 3:
            return "Tempo farki kucuk; doğal pitch/tempo gecisi mumkun."

        if abs(percent) <= 8:
            return "Tempo farki orta; vokalde artefakt riskini kontrol et."

        return "Tempo farki yuksek; yeniden davul yazimi ve vokal time-stretch kontrolu gerekir."

    def next_action(self, checks):

        for check in checks:
            if not check["ok"]:
                return check["message"]

        return "Remix plani hazir. Istersen vokali ayirip DAW projesine gecebilirsin."

    def safe_name(self, value):

        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")
        return name[:120] or "remix_plan"

    def blueprint_text(self, blueprint, readiness):

        lines = [
            f"REMIX PLANI: {blueprint['track']}",
            f"Hedef tarz: {blueprint['target_style']}",
            f"BPM: {blueprint['source_bpm']} -> {blueprint['target_bpm']} ({blueprint['tempo_change_percent']:+.2f}%)",
            f"Hazirlik skoru: {readiness['score']} / 100",
            f"Durum: {readiness['verdict']}",
            f"Tempo notu: {readiness['tempo_note']}",
            "",
            "Yaratim notlari:",
            f"- Davul: {blueprint['drum_feel']}",
            f"- Bass: {blueprint['bass']}",
            f"- Vokal: {blueprint['vocal_treatment']}",
            "",
            "Akis:",
        ]

        for section in blueprint["arrangement"]:
            lines.append(
                f"- {section['section']} | {section['bars']} bar | {section['instruction']}"
            )

        lines.extend(["", "Stem plani:"])
        lines.extend(f"- {item}" for item in blueprint["stem_plan"])
        lines.extend(["", blueprint["legal_note"]])

        return "\n".join(lines)
