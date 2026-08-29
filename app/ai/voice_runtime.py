import asyncio
import contextlib
import importlib.util
import io
import os
import platform
import subprocess
import sys
import tempfile
import threading


class VoiceRuntime:

    def __init__(self):

        self.last_spoken = ""
        self.language = "tr"
        self.tts_priority = ["edge_tts", "gtts", "pyttsx3", "openai"]
        self.last_working_tts = None

    def set_language(self, language_code):
        if not language_code:
            return False

        normalized = str(language_code or "").strip().lower()

        if normalized in ("tr", "tr-TR", "turkce", "turk", "turkish", "türkçe"):
            self.language = "tr"
            return True

        if normalized in ("en", "en-US", "english", "ingilizce"):
            self.language = "en"
            return True

        return False

    def get_language_code(self):
        return "tr-TR" if self.language == "tr" else "en-US"

    def get_gtts_lang(self):
        return "tr" if self.language == "tr" else "en"

    def get_edge_voice(self):
        """Return the user-selected edge-tts voice id, falling back to
        language-appropriate default."""
        try:
            from app.core import voice_config
            vid = voice_config.get_voice_id()
            model = voice_config.get_voice_model(vid)
            # If the selected voice matches current language, use it
            if model["lang"] == self.language:
                return vid
        except Exception:
            pass
        # Fallback: language-appropriate default
        if self.language == "en":
            return "en-US-JennyNeural"
        return "tr-TR-AhmetNeural"

    def status(self):

        voices = self.available_voices()
        turkish_voice = self.find_turkish_voice(voices)
        sapi_turkish_voice = self.find_turkish_voice(self.windows_sapi_voices())
        packages = self.package_status()

        return {
            "tts_available": self.tts_available(),
            "stt_available": self.stt_available(),
            "platform": platform.system(),
            "python_executable": sys.executable,
            "stt_engine": self.stt_engine_name(),
            "tts_engine": self.tts_engine_name(),
            "language": self.language,
            "vosk_model_available": self.vosk_model_available(),
            "vosk_model_path": self.vosk_model_path(),
            "turkish_voice_available": bool(turkish_voice),
            "turkish_voice": turkish_voice or "",
            "sapi_turkish_voice_available": bool(sapi_turkish_voice),
            "sapi_turkish_voice": sapi_turkish_voice or "",
            "turkish_tts_ready": self.turkish_tts_ready(),
            "voices": voices[:12],
            "packages": packages,
            "recommended_install": self.recommended_install_command(),
        }

    def tts_available(self):

        if self.has_module("edge_tts"):
            return True

        if self.has_module("gtts"):
            return True

        if self.has_module("pyttsx3"):
            return True

        if self.has_module("openai") and os.getenv("OPENAI_API_KEY"):
            return True

        return False

    def stt_available(self):

        if self.has_module("speech_recognition") and self.has_module("pyaudio"):
            return True

        return (
            self.has_module("openai") and
            self.has_module("sounddevice") and
            self.has_module("soundfile") and
            bool(os.getenv("OPENAI_API_KEY"))
        ) or (
            self.has_module("vosk") and
            self.has_module("sounddevice") and
            self.vosk_model_available()
        )

    def tts_engine_name(self):

        if self.last_working_tts:
            return f"{self.last_working_tts} ({self.language})"

        if self.has_module("edge_tts"):
            return f"edge-tts ({self.language})"

        if self.has_module("gtts"):
            return f"gTTS ({self.language})"

        if self.has_module("pyttsx3"):
            return f"pyttsx3 ({self.language})"

        if self.has_module("openai") and os.getenv("OPENAI_API_KEY"):
            return f"OpenAI TTS ({self.language})"

        return "NOT_INSTALLED"

    def stt_engine_name(self):

        if self.has_module("speech_recognition") and self.has_module("pyaudio"):
            return "SpeechRecognition + PyAudio"

        if self.has_module("speech_recognition"):
            return "SpeechRecognition installed, PyAudio missing"

        if (
            self.has_module("vosk") and
            self.has_module("sounddevice") and
            self.vosk_model_available()
        ):
            return "Vosk offline + sounddevice"

        if self.has_module("vosk") and self.has_module("sounddevice"):
            return "Vosk installed, Turkish model missing"

        if (
            self.has_module("openai") and
            self.has_module("sounddevice") and
            self.has_module("soundfile") and
            os.getenv("OPENAI_API_KEY")
        ):
            return "OpenAI Whisper + sounddevice"

        return "NOT_INSTALLED"

    def listen_once(self, timeout=5, phrase_time_limit=7):

        attempts = []

        if (
            self.has_module("speech_recognition") and
            self.has_module("pyaudio")
        ):
            attempts.append(("SpeechRecognition", self.listen_with_speech_recognition))

        if (
            self.has_module("vosk") and
            self.has_module("sounddevice") and
            self.vosk_model_available()
        ):
            attempts.append(("Vosk", self.listen_with_vosk))

        if (
            self.has_module("openai") and
            self.has_module("sounddevice") and
            self.has_module("soundfile") and
            os.getenv("OPENAI_API_KEY")
        ):
            attempts.append(("OpenAI Whisper", self.listen_with_openai_whisper))

        last_error = ""

        for name, method in attempts:
            if name == "SpeechRecognition":
                result = method(timeout, phrase_time_limit)
            else:
                result = method(phrase_time_limit)

            if result.get("ok"):
                return result

            last_error = f"{name} fallback: {result.get('error', 'unknown error')}"

        if last_error:
            return {
                "ok": False,
                "text": "",
                "error": (
                    "Ses algilama basarili olamadi. "
                    f"Denenen yollar: {last_error}. "
                    "Lutfen mikrofon baglantisini veya model ayarlarinizi kontrol edin."
                ),
            }

        return {
            "ok": False,
            "text": "",
            "error": (
                "Mikrofon icin ucretsiz yollardan biri gerekli: "
                "1) SpeechRecognition + PyAudio, "
                "2) Vosk + sounddevice + offline Turkce model. "
                "OpenAI sadece opsiyoneldir."
            ),
        }

    def listen_with_speech_recognition(self, timeout=5, phrase_time_limit=7):

        try:
            import speech_recognition as sr
        except Exception:
            return {
                "ok": False,
                "text": "",
                "error": (
                    "Mikrofon dinleme icin SpeechRecognition kurulu olmali."
                ),
            }

        recognizer = sr.Recognizer()

        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
        except SystemExit:
            # PyAudio GIL crash — disable voice silently
            return {
                "ok": False,
                "text": "",
                "error": "SES MOTORU KAPATILDI: Mikrofon GIL hatasi",
            }
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"Mikrofon acilamadi: {e}",
            }

        try:
            text = recognizer.recognize_google(audio, language=self.get_language_code())
            return {
                "ok": True,
                "text": text,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"Ses anlasilamadi: {e}",
            }

    def listen_with_vosk(self, phrase_time_limit=7):

        try:
            import json
            import queue
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"Vosk yolu hazir degil: {e}",
            }

        model_path = self.vosk_model_path()

        if not os.path.exists(model_path):
            return {
                "ok": False,
                "text": "",
                "error": (
                    "Offline Vosk Turkce model bulunamadi. "
                    "VOSK_MODEL_PATH ayarla veya modeli models/vosk-tr "
                    "klasorune koy."
                ),
            }

        samplerate = 16000
        audio_queue = queue.Queue()

        def callback(indata, _frames, _time, status):
            if status:
                pass
            audio_queue.put(bytes(indata))

        try:
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, samplerate)

            with sd.RawInputStream(
                samplerate=samplerate,
                blocksize=8000,
                dtype="int16",
                channels=1,
                callback=callback
            ):
                loops = max(1, int((phrase_time_limit or 7) * 2))

                for _ in range(loops):
                    data = audio_queue.get(timeout=2)
                    recognizer.AcceptWaveform(data)

            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "")

            return {
                "ok": bool(text),
                "text": text,
                "error": "" if text else "Ses anlasilamadi.",
            }
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"Vosk mikrofon hatasi: {e}",
            }

    def listen_with_openai_whisper(self, phrase_time_limit=7):

        try:
            import sounddevice as sd
            import soundfile as sf
            from openai import OpenAI
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"OpenAI mikrofon yolu hazir degil: {e}",
            }

        samplerate = 16000
        seconds = max(2, int(phrase_time_limit or 7))

        try:
            audio = sd.rec(
                int(seconds * samplerate),
                samplerate=samplerate,
                channels=1,
                dtype="int16"
            )
            sd.wait()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = tmp.name

            sf.write(path, audio, samplerate)

            client = OpenAI()

            with open(path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file,
                    language=self.language
                )

            try:
                os.remove(path)
            except OSError:
                pass

            return {
                "ok": True,
                "text": transcript.text,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "text": "",
                "error": f"OpenAI transkripsiyon hatasi: {e}",
            }

    def speak_async(self, text):

        thread = threading.Thread(
            target=self.speak,
            args=(text,),
            daemon=True
        )
        thread.start()

        return thread

    def speak(self, text):

        text = str(text or "").strip()

        if not text:
            return {
                "ok": False,
                "error": "Bos metin konusulamaz.",
            }

        self.last_spoken = text

        for engine_name in list(self.tts_priority):
            if engine_name == "edge_tts" and self.has_module("edge_tts"):
                result = self.speak_with_edge_tts(text)
            elif engine_name == "gtts" and self.has_module("gtts"):
                result = self.speak_with_gtts(text)
            elif engine_name == "pyttsx3" and self.has_module("pyttsx3"):
                result = self.speak_with_pyttsx3(text)
            elif engine_name == "openai" and self.has_module("openai") and os.getenv("OPENAI_API_KEY"):
                result = self.speak_with_openai_tts(text)
            else:
                continue

            if result.get("ok"):
                self.last_working_tts = engine_name
                self._promote_tts_engine(engine_name)
                return result

        return {
            "ok": False,
            "error": "Gelişmiş bir TTS motoru bulunamadi. edge-tts, gTTS, OpenAI TTS veya pyttsx3 yükleyin."
        }

    def speak_with_edge_tts(self, text):

        try:
            asyncio.run(self._edge_tts_to_speaker(text))
            return {
                "ok": True,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    async def _edge_tts_to_speaker(self, text):

        import edge_tts

        voice = self.get_edge_voice()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            path = tmp.name

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(path)
        self.play_audio_file(path)

        try:
            os.remove(path)
        except OSError:
            pass

    def speak_with_openai_tts(self, text):

        try:
            from openai import OpenAI

            client = OpenAI()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                path = tmp.name

            instructions = (
                "Akici, dogal Turkce konus. Ingilizce aksan yapma."
                if self.language == "tr"
                else "Speak fluent natural American English without a strong accent."
            )

            with client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=text,
                instructions=instructions
            ) as response:
                response.stream_to_file(path)

            self.play_audio_file(path)

            try:
                os.remove(path)
            except OSError:
                pass

            return {
                "ok": True,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def speak_with_pyttsx3(self, text):

        try:
            import pyttsx3

            engine = pyttsx3.init()
            self.select_pyttsx3_voice(engine)
            engine.say(text)
            engine.runAndWait()
            return {
                "ok": True,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def speak_with_gtts(self, text):

        try:
            from gtts import gTTS

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                path = tmp.name

            tts = gTTS(text=text, lang=self.get_gtts_lang())
            tts.save(path)
            self.play_audio_file(path)

            try:
                os.remove(path)
            except OSError:
                pass

            return {
                "ok": True,
                "error": "",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def play_audio_file(self, path):

        if platform.system().lower() == "windows":
            try:
                os.startfile(path)
                return
            except Exception:
                pass

        if platform.system().lower() == "darwin":
            try:
                subprocess.Popen(["open", path])
                return
            except Exception:
                pass

        try:
            subprocess.Popen(["xdg-open", path])
            return
        except Exception:
            pass

        if self.has_module("pygame"):
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    import pygame

                pygame.mixer.init()
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    pygame.time.wait(80)

                pygame.mixer.music.unload()
                return
            except Exception:
                pass

        # Last resort: try powershell play command for WAV only.
        if platform.system().lower() == "windows" and path.lower().endswith(".wav"):
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        (
                            "Add-Type -AssemblyName presentationCore; "
                            f"$p=New-Object System.Windows.Media.MediaPlayer; "
                            f"$p.Open([uri]'{path}'); $p.Play(); "
                            "Start-Sleep -Seconds 8"
                        ),
                    ],
                    timeout=15
                )
                return
            except Exception:
                pass

        raise RuntimeError("Ses dosyasi calistirilamadi: audio oynatici bulunamadi.")

    def speak_with_windows_sapi(self, text):
        return {
            "ok": False,
            "error": "Windows SAPI desteği artık aktif değil. edge-tts veya OpenAI TTS kullanın."
        }

        try:
            process = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    script,
                ],
                input=text,
                text=True,
                capture_output=True,
                timeout=30
            )

            return {
                "ok": process.returncode == 0,
                "error": process.stderr.strip(),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def has_module(self, module_name):

        return importlib.util.find_spec(module_name) is not None

    def available_voices(self):

        if self.has_module("pyttsx3"):
            voices = self.pyttsx3_voices()

            if voices:
                return voices

        if platform.system().lower() == "windows":
            return self.windows_sapi_voices() + self.windows_onecore_voices()

        return []

    def pyttsx3_voices(self):

        try:
            import pyttsx3

            engine = pyttsx3.init()
            voices = []

            for voice in engine.getProperty("voices"):
                languages = getattr(voice, "languages", []) or []
                voices.append({
                    "id": str(getattr(voice, "id", "")),
                    "name": str(getattr(voice, "name", "")),
                    "languages": [str(item) for item in languages],
                })

            return voices
        except Exception:
            return []

    def windows_sapi_voices(self):

        if platform.system().lower() != "windows":
            return []

        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.GetInstalledVoices() | ForEach-Object { "
            "$_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name "
            "}"
        )

        try:
            process = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                text=True,
                capture_output=True,
                timeout=15
            )
        except Exception:
            return []

        voices = []

        for line in process.stdout.splitlines():
            if "|" not in line:
                continue

            name, culture = line.split("|", 1)
            voices.append({
                "id": name.strip(),
                "name": name.strip(),
                "languages": [culture.strip()],
            })

        return voices

    def windows_onecore_voices(self):

        if platform.system().lower() != "windows":
            return []

        script = (
            "$paths = @("
            "'HKLM:\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\*',"
            "'HKCU:\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\*'"
            "); "
            "foreach ($path in $paths) { "
            "Get-ItemProperty -Path $path -ErrorAction SilentlyContinue | "
            "ForEach-Object { "
            "$name = $_.'(default)'; "
            "if (-not $name) { $name = $_.PSChildName }; "
            "$lang = $_.Language; "
            "$name + '|OneCore|' + $lang "
            "} }"
        )

        try:
            process = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                text=True,
                capture_output=True,
                timeout=15
            )
        except Exception:
            return []

        voices = []

        for line in process.stdout.splitlines():
            parts = line.split("|")

            if len(parts) < 3:
                continue

            voices.append({
                "id": parts[0].strip(),
                "name": parts[0].strip(),
                "languages": [parts[2].strip()],
                "engine": "OneCore",
                "note": "Windows OneCore voice; SAPI/pyttsx3 may not use it directly.",
            })

        return voices

    def find_turkish_voice(self, voices):

        for voice in voices:
            haystack = " ".join([
                voice.get("id", ""),
                voice.get("name", ""),
                " ".join(voice.get("languages", [])),
            ]).lower()

            if any(token in haystack for token in ("tr-tr", "turkish", "turk", "tolga", "filiz")):
                return voice.get("name") or voice.get("id")

        return ""

    def package_status(self):

        names = [
            "pyttsx3",
            "gtts",
            "edge_tts",
            "openai",
            "speech_recognition",
            "pyaudio",
            "sounddevice",
            "soundfile",
            "vosk",
            "pygame",
        ]

        return {
            name: self.has_module(name)
            for name in names
        }

    def vosk_model_path(self):

        return os.getenv("VOSK_MODEL_PATH", "models/vosk-tr")

    def vosk_model_available(self):

        return os.path.exists(self.vosk_model_path())

    def turkish_tts_ready(self):

        if self.language == "tr":
            if self.has_module("edge_tts"):
                return True

            if self.has_module("gtts"):
                return True

            if self.has_module("pyttsx3"):
                return True

            if self.has_module("openai") and os.getenv("OPENAI_API_KEY"):
                return True

            return bool(self.find_turkish_voice(self.windows_sapi_voices()))

        if self.language == "en":
            return self.has_module("edge_tts") or self.has_module("gtts") or self.has_module("pyttsx3") or (
                self.has_module("openai") and os.getenv("OPENAI_API_KEY")
            )

        return False

    def recommended_install_command(self):

        return (
            f"\"{sys.executable}\" -m pip install edge-tts gtts pyttsx3 sounddevice soundfile "
            "SpeechRecognition vosk pygame"
        )

    def select_pyttsx3_voice(self, engine):

        try:
            voices = engine.getProperty("voices")
        except Exception:
            return

        # pyttsx3 voice selection may be imperfect; choose the first matching language.
        # Keep the existing voice if already correctly selected.

        target_tokens = (
            ("tr-tr", "turkish", "turk", "tolga", "filiz")
            if self.language == "tr"
            else ("en-us", "english", "us", "david", "zira", "george", "michael")
        )

        for voice in voices:
            haystack = " ".join([
                str(getattr(voice, "id", "")),
                str(getattr(voice, "name", "")),
                " ".join(str(item) for item in (getattr(voice, "languages", []) or [])),
            ]).lower()

            if any(token in haystack for token in target_tokens):
                engine.setProperty("voice", voice.id)
                return

        # If no language-specific voice is found, keep default engine voice.

    def _promote_tts_engine(self, engine_name):

        if engine_name in self.tts_priority:
            self.tts_priority.remove(engine_name)
            self.tts_priority.insert(0, engine_name)
