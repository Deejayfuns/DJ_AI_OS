import json
import os
import re


class KeywordEngine:

    def __init__(self):

        self.file = "app/config/genres.json"

        self.data = self.load_keywords()

    def load_keywords(self):

        default = {

            "MELODIC TECHNO": [
                "afterlife",
                "anyma",
                "argy",
                "melodic",
                "tale of us"
            ],

            "AFRO HOUSE": [
                "keinemusik",
                "afro",
                "moblack",
                "black coffee"
            ],

            "TECH HOUSE": [
                "cloonee",
                "tech house",
                "fisher",
                "solid grooves"
            ],

            "TRANCE": [
                "armin",
                "trance",
                "uplifting"
            ]
        }

        os.makedirs("app/config", exist_ok=True)

        if not os.path.exists(self.file):

            with open(self.file, "w") as f:
                json.dump(default, f, indent=4)

            return default

        with open(self.file, "r") as f:
            return json.load(f)

    def clean_text(self, text):

        text = text.lower()

        text = re.sub(r'[\(\)\[\]\-_]', ' ', text)

        return text

    def detect(self, filename):

        text = self.clean_text(filename)

        scores = {}

        for genre, keywords in self.data.items():

            score = 0

            for keyword in keywords:

                if keyword.lower() in text:
                    score += 1

            scores[genre] = score

        best = max(scores, key=scores.get)

        confidence = scores[best] / 5

        return {
            "genre": best,
            "confidence": confidence
        }
