class LibraryManager:

    def __init__(self, db):
        self.db = db

    # =========================================
    # SAVE LIBRARY
    # =========================================
    def add_track(self, track):

        if not track:
            return

        self.db.save_track(track)

    # =========================================
    # LOAD LIBRARY
    # =========================================
    def load(self):

        return self.db.load_all()

    # =========================================
    # SEARCH
    # =========================================
    def search_genre(self, genre):

        return self.db.search_by_genre(genre)
