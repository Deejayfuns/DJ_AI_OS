class LibraryChat:

    def build(self, old, new):

        return {
            "title": "Duplicate Detected",
            "message": (
                f"🎵 {old.get('name')} zaten kütüphanende var.\n\n"
                f"📦 Eski kalite: {old.get('bitrate',0)} kbps\n"
                f"🆕 Yeni kalite: {new.get('bitrate',0)} kbps\n\n"
                "Ne yapmak istersin?"
            ),
            "options": [
                "🗑 Eskiyi sil",
                "📁 Duplicate klasörüne taşı",
                "🔁 Yeni ile değiştir"
            ]
        }
