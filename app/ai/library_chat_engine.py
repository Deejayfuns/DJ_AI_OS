class LibraryChatEngine:

    def build_message(self, track_name, decision):

        return {
            "title": "Duplicate Detected",
            "message": f"'{track_name}' zaten kütüphanende var ama farklı kalite bulundu.",
            "options": [
                "🗑 Eskiyi sil, yeniyi kullan",
                "📁 Ayrı klasöre taşı (Duplicates)",
                "🔁 Hiçbir şey yapma"
            ],
            "decision": decision
        }
