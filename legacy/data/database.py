import sqlite3
import os

DB_PATH = "data/dj_database.db"

class Database:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            path TEXT,
            filename TEXT,
            bpm INTEGER,
            key TEXT,
            genre TEXT,
            energy REAL,
            role TEXT,
            hit_score REAL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            action TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT,
            usage_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.conn.commit()

    def insert_track(self, data):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()
