import json
import os
import re
from collections import defaultdict


class GenreKnowledgeBase:

    def __init__(self, discovery_file="app/config/discovered_genres.json"):

        self.discovery_file = discovery_file
        self.taxonomy = self.build_taxonomy()
        self.discovered = self.load_discovered()

    def build_taxonomy(self):

        return {
            "HOUSE": {
                "subgenres": [
                    "AFRO HOUSE", "AMAPIANO", "DEEP HOUSE", "ORGANIC HOUSE",
                    "MELODIC HOUSE", "PROGRESSIVE HOUSE", "TECH HOUSE",
                    "CLASSIC HOUSE", "FUNKY HOUSE", "JACKIN HOUSE",
                    "SOULFUL HOUSE", "DISCO HOUSE", "NU DISCO",
                    "MINIMAL HOUSE", "ELECTRO HOUSE", "BASS HOUSE",
                    "FUTURE HOUSE", "TROPICAL HOUSE", "LATIN HOUSE"
                ],
                "keywords": [
                    "house", "afro", "amapiano", "deep", "organic",
                    "melodic house", "progressive", "tech house",
                    "disco", "funky", "soulful", "latin house"
                ],
                "bpm": (115, 130)
            },
            "TECHNO": {
                "subgenres": [
                    "MELODIC TECHNO", "PEAK TIME TECHNO", "DRIVING TECHNO",
                    "MINIMAL TECHNO", "RAW TECHNO", "DUB TECHNO",
                    "DETROIT TECHNO", "HARD TECHNO", "ACID TECHNO",
                    "INDUSTRIAL TECHNO", "HYPNOTIC TECHNO"
                ],
                "keywords": [
                    "techno", "melodic techno", "afterlife", "anyma",
                    "tale of us", "argy", "peak time", "raw", "dub techno",
                    "acid techno", "hard techno", "industrial"
                ],
                "bpm": (120, 150)
            },
            "TRANCE": {
                "subgenres": [
                    "UPLIFTING TRANCE", "PROGRESSIVE TRANCE", "PSYTRANCE",
                    "GOA TRANCE", "VOCAL TRANCE", "TECH TRANCE"
                ],
                "keywords": [
                    "trance", "uplifting", "psytrance", "goa",
                    "armin", "anjuna", "vocal trance"
                ],
                "bpm": (128, 145)
            },
            "BASS": {
                "subgenres": [
                    "DRUM AND BASS", "JUNGLE", "DUBSTEP", "UK GARAGE",
                    "2-STEP", "BREAKS", "BASSLINE", "GRIME"
                ],
                "keywords": [
                    "drum and bass", "dnb", "jungle", "dubstep",
                    "garage", "2step", "2-step", "breaks", "grime"
                ],
                "bpm": (130, 180)
            },
            "HIP HOP": {
                "subgenres": [
                    "HIP HOP", "TRAP", "DRILL", "BOOM BAP", "RNB",
                    "AFROBEATS", "REGGAETON", "DANCEHALL"
                ],
                "keywords": [
                    "hip hop", "hiphop", "trap", "drill", "boom bap",
                    "rnb", "r&b", "afrobeats", "reggaeton", "dancehall"
                ],
                "bpm": (70, 110)
            },
            "COMMERCIAL": {
                "subgenres": [
                    "POP", "DANCE POP", "EDM", "BIG ROOM",
                    "FUTURE RAVE", "MAINSTAGE", "REMIX", "MASHUP"
                ],
                "keywords": [
                    "pop", "edm", "big room", "mainstage", "future rave",
                    "remix", "mashup", "bootleg", "radio edit"
                ],
                "bpm": (95, 135)
            },
            "LATIN": {
                "subgenres": [
                    "LATIN", "REGGAETON", "MOOMBAHTON", "SALSA",
                    "BACHATA", "CUMBIA", "BAILE FUNK"
                ],
                "keywords": [
                    "latin", "reggaeton", "moombahton", "salsa",
                    "bachata", "cumbia", "baile funk"
                ],
                "bpm": (85, 130)
            },
            "WEDDING & EVENT": {
                "subgenres": [
                    "KINA GECESI", "OYUN HAVASI", "HALAY", "CIFTETELLI",
                    "ROMAN HAVASI", "ANKARA HAVASI", "KARSILAMA",
                    "ZEYBEK", "HORON", "DAMAT HALAYI", "GELIN CIKIS",
                    "ILK DANS", "TAKI TORENI", "DUGUN POP",
                    "TURKISH WEDDING", "ARABESK", "TURKCE POP"
                ],
                "keywords": [
                    "kina", "kına", "kina gecesi", "kına gecesi",
                    "oyun havasi", "oyun havası", "halay", "ciftetelli",
                    "çiftetelli", "roman", "ankara havasi", "ankara havası",
                    "karsilama", "karşılama", "zeybek", "horon",
                    "damat halayi", "damat halayı", "gelin cikis",
                    "gelin çıkış", "ilk dans", "taki toreni", "takı töreni",
                    "dugun", "düğün", "turkce pop", "türkçe pop",
                    "arabesk", "fantazi"
                ],
                "bpm": (70, 150)
            },
            "CHILL": {
                "subgenres": [
                    "AMBIENT", "DOWNTEMPO", "LOUNGE", "CHILLOUT",
                    "LOFI", "TRIP HOP", "NU JAZZ"
                ],
                "keywords": [
                    "ambient", "downtempo", "lounge", "chillout",
                    "lofi", "lo-fi", "trip hop", "nu jazz"
                ],
                "bpm": (60, 115)
            },
            "ROCK": {
                "subgenres": [
                    "ROCK", "INDIE ROCK", "ALTERNATIVE", "PUNK",
                    "METAL", "FUNK ROCK"
                ],
                "keywords": [
                    "rock", "indie", "alternative", "punk", "metal"
                ],
                "bpm": (80, 150)
            },
        }

    def load_discovered(self):

        if not os.path.exists(self.discovery_file):
            return {}

        try:
            with open(self.discovery_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_discovered(self):

        os.makedirs(os.path.dirname(self.discovery_file), exist_ok=True)

        with open(self.discovery_file, "w", encoding="utf-8") as f:
            json.dump(self.discovered, f, indent=4, ensure_ascii=True)

    def classify(self, track):

        text = self.build_search_text(track)
        bpm = float(track.get("bpm", 0) or 0)
        energy = float(track.get("energy", 0) or 0)

        scores = defaultdict(float)
        matched = defaultdict(list)

        for parent, data in self.taxonomy.items():
            low, high = data["bpm"]

            if bpm and low <= bpm <= high:
                scores[parent] += 0.25
                matched[parent].append("bpm")

            for keyword in data["keywords"]:
                if self.keyword_in_text(keyword, text):
                    scores[parent] += 0.45
                    matched[parent].append(keyword)

            for subgenre in data["subgenres"]:
                if self.keyword_in_text(subgenre, text):
                    scores[parent] += 0.75
                    matched[parent].append(subgenre)

        if not scores:
            return self.discover_unknown(track, text, bpm, energy)

        parent = max(scores, key=scores.get)
        subgenre = self.pick_subgenre(parent, text, bpm, energy)
        confidence = min(1.0, scores[parent])

        if confidence < 0.35:
            return self.discover_unknown(track, text, bpm, energy)

        return {
            "parent_genre": parent,
            "genre": subgenre,
            "subgenre": subgenre,
            "confidence": round(confidence, 2),
            "discovery_status": "KNOWN",
            "matched_signals": list(dict.fromkeys(matched[parent])),
        }

    def build_search_text(self, track):

        parts = [
            track.get("name", ""),
            track.get("artist", ""),
            track.get("genre", ""),
            track.get("path", ""),
        ]

        return self.clean_text(" ".join(str(p) for p in parts))

    def clean_text(self, text):

        text = text.lower()
        text = re.sub(r"[^a-z0-9&+ ]+", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def keyword_in_text(self, keyword, text):

        keyword = self.clean_text(keyword)
        return keyword in text

    def pick_subgenre(self, parent, text, bpm, energy):

        data = self.taxonomy[parent]

        for subgenre in data["subgenres"]:
            if self.keyword_in_text(subgenre, text):
                return subgenre

        if parent == "HOUSE":
            if "afro" in text or "keinemusik" in text:
                return "AFRO HOUSE"
            if "deep" in text:
                return "DEEP HOUSE"
            if bpm >= 123 and energy >= 0.65:
                return "TECH HOUSE"

        if parent == "TECHNO":
            if "melodic" in text or "afterlife" in text:
                return "MELODIC TECHNO"
            if bpm >= 132 or energy >= 0.8:
                return "PEAK TIME TECHNO"

        if parent == "WEDDING & EVENT":
            wedding_map = [
                ("kina", "KINA GECESI"),
                ("kına", "KINA GECESI"),
                ("halay", "HALAY"),
                ("oyun hav", "OYUN HAVASI"),
                ("ciftetelli", "CIFTETELLI"),
                ("çiftetelli", "CIFTETELLI"),
                ("roman", "ROMAN HAVASI"),
                ("ankara", "ANKARA HAVASI"),
                ("zeybek", "ZEYBEK"),
                ("horon", "HORON"),
                ("ilk dans", "ILK DANS"),
                ("gelin", "GELIN CIKIS"),
                ("damat", "DAMAT HALAYI"),
                ("arabesk", "ARABESK"),
                ("turkce pop", "TURKCE POP"),
                ("türkçe pop", "TURKCE POP"),
            ]

            for needle, subgenre in wedding_map:
                if needle in text:
                    return subgenre

        return data["subgenres"][0]

    def discover_unknown(self, track, text, bpm, energy):

        signature = self.build_discovery_signature(text, bpm, energy)

        if signature not in self.discovered:
            self.discovered[signature] = {
                "label": f"DISCOVERED_STYLE_{len(self.discovered) + 1}",
                "count": 0,
                "examples": [],
                "bpm_min": bpm,
                "bpm_max": bpm,
                "energy_avg": energy,
                "needs_review": True,
            }

        item = self.discovered[signature]
        item["count"] += 1
        item["bpm_min"] = min(item["bpm_min"] or bpm, bpm or item["bpm_min"])
        item["bpm_max"] = max(item["bpm_max"] or bpm, bpm or item["bpm_max"])
        item["energy_avg"] = round(
            ((item["energy_avg"] * (item["count"] - 1)) + energy) /
            item["count"],
            3
        )

        example = track.get("name", track.get("path", "UNKNOWN"))

        if example not in item["examples"] and len(item["examples"]) < 5:
            item["examples"].append(example)

        self.save_discovered()

        return {
            "parent_genre": "UNKNOWN",
            "genre": item["label"],
            "subgenre": item["label"],
            "confidence": 0.2,
            "discovery_status": "DISCOVERED",
            "matched_signals": [signature],
        }

    def build_discovery_signature(self, text, bpm, energy):

        tokens = [
            token for token in text.split()
            if len(token) > 3
            and token not in {"original", "extended", "mix", "remix"}
        ][:4]

        bpm_band = "unknown_bpm"

        if bpm:
            bpm_band = f"{int(bpm // 5) * 5}-{int(bpm // 5) * 5 + 4}"

        energy_band = "low"

        if energy >= 0.75:
            energy_band = "high"
        elif energy >= 0.45:
            energy_band = "mid"

        return "_".join(tokens + [bpm_band, energy_band]) or "unknown_style"
