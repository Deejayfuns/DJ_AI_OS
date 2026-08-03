import sqlite3
import threading
import json


class AILibraryDB:

    def __init__(self, db_path="dj_ai_library.db"):

        self.lock = threading.Lock()

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.cursor = self.conn.cursor()

        self.create_tables()

    # =====================================================
    # TABLES
    # =====================================================
    def create_tables(self):

        with self.lock:

            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (

                id TEXT PRIMARY KEY,
                name TEXT,
                path TEXT,
                artist TEXT,
                duration INTEGER,

                bpm REAL,
                key TEXT,
                camelot TEXT,

                genre TEXT,
                parent_genre TEXT,
                subgenre TEXT,
                mood TEXT,
                role TEXT,
                quality TEXT,
                confidence REAL,
                discovery_status TEXT,
                matched_signals TEXT,
                assistant_message TEXT,
                suggested_filename TEXT,
                identity_key TEXT,
                duplicate_status TEXT,
                duplicate_confidence REAL,
                duplicate_match TEXT,
                recommended_duplicate_action TEXT,
                doctor_message TEXT,
                research_status TEXT,
                research_query TEXT,
                research_links TEXT,
                research_message TEXT,
                artwork_status TEXT,
                album_art_url TEXT,
                album_art_path TEXT,
                hit_status TEXT,
                release_year TEXT,
                label TEXT,
                external_metadata TEXT,
                archived_path TEXT,
                content_fingerprint TEXT,
                archive_status TEXT,

                energy REAL,
                brightness REAL,
                roughness REAL,
                danceability REAL,
                drop_strength REAL,
                waveform TEXT,
                analysis_status TEXT,
                analysis_error TEXT,

                bitrate INTEGER
                ,
                file_size INTEGER,
                ai_ear_score REAL,
                rhythmic_density REAL,
                vocal_risk REAL,
                intro_outro_mixability REAL,
                arrangement_score REAL,
                crowd_energy_role TEXT,
                ai_ear_summary TEXT
                ,
                phrase_points TEXT
                ,
                bpm_original REAL,
                bpm_correction TEXT,
                tempo_confidence REAL,
                tempo_warning TEXT,
                heart_score REAL,
                emotional_color TEXT,
                crowd_moment TEXT,
                heart_advice TEXT,
                version_type TEXT

            )
            """)

            self.migrate_tracks_table()
            self.create_indexes()
            self.conn.commit()

    def migrate_tracks_table(self):

        self.cursor.execute("PRAGMA table_info(tracks)")
        existing = {row[1] for row in self.cursor.fetchall()}

        migrations = {
            "artist": "TEXT",
            "duration": "INTEGER",
            "camelot": "TEXT",
            "parent_genre": "TEXT",
            "subgenre": "TEXT",
            "role": "TEXT",
            "quality": "TEXT",
            "confidence": "REAL",
            "discovery_status": "TEXT",
            "matched_signals": "TEXT",
            "assistant_message": "TEXT",
            "suggested_filename": "TEXT",
            "identity_key": "TEXT",
            "duplicate_status": "TEXT",
            "duplicate_confidence": "REAL",
            "duplicate_match": "TEXT",
            "recommended_duplicate_action": "TEXT",
            "doctor_message": "TEXT",
            "research_status": "TEXT",
            "research_query": "TEXT",
            "research_links": "TEXT",
            "research_message": "TEXT",
            "artwork_status": "TEXT",
            "album_art_url": "TEXT",
            "album_art_path": "TEXT",
            "hit_status": "TEXT",
            "release_year": "TEXT",
            "label": "TEXT",
            "external_metadata": "TEXT",
            "archived_path": "TEXT",
            "content_fingerprint": "TEXT",
            "archive_status": "TEXT",
            "file_size": "INTEGER",
            "roughness": "REAL",
            "danceability": "REAL",
            "drop_strength": "REAL",
            "waveform": "TEXT",
            "analysis_status": "TEXT",
            "analysis_error": "TEXT",
            "ai_ear_score": "REAL",
            "rhythmic_density": "REAL",
            "vocal_risk": "REAL",
            "intro_outro_mixability": "REAL",
            "arrangement_score": "REAL",
            "crowd_energy_role": "TEXT",
            "ai_ear_summary": "TEXT",
            "phrase_points": "TEXT",
            "bpm_original": "REAL",
            "bpm_correction": "TEXT",
            "tempo_confidence": "REAL",
            "tempo_warning": "TEXT",
            "heart_score": "REAL",
            "emotional_color": "TEXT",
            "crowd_moment": "TEXT",
            "heart_advice": "TEXT",
            "version_type": "TEXT",
        }

        for column, column_type in migrations.items():
            if column not in existing:
                self.cursor.execute(
                    f"ALTER TABLE tracks ADD COLUMN {column} {column_type}"
                )

    def create_indexes(self):

        try:
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_content_fingerprint "
                "ON tracks(content_fingerprint)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_archive_status "
                "ON tracks(archive_status)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_version_type "
                "ON tracks(version_type)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_genre "
                "ON tracks(genre)"
            )
        except Exception:
            pass  # Index creation is best-effort

    # =====================================================
    # SAVE TRACK (UPSERT SAFE)
    # =====================================================
    def save_track(self, track):

        with self.lock:

            self.cursor.execute("""
            INSERT OR REPLACE INTO tracks (
                id, name, path, artist, duration,
                bpm, key, camelot,
                genre, parent_genre, subgenre,
                mood, role, quality, confidence,
                discovery_status, matched_signals, assistant_message,
                suggested_filename, identity_key, duplicate_status,
                duplicate_confidence, duplicate_match,
                recommended_duplicate_action, doctor_message,
                research_status, research_query, research_links,
                research_message, artwork_status, album_art_url,
                album_art_path, hit_status, release_year, label,
                external_metadata, archived_path, content_fingerprint, archive_status,
                energy, brightness, roughness, danceability, drop_strength,
                waveform, analysis_status, analysis_error,
                bitrate, file_size,
                ai_ear_score, rhythmic_density, vocal_risk,
                intro_outro_mixability, arrangement_score,
                crowd_energy_role, ai_ear_summary, phrase_points,
                bpm_original, bpm_correction, tempo_confidence, tempo_warning,
                heart_score, emotional_color, crowd_moment, heart_advice,
                version_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (

                track.get("id"),
                track.get("name"),
                track.get("path", track.get("id")),
                track.get("artist", "UNKNOWN"),
                int(track.get("duration", 0) or 0),

                float(track.get("bpm", 0) or 0),
                track.get("key", ""),
                track.get("camelot", track.get("key", "")),

                track.get("genre", ""),
                track.get("parent_genre", ""),
                track.get("subgenre", ""),
                track.get("mood", ""),
                track.get("role", ""),
                track.get("quality", ""),
                float(track.get("confidence", 0) or 0),
                track.get("discovery_status", ""),
                self.serialize_json(track.get("matched_signals", [])),
                track.get("assistant_message", ""),
                track.get("suggested_filename", ""),
                track.get("identity_key", ""),
                track.get("duplicate_status", ""),
                float(track.get("duplicate_confidence", 0) or 0),
                self.serialize_json(track.get("duplicate_match", {})),
                track.get("recommended_duplicate_action", ""),
                track.get("doctor_message", ""),
                track.get("research_status", ""),
                track.get("research_query", ""),
                self.serialize_json(track.get("research_links", {})),
                track.get("research_message", ""),
                track.get("artwork_status", ""),
                track.get("album_art_url", ""),
                track.get("album_art_path", ""),
                track.get("hit_status", ""),
                track.get("release_year", ""),
                track.get("label", ""),
                self.serialize_json(track.get("external_metadata", {})),
                track.get("archived_path", ""),
                track.get("content_fingerprint", ""),
                track.get("archive_status", ""),

                float(track.get("energy", 0) or 0),
                float(track.get("brightness", 0) or 0),
                float(track.get("roughness", 0) or 0),
                float(track.get("danceability", 0) or 0),
                float(track.get("drop_strength", 0) or 0),
                self.serialize_json(track.get("waveform", [])[:1024]),
                track.get("analysis_status", ""),
                track.get("analysis_error", ""),

                int(track.get("bitrate", 0) or 0),
                int(track.get("file_size", 0) or 0),
                float(track.get("ai_ear_score", 0) or 0),
                float(track.get("rhythmic_density", 0) or 0),
                float(track.get("vocal_risk", 0) or 0),
                float(track.get("intro_outro_mixability", 0) or 0),
                float(track.get("arrangement_score", 0) or 0),
                track.get("crowd_energy_role", ""),
                track.get("ai_ear_summary", ""),
                self.serialize_json(track.get("phrase_points", [])),
                float(track.get("bpm_original", track.get("bpm", 0)) or 0),
                track.get("bpm_correction", ""),
                float(track.get("tempo_confidence", 0) or 0),
                track.get("tempo_warning", ""),
                float(track.get("heart_score", 0) or 0),
                track.get("emotional_color", ""),
                track.get("crowd_moment", ""),
                track.get("heart_advice", ""),
                track.get("version_type", "")

            ))

            self.conn.commit()

    def serialize_json(self, value):

        if isinstance(value, str):
            return value

        try:
            return json.dumps(value)
        except Exception:
            return "[]"

    # =====================================================
    # BATCH SAVE (multiple tracks, single commit)
    # =====================================================
    def save_many_tracks(self, tracks):

        if not tracks:
            return

        with self.lock:
            for track in tracks:
                self._save_track_unsafe(track)

            self.conn.commit()

    def _save_track_unsafe(self, track):
        """Insert/replace a track without acquiring the lock (for batch use)."""

        self.cursor.execute("""
        INSERT OR REPLACE INTO tracks (
            id, name, path, artist, duration,
            bpm, key, camelot,
            genre, parent_genre, subgenre,
            mood, role, quality, confidence,
            discovery_status, matched_signals, assistant_message,
            suggested_filename, identity_key, duplicate_status,
            duplicate_confidence, duplicate_match,
            recommended_duplicate_action, doctor_message,
            research_status, research_query, research_links,
            research_message, artwork_status, album_art_url,
            album_art_path, hit_status, release_year, label,
            external_metadata, archived_path, content_fingerprint, archive_status,
            energy, brightness, roughness, danceability, drop_strength,
            waveform, analysis_status, analysis_error,
            bitrate, file_size,
            ai_ear_score, rhythmic_density, vocal_risk,
            intro_outro_mixability, arrangement_score,
            crowd_energy_role, ai_ear_summary, phrase_points,
            bpm_original, bpm_correction, tempo_confidence, tempo_warning,
            heart_score, emotional_color, crowd_moment, heart_advice,
            version_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            track.get("id"),
            track.get("name"),
            track.get("path", track.get("id")),
            track.get("artist", "UNKNOWN"),
            int(track.get("duration", 0) or 0),
            float(track.get("bpm", 0) or 0),
            track.get("key", ""),
            track.get("camelot", track.get("key", "")),
            track.get("genre", ""),
            track.get("parent_genre", ""),
            track.get("subgenre", ""),
            track.get("mood", ""),
            track.get("role", ""),
            track.get("quality", ""),
            float(track.get("confidence", 0) or 0),
            track.get("discovery_status", ""),
            self.serialize_json(track.get("matched_signals", [])),
            track.get("assistant_message", ""),
            track.get("suggested_filename", ""),
            track.get("identity_key", ""),
            track.get("duplicate_status", ""),
            float(track.get("duplicate_confidence", 0) or 0),
            self.serialize_json(track.get("duplicate_match", {})),
            track.get("recommended_duplicate_action", ""),
            track.get("doctor_message", ""),
            track.get("research_status", ""),
            track.get("research_query", ""),
            self.serialize_json(track.get("research_links", {})),
            track.get("research_message", ""),
            track.get("artwork_status", ""),
            track.get("album_art_url", ""),
            track.get("album_art_path", ""),
            track.get("hit_status", ""),
            track.get("release_year", ""),
            track.get("label", ""),
            self.serialize_json(track.get("external_metadata", {})),
            track.get("archived_path", ""),
            track.get("content_fingerprint", ""),
            track.get("archive_status", ""),
            float(track.get("energy", 0) or 0),
            float(track.get("brightness", 0) or 0),
            float(track.get("roughness", 0) or 0),
            float(track.get("danceability", 0) or 0),
            float(track.get("drop_strength", 0) or 0),
            self.serialize_json(track.get("waveform", [])[:1024]),
            track.get("analysis_status", ""),
            track.get("analysis_error", ""),
            int(track.get("bitrate", 0) or 0),
            int(track.get("file_size", 0) or 0),
            float(track.get("ai_ear_score", 0) or 0),
            float(track.get("rhythmic_density", 0) or 0),
            float(track.get("vocal_risk", 0) or 0),
            float(track.get("intro_outro_mixability", 0) or 0),
            float(track.get("arrangement_score", 0) or 0),
            track.get("crowd_energy_role", ""),
            track.get("ai_ear_summary", ""),
            self.serialize_json(track.get("phrase_points", [])),
            float(track.get("bpm_original", track.get("bpm", 0)) or 0),
            track.get("bpm_correction", ""),
            float(track.get("tempo_confidence", 0) or 0),
            track.get("tempo_warning", ""),
            float(track.get("heart_score", 0) or 0),
            track.get("emotional_color", ""),
            track.get("crowd_moment", ""),
            track.get("heart_advice", ""),
            track.get("version_type", "")
        ))

    # =====================================================
    # LOAD ALL (DICT FIXED)
    # =====================================================
    def load_all(self):

        with self.lock:

            self.cursor.execute("SELECT * FROM tracks")

            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]

        return [
            self.deserialize_track(dict(zip(columns, row)))
            for row in rows
        ]

    # =====================================================
    # SEARCH ENGINE (DJ STYLE)
    # =====================================================
    def search_by_genre(self, genre):

        with self.lock:

            self.cursor.execute(
                "SELECT * FROM tracks WHERE genre=?",
                (genre,)
            )

            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]

        return [
            self.deserialize_track(dict(zip(columns, row)))
            for row in rows
        ]

    def deserialize_track(self, track):

        for field in (
            "waveform",
            "matched_signals",
            "duplicate_match",
            "research_links",
            "external_metadata",
            "phrase_points"
        ):

            value = track.get(field)

            if isinstance(value, str):
                try:
                    track[field] = json.loads(value)
                except Exception:
                    track[field] = []

        return track

    # =====================================================
    # CLOSE
    # =====================================================
    def close(self):

        with self.lock:
            self.conn.close()
