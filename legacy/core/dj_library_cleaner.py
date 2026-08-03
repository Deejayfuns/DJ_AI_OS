import os
import hashlib
from mutagen import File


class DJLibraryCleaner:

    def __init__(self, audio_brain=None):
        self.brain = audio_brain

    # =====================================================
    # MAIN CLEAN PIPELINE
    # =====================================================
    def clean(self, tracks):

        seen = {}
        clean = []
        duplicates = []

        for track in tracks:

            path = track.get("id")

            if not path or not os.path.exists(path):
                continue

            file_hash = self.get_audio_hash(path)
            bitrate = self.get_bitrate(path)

            enriched = {
                **track,
                "bitrate": bitrate,
                "hash": file_hash
            }

            # -------------------------
            # NEW TRACK
            # -------------------------
            if file_hash not in seen:
                seen[file_hash] = enriched
                clean.append(enriched)
                continue

            # -------------------------
            # DUPLICATE FOUND
            # -------------------------
            existing = seen[file_hash]

            best = self.pick_better(existing, enriched)

            duplicate = enriched if best == existing else existing

            seen[file_hash] = best

            duplicates.append({
                "best": best,
                "duplicate": duplicate,
                "reason": self.explain_choice(best, duplicate)
            })

            # replace in clean list
            clean = [t for t in clean if t["id"] != duplicate["id"]]
            clean.append(best)

        return {
            "clean": clean,
            "duplicates": duplicates
        }

    # =====================================================
    # AI DUPLICATE RANKING (DJ INTELLIGENCE)
    # =====================================================
    def rank_duplicates(self, group):

        best = None
        best_score = -1

        for track in group.get("items", []):

            score = 0

            # bitrate quality
            bitrate = track.get("bitrate", 0)
            score += bitrate / 320

            # AI DJ score
            score += track.get("dj_score", 0)

            # energy preference
            score += track.get("energy", 0)

            if score > best_score:
                best_score = score
                best = track

        return best

    # =====================================================
    # QUALITY DECISION ENGINE
    # =====================================================
    def pick_better(self, a, b):

        a_score = self._quality_score(a)
        b_score = self._quality_score(b)

        return b if b_score > a_score else a

    def _quality_score(self, t):

        score = 0

        # bitrate is king
        score += t.get("bitrate", 0) / 320

        # AI brain score (if exists)
        score += t.get("dj_score", 0)

        # energy bonus (club relevance)
        score += t.get("energy", 0)

        return score

    # =====================================================
    # AUDIO HASH (FAST DUP DETECTION)
    # =====================================================
    def get_audio_hash(self, path):

        h = hashlib.md5()

        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)

        except Exception:
            return None

        return h.hexdigest()

    # =====================================================
    # BITRATE DETECTOR
    # =====================================================
    def get_bitrate(self, path):

        try:
            audio = File(path)

            if audio is None:
                return 0

            info = getattr(audio, "info", None)

            if not info:
                return 0

            bitrate = getattr(info, "bitrate", 0)

            return int(bitrate / 1000)

        except Exception:
            return 0

    # =====================================================
    # AI EXPLANATION LAYER
    # =====================================================
    def explain_choice(self, best, dup):

        return (
            f"AI selected higher quality version: "
            f"{best.get('bitrate',0)} kbps over {dup.get('bitrate',0)} kbps "
            f"(plus DJ score weighting)"
        )
