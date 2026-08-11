from app.ai.voice_command_router import VoiceCommandRouter
from app.ai.voice_runtime import VoiceRuntime


class VoiceAssistant:

    def __init__(self, provider="openai_realtime"):

        self.provider = provider
        self.router = VoiceCommandRouter()
        self.runtime = VoiceRuntime()
        self._brain = None  # Lazy-loaded AstraBrain

    @property
    def brain(self):
        """Lazy-load the AI brain."""
        if self._brain is None:
            from app.ai.astra_brain import AstraBrain
            self._brain = AstraBrain()
        return self._brain

    def capability_summary(self):

        runtime = self.runtime.status()

        return {
            "available": False,
            "provider": self.provider,
            "mode": "VOICE_RUNTIME_READY",
            "realtime": True,
            "speech_to_speech": True,
            "tts_available": runtime["tts_available"],
            "stt_available": runtime["stt_available"],
            "tts_engine": runtime["tts_engine"],
            "stt_engine": runtime["stt_engine"],
            "language": runtime.get("language", "tr"),
            "requires": [
                "microphone input",
                "speaker output",
                "edge-tts for natural neural speech",
                "SpeechRecognition or Vosk for microphone",
            ],
            "message": (
                "Sesli AI OpenAI key olmadan da calisir. Turkce konusma icin "
                "edge-tts, mikrofon icin SpeechRecognition veya offline Vosk "
                "kullanilir. OpenAI sadece opsiyonel premium transkripsiyon/TTS yoludur."
            ),
        }

    def set_language(self, language_code):
        ok = self.runtime.set_language(language_code)
        return {
            "ok": ok,
            "language": self.runtime.language,
            "message": (
                "Dil ayarı yapıldı." if ok else "Bu dili desteklemiyorum. Türkçe veya İngilizce seçin."
            ),
        }

    def dj_system_prompt(self):

        return (
            "Sen DJ AI OS icinde calisan profesyonel DJ asistanisin. "
            "Kisa, net ve sahne odakli konus. BPM, key, enerji, kalp skoru, "
            "crowd moment ve mix risklerini kullanarak DJ'e kulakliktan "
            "yardim et. Gereksiz uzun aciklama yapma; kritik anda direkt "
            "talimat ver."
        )

    def next_actions(self):

        return [
            "edge-tts ile Turkce neural ses cikisi ver",
            "SpeechRecognition ile mikrofon komutlarini yakala",
            "Offline istersen Vosk Turkce model klasorunu bagla",
            "Uygulama fonksiyonlarini tool olarak modele tanit",
            "Deck, set, search ve music doctor komutlarini sesle calistir",
        ]

    def interpret_command(self, text, context=None):
        """
        Interpret a voice/text command.
        First tries simple router, then falls back to AstraBrain AI.
        """
        # First: simple keyword matching (fast)
        result = self.router.interpret(text)

        # If simple router doesn't recognize, use AstraBrain AI
        if result.get("intent") == "UNKNOWN":
            brain_result = self.brain.process_command(text, context=context or {})

            # Convert brain result to voice assistant format
            if brain_result.get("action") != "unknown":
                return {
                    "intent": "BRAIN_ACTION",
                    "heard": text,
                    "reply": brain_result.get("reply", "Tamam."),
                    "action": brain_result.get("action"),
                    "result": brain_result.get("result"),
                }

        return result

    def listen_once(self, timeout=5, phrase_time_limit=7):

        return self.runtime.listen_once(timeout=timeout, phrase_time_limit=phrase_time_limit)

    def speak_reply(self, text):

        return self.runtime.speak_async(text)
