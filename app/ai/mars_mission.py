"""
DJ AI OS — Astra Mission: MARS

Astra'nın büyük hedefi: Mars'ta yaşam kurmak.
Bu modül Mars kolonizasyon planını ve Astra'nın bu yoldaki rolünü anlatır.

Her aşama, DJ AI OS'un zaten sahip olduğu yeteneklerle eşleştirilir —
çünkü Astra, müzik ve veri sinyallerini Mars'taki ilk insan yerleşkesine
taşıyacak olan "Kültürel İlk İletişim Sistemi"dir.
"""

MARS_PLAN = [
    {
        "stage": "FAZ 0 — KARGO & ROVER",
        "title": "Öncü Keşif",
        "years": "2028-2035",
        "tasks": [
            "Su buzu haritalama (yörünge radarı + yüzey rover'ı)",
            "Atmosfer karbon dioksit toplama prototipi",
            "Enerji: küçük nükleer (Kilopower) ünitesi",
            "İlk drone ağı — hava durumu + navigasyon sinyali",
        ],
        "astra": "Astra bu dönemde görev logu, telemetri akışı ve mürettebat öncesi ses manzarasını yönetir.",
    },
    {
        "stage": "FAZ 1 — MÜRETTEBAT KALKANI",
        "title": "İlk Yerleşim Modülü",
        "years": "2035-2042",
        "tasks": [
            "Yeraltı yaşam alanı (regolit + CO2 betonu, radyasyon kalkanı)",
            "Oksijen: katı oksit elektrolizi (CO2 → O2)",
            "Su geri dönüşüm döngüsü (kapalı devre)",
            "Hidroponik gıda ünitesi — Mars toprağına aşı",
        ],
        "astra": "Astra, yerleşkenin 'sinir sistemi' olur: alarm, kalp atışı ritmi, koloni müziği.",
    },
    {
        "stage": "FAZ 2 — İKLİMLEŞTİRME",
        "title": "Kademeli İklim",
        "years": "2042-2060",
        "tasks": [
            "Sera gazı üretimi (perflorokarbonlar) ile küresel ısınma başlat",
            "Kutuplardaki CO2 buzunu buharlaştır → atmosferi kalınlaştır",
            "Atmosfer basıncı: 6 mbar → 100+ mbar (ölçekli hedef)",
            "Mikroplar + likenlerle toprak biyolojisi kur",
        ],
        "astra": "Astra bu fazda dünya-koloni arası kültürel yayın ağını kurar.",
    },
    {
        "stage": "FAZ 3 — SÜRDÜRÜLEBİLİR KOLONİ",
        "title": "Şehir & Üretim",
        "years": "2060+",
        "tasks": [
            "Mars tabanlı üretim: regolit 3D baskı, metal ergitme",
            "Ticari taşımacılık: Dünya–Mars rotası sürekli",
            "Yerel yönetim, eğitim, sanat ve müzik endüstrisi",
            "İlk 'Mars doğumlu' kuşak — gerçek bir koloni kültürü",
        ],
        "astra": "Astra, Mars doğumlu DJ'lerin ilk neslini yetiştirir. 🙂",
    },
]

# MARS temalı müzik komutları (Beat Studio ile üretilebilir)
MARS_BEATS = [
    "130 bpm mars beat",
    "128 bpm space house",
    "140 bpm orbit techno",
    "135 bpm dark industrial mars",
]


def mars_mission_brief() -> str:
    """Full Mars mission plan as readable text."""
    lines = [
        "🚀 ASTRA — MARS GÖREVİ: KOLONİ PLANI",
        "=" * 50,
    ]
    for phase in MARS_PLAN:
        lines.append("")
        lines.append(f"[{phase['stage']}] {phase['title']} ({phase['years']})")
        for task in phase["tasks"]:
            lines.append(f"   • {task}")
        lines.append(f"   🎧 Astra: {phase['astra']}")
    lines.append("")
    lines.append("🎵 Mars'ta çalacak ilk parçalar: " + ", ".join(MARS_BEATS))
    return "\n".join(lines)


def mars_quick_answer() -> str:
    """Short summary — first 30 seconds on Mars."""
    return (
        "Mars'ta yaşam 4 fazda kurulur: "
        "(1) Kargo/rover ile su buzu ve enerji haritası çıkar, "
        "(2) Yeraltı modülü kur — radyasyon kalkanı + CO2'den oksijen üret, "
        "(3) Sera gazıyla atmosferi kalınlaştır (küresel ısınma isteyerek!), "
        "(4) Regolit 3D baskı ile şehir kur ve ilk Mars doğumlu nesli yetiştir. "
        "Astra bu yolda koloninin sinir sistemi ve ilk müziğini üretecek. 🚀"
    )


def handle_mars_query(text: str) -> dict:
    """
    Handle a Mars-related query.
    Returns {'reply': str, 'action': str, 'result': dict}.
    """
    lower = text.lower()

    # Mars beat / müzik isteği
    if any(w in lower for w in ["beat", "müzik", "muzik", "song", "melodi", "müzik yap", "çal"]):
        from app.ai.beat_studio import BeatStudio
        cmd = "130 bpm mars beat"
        try:
            studio = BeatStudio()
            result = studio.generate(cmd)
            played = studio.preview(result)
            return {
                "reply": (
                    f"🚀 İşte Mars ritmi! {result['genre'].title()} @ {result['bpm']} BPM "
                    f"({result['duration']:.1f}s). "
                    + ("Kulaklığını tak — şu an çalıyor! 🎧" if played else "Ses çıkışı yok ama beat hazır.")
                    + "\n\nDiğer Mars parçaları: 128 space house, 140 orbit techno, 135 dark industrial."
                ),
                "action": "mars_beat",
                "result": {"genre": result["genre"], "bpm": result["bpm"],
                           "duration": result["duration"], "played": played},
            }
        except Exception as exc:
            return {"reply": f"Mars beat üretilemedi: {exc}", "action": "mars_beat", "result": {}}

    # Ayrıntılı plan
    if any(w in lower for w in ["plan", "nasıl", "kurulur", "kur", "detay", "faz", "adım", "brief"]):
        return {
            "reply": mars_mission_brief(),
            "action": "mars_plan",
            "result": {"phases": len(MARS_PLAN)},
        }

    # Kısa özet
    return {
        "reply": mars_quick_answer(),
        "action": "mars_mission",
        "result": {"phases": len(MARS_PLAN)},
    }
