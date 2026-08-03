import json
import os
import re
from datetime import datetime


class AssistantMemory:

    def __init__(self, file="astra_memory.json"):

        self.file = file
        self.data = self.load()
        self.data.setdefault("history", [])
        self.data.setdefault("terms", {})
        self.data.setdefault("unknown", [])

    def load(self):

        if not os.path.exists(self.file):
            return {}

        try:
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("⚠ ASTRA MEMORY FILE CORRUPTED — RESETTING")
            return {}

    def save(self):

        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def remember(self, speaker, text):

        entry = {
            "timestamp": str(datetime.now()),
            "speaker": speaker,
            "text": str(text or "").strip()
        }

        if not entry["text"]:
            return

        self.data["history"].append(entry)

        if len(self.data["history"]) > 300:
            self.data["history"] = self.data["history"][-300:]

        self.save()

    def learn_term(self, term, meaning):

        key = self.normalize_term(term)

        if not key or not meaning:
            return

        self.data["terms"][key] = str(meaning).strip()

        if key in self.data["unknown"]:
            self.data["unknown"].remove(key)

        self.save()

    def get_term(self, term):

        return self.data["terms"].get(self.normalize_term(term))

    def known_terms(self):

        return list(self.data["terms"].keys())

    def log_unknown_terms(self, terms):

        for term in terms:
            key = self.normalize_term(term)
            if key and key not in self.data["terms"] and key not in self.data["unknown"]:
                self.data["unknown"].append(key)

        self.save()

    def get_unknown_terms(self):

        return list(self.data["unknown"])

    def normalize_term(self, term):

        if not term:
            return ""

        text = str(term or "").lower()
        text = re.sub(r"[^a-z0-9ığüşöç]+", " ", text)
        text = " ".join(text.split())
        return text.strip()

    def extract_candidate_terms(self, text):

        if not text:
            return []

        normalized = self.normalize_term(text)
        words = normalized.split()
        stop_words = {
            "ve", "bir", "bu", "o", "da", "de", "mi", "mu", "ya", "ile",
            "için", "ne", "nasıl", "daha", "gibi", "ben", "sen", "biz",
            "sana", "seni", "içinde", "kendi", "çok", "şu", "şunu",
            "ama", "veya", "ya", "olarak", "yerine", "stüdyo", "sahne",
            "müzik", "parça", "şarkı", "track", "set", "remix",
        }

        candidates = []

        for word in words:
            if len(word) < 3:
                continue
            if word in stop_words:
                continue
            if word.isdigit():
                continue
            if self.get_term(word):
                continue
            candidates.append(word)

        return list(dict.fromkeys(candidates))

    def recent_summary(self):

        recent = self.data["history"][-6:]
        summary = []

        for item in recent:
            prefix = "Kullanıcı" if item["speaker"] == "user" else "Astra"
            summary.append(f"{prefix}: {item['text']}")

        return " | ".join(summary)
