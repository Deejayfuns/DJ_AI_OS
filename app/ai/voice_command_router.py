class VoiceCommandRouter:

    COMMANDS = [
        {
            "intent": "LOAD_LIBRARY",
            "keywords": [
                "klasor sec",
                "arsiv yukle",
                "library yukle",
                "muzik tara",
                "scan",
                "load library",
                "muzik yukle",
                "dosya ekle",
                "klasor ac",
            ],
            "reply": "Muzik klasoru secme ekranini aciyorum.",
        },
        {
            "intent": "GENERATE_SET",
            "keywords": [
                "set olustur",
                "set hazirla",
                "playlist yap",
                "generate set",
            ],
            "reply": "AI set olusturuyorum.",
        },
        {
            "intent": "PLAY",
            "keywords": [
                "cal",
                "baslat",
                "play",
                "start",
                "oynat",
                "ac",
                "devam et",
            ],
            "reply": "Caliyorum.",
        },
        {
            "intent": "STOP",
            "keywords": [
                "dur",
                "durdur",
                "stop",
                "pause",
                "kes",
                "bitir",
                "beklet",
            ],
            "reply": "Durduruyorum.",
        },
        {
            "intent": "NEXT",
            "keywords": [
                "sonraki",
                "siradaki",
                "next",
            ],
            "reply": "Siradaki parcaya geciyorum.",
        },
        {
            "intent": "OPEN_HEART",
            "keywords": [
                "kalp",
                "duygu",
                "heart",
                "nabiz",
                "kalp ekran",
                "kalp ekranini",
                "kalp panel",
            ],
            "reply": "DJ Heart ekranini aciyorum.",
        },
        {
            "intent": "AUDIT_ARCHIVE",
            "keywords": [
                "arsivi kontrol et",
                "arsiv kontrol",
                "arsivi denetle",
                "audit",
                "sifir dosya",
                "dosyalari denetle",
                "arşiv",
                "arsiv tarama",
            ],
            "reply": "Arsiv saglik kontrolunu baslatiyorum.",
        },
        {
            "intent": "OPEN_DECKS",
            "keywords": [
                "deck",
                "deckleri ac",
                "deck ekran",
                "mixle",
                "auto mix",
                "deck studio",
                "mixer",
                "kanal",
                "kontrol odasi",
            ],
            "reply": "Deck Studio ekranini aciyorum.",
        },
        {
            "intent": "OPEN_CLOUD_EXPORT",
            "keywords": [
                "export",
                "rekordbox",
                "cloud",
                "trend",
                "paket",
                "disa aktar",
            ],
            "reply": "Cloud ve export ekranini aciyorum.",
        },
        {
            "intent": "VOICE_TEST",
            "keywords": [
                "ses test",
                "mikrofon test",
                "tts test",
                "sesli komut testi",
                "voice test",
                "mic test",
                "voice diagnostics",
                "ses kontrol",
            ],
            "reply": "Sesli asistani test ediyorum.",
        },
        {
            "intent": "COACH_SELECTED_TRACK",
            "keywords": [
                "bu parca nasil",
                "bu sarki nasil",
                "bu uygun mu",
                "bunu calayim mi",
                "track advice",
                "parcayi yorumla",
            ],
            "reply": "Secili parcayi DJ kulagi ve kalbiyle yorumluyorum.",
        },
        {
            "intent": "COACH_CURRENT_SET",
            "keywords": [
                "set nasil",
                "akis nasil",
                "gece nasil",
                "seti yorumla",
                "ne calayim",
                "siradaki ne",
            ],
            "reply": "Aktif setin akisini yorumluyorum.",
        },
        {
            "intent": "AUTO_MIX_COACH",
            "keywords": [
                "nasil mixleyeyim",
                "mix oner",
                "gecisi anlat",
                "transition",
                "crossfade",
            ],
            "reply": "Gecis icin DJ talimati hazirliyorum.",
        },
        {
            "intent": "MIX_MASTER_ANALYZE",
            "keywords": [
                "wav analiz",
                "mix master analiz",
                "mastering analiz",
                "sesi analiz et",
                "ses doktoru",
                "master yap",
            ],
            "reply": "Secili dosya icin mix-master analizini baslatiyorum.",
        },
        {
            "intent": "OPEN_REMIX_LAB",
            "keywords": [
                "remix lab",
                "remix yap",
                "vokal ayir",
                "stem ayir",
                "acapella",
            ],
            "reply": "Remix Lab ekranini aciyorum.",
        },
        {
            "intent": "ENABLE_PASSIVE_LISTEN",
            "keywords": [
                "sadece dinle",
                "dinle beni",
                "sessizce dinle",
                "sus ve dinle",
                "benimle konuşma",
            ],
            "reply": "Şimdi sessizce dinliyorum ve konuşmalarını hafızama alıyorum.",
        },
        {
            "intent": "DISABLE_PASSIVE_LISTEN",
            "keywords": [
                "artık dinleme",
                "sessiz modu kapat",
                "sustur",
                "konuşmaya başla",
                "normal mod",
            ],
            "reply": "Sessiz dinleme modu kapatıldı.",
        },
        {
            "intent": "OPEN_ASTRA",
            "keywords": [
                "astra open",
                "astra aç",
                "astra başlat",
                "astra dinle",
                "astra asistan",
            ],
            "reply": "Astra asistanını açıyorum.",
        },
        {
            "intent": "OPEN_TRENDS",
            "keywords": [
                "trendleri ac",
                "guncel sarkilar",
                "hit oner",
                "global trend",
                "beatport",
                "trendleri goster",
                "trendleri gor",
                "populer",
                "sarkilar",
                "hitler",
                "trend",
            ],
            "reply": "Global trend ekranini aciyorum.",
        },
        {
            "intent": "OPEN_SETTINGS",
            "keywords": [
                "ayarlar",
                "settings",
                "ses ayari",
                "voice setup",
                "ayar ekranini ac",
                "ayarları aç",
            ],
            "reply": "Ayarlar ekranini aciyorum.",
        },
        {
            "intent": "SET_LANGUAGE",
            "keywords": [
                "dili değiştir",
                "dili degistir",
                "dil değiştir",
                "dil degistir",
            ],
            "reply": "Lütfen Türkçe veya İngilizce olarak hangi dili istediğini söyle.",
        },
        {
            "intent": "SET_LANGUAGE_TR",
            "keywords": [
                "dili değiştir türkçe",
                "dili degistir turkce",
                "türkçe konuş",
                "turkce konus",
                "dil türkçe",
                "dil turkce",
                "sadece türkçe",
                "konuş türkçe",
            ],
            "reply": "Ses modelini Türkçe'ye alıyorum.",
        },
        {
            "intent": "SET_LANGUAGE_EN",
            "keywords": [
                "dili değiştir ingilizce",
                "dili degistir ingilizce",
                "ingilizce konuş",
                "ingilizce konus",
                "dil ingilizce",
                "sadece ingilizce",
                "konuş ingilizce",
                "english",
                "speak english",
            ],
            "reply": "Dil İngilizceye alınıyor.",
        },
        {
            "intent": "OPEN_ACCOUNT",
            "keywords": [
                "hesap",
                "account",
                "licans",
                "lisans",
                "profil",
                "hesap bilgileri",
            ],
            "reply": "Hesap ve lisans ekranini aciyorum.",
        },
        {
            "intent": "OPEN_CRATE_BUILDER",
            "keywords": [
                "crate",
                "crate builder",
                "crate hazirla",
                "crate yap",
                "crate olustur",
            ],
            "reply": "Crate Builder ekranini aciyorum.",
        },
        {
            "intent": "OPEN_LIVE_VIEW",
            "keywords": [
                "live",
                "canli gorunum",
                "canli",
                "live view",
                "canli dj",
            ],
            "reply": "Canli gorunum ekranini aciyorum.",
        },
        {
            "intent": "OPEN_AI_MEMORY",
            "keywords": [
                "memory",
                "ai hafiza",
                "ai memory",
                "hafiza",
                "memory view",
            ],
            "reply": "AI Memory ekranini aciyorum.",
        },
        {
            "intent": "OPEN_ARCHIVE_GUARDIAN",
            "keywords": [
                "archive guardian",
                "arsiv koruyucu",
                "koruyucu",
                "arsiv guardian",
                "coruma",
            ],
            "reply": "Archive Guardian ekranini aciyorum.",
        },
        {
            "intent": "OPEN_DUPLICATE_REVIEW",
            "keywords": [
                "duplicate review",
                "duplicate incele",
                "duplicate kontrol",
                "tekrar eden",
                "duplicate listesi",
            ],
            "reply": "Duplicate inceleme ekranini aciyorum.",
        },
        {
            "intent": "HELP",
            "keywords": [
                "yardim",
                "komutlar",
                "neler yapiyorsun",
                "ne yaparsin",
                "nasil kullanirim",
                "komut ogren",
                "öğren",
                "ögren",
            ],
            "reply": "Hangi komutlari kullanabilecegini soyluyorum.",
        },
        {
            "intent": "BUILD_SHOW",
            "keywords": [
                "gece kurgula",
                "show hazirla",
                "performans kurgula",
                "4 saatlik set",
                "program yap",
            ],
            "reply": "Show Director ile gece kurgusunu hazirliyorum.",
        },
    ]

    def available_commands_text(self):

        return (
            "Kullanabilecegin ornek komutlar: klasor sec, set olustur, cal, dur, sonraki, "
            "deck ac, remix lab ac, vokal ayir, export et, trendleri ac, mix master analiz, "
            "arsiv denetle, kalp ekranini ac, ayarlar, hesap, crate builder, canli gorunum, "
            "AI memory, duplicate incele."
        )

    def interpret(self, text):

        normalized = self.normalize(text)

        if not normalized:
            return self.unknown("")

        best_match = None
        best_length = -1

        for command in self.COMMANDS:
            for keyword in command["keywords"]:
                if keyword in normalized:
                    if len(keyword) > best_length:
                        best_match = command
                        best_length = len(keyword)

        if best_match:
            return {
                "intent": best_match["intent"],
                "reply": best_match["reply"],
                "confidence": 0.9,
                "heard": text,
            }

        return self.unknown(text)

    def unknown(self, text):

        return {
            "intent": "UNKNOWN",
            "reply": (
                "Bu komutu anlayamadim. "
                f"{self.available_commands_text()}"
            ),
            "confidence": 0.0,
            "heard": text,
        }

    def normalize(self, text):

        text = str(text or "").lower()
        replacements = {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }

        for source, target in replacements.items():
            text = text.replace(source, target)

        return " ".join(text.split())
