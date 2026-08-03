class LibraryAssistant:

    def build_message(self, dup):

        old = dup["old"]
        new = dup["new"]

        return {
            "title": "Duplicate Found",
            "text": f"""
Aynı track bulundu:

🎵 {old['name']}

Ama farklı kalite mevcut:
- Eski: {old.get('bitrate', 0)} kbps
- Yeni: {new.get('bitrate', 0)} kbps
            """,

            "options": [
                "🗑 Eskiyi sil",
                "📁 Duplicate klasörüne taşı",
                "🔁 Yeni ile değiştir"
            ],

            "type": "duplicate_dialog"
        }
