import sqlite3
from collections import defaultdict


class DJMemory:

    def __init__(self):

        self.conn = sqlite3.connect("dj_memory.db")
        self.create_tables()

    # ---------------------------------------------------
    # TABLES
    # ---------------------------------------------------

    def create_tables(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plays (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            track_name TEXT,
            genre TEXT,
            bpm INTEGER,
            energy REAL,
            camelot TEXT,

            play_position INTEGER
        )
        """)

        self.conn.commit()

    # ---------------------------------------------------
    # SAVE PLAY
    # ---------------------------------------------------

    def log_play(self, track, position):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO plays (
            track_name,
            genre,
            bpm,
            energy,
            camelot,
            play_position
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            track.get("name"),
            track.get("genre"),
            track.get("bpm"),
            track.get("energy"),
            track.get("camelot"),
            position
        ))

        self.conn.commit()

    # ---------------------------------------------------
    # DJ STYLE ANALYSIS
    # ---------------------------------------------------

    def analyze_style(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT genre, AVG(play_position)
        FROM plays
        GROUP BY genre
        """)

        rows = cursor.fetchall()

        profile = {}

        for genre, avg_pos in rows:

            profile[genre] = {
                "avg_position": round(avg_pos, 2)
            }

        return profile

    # ---------------------------------------------------
    # ENERGY PROFILE
    # ---------------------------------------------------

    def energy_curve(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT AVG(energy), play_position
        FROM plays
        GROUP BY play_position
        ORDER BY play_position
        """)

        rows = cursor.fetchall()

        return [
            {
                "position": r[1],
                "avg_energy": round(r[0], 2)
            }
            for r in rows
        ]
