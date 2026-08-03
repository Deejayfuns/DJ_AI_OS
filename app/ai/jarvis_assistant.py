import os
import random
import re
from app.ai.voice_runtime import VoiceRuntime
from app.ai.assistant_memory import AssistantMemory
from app.ai.graph_memory import GraphMemory


class AstraAssistant:

    def __init__(self, runtime=None):
        self.runtime = runtime or VoiceRuntime()
        self.memory = AssistantMemory()
        self.graph = GraphMemory()
        self.history = []
        self.name = "Astra"

    def status(self):
        runtime = self.runtime.status()

        return {
            "available": self.runtime.tts_available() or self.runtime.stt_available(),
            "provider": "Astra_Core",
            "tts_engine": runtime.get("tts_engine"),
            "stt_engine": runtime.get("stt_engine"),
            "message": (
                "Sahne arkası sohbet asistanı: DJ prodüksiyon fikirleri, remiks stratejileri, "
                "espirili yorumlar ve birlikte yaratım için uyarlanmış Astra stili.")
        }

    def chat(self, prompt):
        text = str(prompt or "").strip()

        if not text:
            response = "Ne hakkında konuşmak istediğini söyle. Stüdyoda beraber bir parça yazıyoruz."
            self.speak(response)
            return {"ok": False, "response": response}

        self.memory.remember("user", text)
        # Log unknown candidate terms into simple memory
        self.memory.log_unknown_terms(self.memory.extract_candidate_terms(text))
        # Also learn relationships between candidate terms into the graph memory
        try:
            self.graph.learn_from_text(text)
        except Exception:
            pass

        response = self.generate_response(text)
        self.memory.remember("assistant", response)
        self.history.append({"user": text, "assistant": response})
        self.speak(response)

        return {
            "ok": True,
            "response": response,
            "history": list(self.history[-20:]),
            "memory_summary": self.memory.recent_summary(),
        }

    def generate_response(self, prompt):
        prompt_lower = prompt.lower()

        answered_definition = self.term_definition_response(prompt_lower)
        if answered_definition:
            return answered_definition

        learned_term = self.learn_term_declaration(prompt_lower)
        if learned_term:
            return learned_term

        if any(term in prompt_lower for term in ["yardim", "komutlar", "neler yapiyorsun", "ne yaparsin", "nasil kullanirim", "komut ogren", "öğren", "ögren"]):
            return (
                "Astra sesli komutlarini ogrendi. "
                f"{self.command_help()}"
                " Ornek: 'Astra, çal', 'Astra, set oluştur', 'Astra, remix lab aç'."
            )

        if any(term in prompt_lower for term in ["set olustur", "set hazirla", "playlist", "playlist yap", "remix", "vokal ayir", "stem", "export", "disa aktar", "trend", "trendleri", "deck", "ayar", "hesap", "crate", "live", "memory", "arsiv", "audit", "duplicate", "doctor", "kalp"]):
            return (
                "Bunlari sesli komut olarak da kullanabilirsin. "
                f"{self.command_help()}"
            )

        if any(term in prompt_lower for term in ["öğren", "ögren", "öyran", "anlamadim", "bilmediğin", "tanımıyor musun", "tanimli degil", "öğret", "öğreti", "ogren"]):
            unknown_terms = self.memory.extract_candidate_terms(prompt)
            if unknown_terms:
                self.memory.log_unknown_terms(unknown_terms)
                return (
                    "Bu kelimeleri hafızama kaydettim ve zamanla daha iyi öğreneceğim: "
                    + ", ".join(unknown_terms[:5]) + "."
                )
            return (
                "Bana yeni bir şey öğrettin gibi görünüyor. Biraz daha detay verirsen, hafızama kaydederim."
            )

        if any(term in prompt_lower for term in ["espiri", "şaka", "komik"]):
            return random.choice([
                "Sahne ışıkları yanıyor, biz de bir espri patlatıyoruz: DJ kabiniyle akustik bir buluşma olabilir mi?",
                "Bu gece remix yapıyoruz, ama önce kahkaha patlatmak serbest. Aklından geçen ritim bir çift şakanın arasından çıktı.",
                "Mikserin potu kadar keskin bir şaka söylüyorum: davul sesi kadar güçlü bir punchline!"
            ])

        if any(term in prompt_lower for term in ["remix", "remiks", "remake", "edit"]):
            return random.choice([
                "Tam da iki müzik insanının kafa kafaya verdiği an: vokali kırpıyor, groove'u yeniden inşa ediyoruz.",
                "Bence ana hatlarıyla bir remix planı: tempoyu 4/4'e çek, ana akoru daha geniş çal ve bası daha seksi yap.",
                "Bu parça için önerim: araya atmosferik bir geçiş koy, sonra geri dönerken kick'i daha canlı hissettir.",
            ])

        if any(term in prompt_lower for term in ["beat", "bpm", "groove", "ritim"]):
            return random.choice([
                "BPM 125-128 arası bir dans pistinde daha fazla nefes alır. Bas hatlarını özellikle vurgulayalım.",
                "Beat için önerim: hi-hat'leri biraz daha hareketli kullan, ama düşük frekansları temiz tut.",
                "Kafamızda bir beat var: perdesiz synth, derin sub ve gökyüzüne açılan melodiye karşı sert bir davul."
            ])

        if any(term in prompt_lower for term in ["yardim", "komutlar", "neler yapiyorsun", "ne yaparsin", "nasil kullanirim", "komut ogren", "öğren", "ögren"]):
            return (
                "Astra sesli komutlarini ogrendi. "
                f"{self.command_help()}"
                " Ornek: 'Astra, çal', 'Astra, set oluştur', 'Astra, remix lab aç'."
            )

        if any(term in prompt_lower for term in ["set olustur", "set hazirla", "playlist", "playlist yap", "remix", "vokal ayir", "stem", "export", "disa aktar", "trend", "deck", "ayar", "hesap", "crate", "live", "memory", "arsiv", "audit", "duplicate", "doctor", "kalp"]):
            return (
                "Bunlari sesli komut olarak da kullanabilirsin. "
                f"{self.command_help()}"
            )

        if any(term in prompt_lower for term in ["jarvis", "asistan", "sen kimsin", "ne yapıyorsun"]):
            return (
                "Ben Astra, DJ prodüksiyon asistaninim. Sistemin arkasında sahneyi izliyor, sesi algılıyor ve "
                "prodüksiyon kararlarını birlikte alıyoruz. Şu anda senden gelen komutları duyuyorum ve cevap veriyorum."
            )

        if any(term in prompt_lower for term in ["ses duyuyor musun", "beni anlıyorsun mu", "komut", "ses komut"]):
            return (
                "Evet, konuşmanı algılıyorum. Mikrofonun aktif ve Astra ses komutlarını dinliyor. "
                "Eğer bir talimat verirsen set, remix veya kamera kontrolünü hemen başlatabilirim."
            )

        if any(term in prompt_lower for term in ["iyi", "nasıl", "ne düşünüyorsun", "fikir"]):
            return random.choice([
                "Bence şu anda stüdyoda iki insan ve teknoloji arasındaki işbirliği sanat eserine dönüşüyor.",
                "Bu fikir, hem duyguyu hem de dans pistini besleyebilir. Hadi biraz daha çarpıcı öğeler ekleyelim.",
                "Gayet güçlü bir başlangıç. Şimdi biraz kontrast ve momentum koyalım."
            ])

        if any(term in prompt_lower for term in ["müzik", "şarkı", "parça", "track"]):
            return random.choice([
                "Bir şarkı tasarlıyoruz: enerjiyi kontrol edelim, kulakları rahatlatacak bölümler yaratalım.",
                "Melodiyi akılda kalıcı tut; beat kısmını ise hafifçe karanlık bırak, sonra patlat.",
                "Bu parça için önerim: girişte küçük bir motif, ortada sürpriz bir vokal efekti, çıkışta geri dönüş."
            ])

        recent = self.memory.recent_summary()
        if recent:
            return (
                "Evet, buradayım. "
                "Son konuşmalarımızı hatırlıyorum: "
                f"{recent}. "
                "Ne yapmak istersin?"
            )

        return random.choice([
            "Evet, buradayım. Şimdi, hangi sahneyi birlikte yazıyoruz?",
            "Aklındaki fikri daha yüksek sesle söyle, ben onu DJ prodüksiyonuna çeviririm.",
            "Stüdyo modu açık. Sana remix ve beat üretimi için öneriler sunabilirim.",
        ])

    def term_definition_response(self, prompt_lower):
        if not any(pattern in prompt_lower for pattern in ["ne demek", "nedir", "anlami ne", "anlamı ne", "tanimi nedir", "tanımı nedir"]):
            return None

        candidates = self.memory.extract_candidate_terms(prompt_lower)
        definitions = []

        for term in candidates:
            meaning = self.memory.get_term(term)
            if meaning:
                definitions.append(f"'{term}' hafızamda şöyle: {meaning}")
            else:
                self.memory.log_unknown_terms([term])

        if definitions:
            return " | ".join(definitions)

        if candidates:
            return (
                "Bu kelimeyi henüz öğrenmedim. Bana anlamını söylersen hafızama eklerim."
            )

        return None

    def learn_term_declaration(self, prompt_lower):
        match = re.search(
            r"([a-zığüşöç0-9 ]{2,})\s+(demek|anlamına geliyor|anlami|anlamı|demek)\s+(.+)",
            prompt_lower
        )

        if not match:
            return None

        term = match.group(1).strip()
        meaning = match.group(3).strip()

        if not term or not meaning:
            return None

        self.memory.learn_term(term, meaning)
        return (
            f"Tamam, '{term}' için bu anlamı kaydettim: {meaning}. "
            "Bundan sonra bu kelimeyi hatırlayacağım."
        )

    def suggest_program_sections(self):
        return (
            "Program için yeni modül önerilerim var: "
            "1) Canlı DJ mix sahnesi ve hot cue yönetimi, "
            "2) gelişmiş sesi analiz eden bir frekans haritası ve enerji segmentasyonu, "
            "3) otomatik geçiş planlayıcısı, "
            "4) kayıt altına alınmış DJ kararlarını inceleyen performans geri bildirimi, "
            "5) remix şablonları ve sahneye uygun müzik kataloğu önerisi."
        )

    def dj_audio_analysis_response(self):
        return (
            "DJ modundayım: frekans spektrumunu, BPM değişimini ve enerji haritasını izliyorum. "
            "Parçayı bir dans pistinde düşün: düşük frekanslar güçlendirilmeli, mid aralığı temizlenmeli, "
            "ve patlama anlarında transient kontrollerini sıkılaştırmalıyız. "
            "Eksik kısımlar için sahne kontrolü ve akış stabilitesi öneriyorum."
        )

    def command_help(self):
        try:
            from app.ai.voice_command_router import VoiceCommandRouter
            router = VoiceCommandRouter()
            return router.available_commands_text()
        except Exception:
            return (
                "Ornek komutlar: klasor sec, set olustur, cal, dur, sonraki, deck ac, remix lab ac, "
                "export et, trendleri ac, mix master analiz, arşiv denetle, kalp ekranini ac."
            )

    def speak(self, text):
        return self.runtime.speak_async(text)
