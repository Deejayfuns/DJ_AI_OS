import uuid
import os
from app.ai.features import extract_features
from app.ai.classifier import AIClassifier
from app.core.organizer import Organizer

class Pipeline:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self.ai = AIClassifier()
        self.organizer = Organizer("DJ_AI_OUTPUT")

    def process(self, path):
        features = extract_features(path)
        features["path"] = path
        prediction = self.ai.predict(features, os.path.basename(path))
        copied_path = self.organizer.safe_copy(
            path,
            prediction
        )

        track_id = str(uuid.uuid4())

        data = (
            track_id,
            path,
            os.path.basename(path),
            prediction.get("bpm") or features.get("bpm"),
            prediction.get("key", ""),
            prediction["genre"],
            prediction["energy"],
            prediction["role"],
            prediction["hit_score"]
        )

        self.db.insert_track(data)

        self.logger.log(f"Processed: {path}")
        self.logger.log(f"Copied to: {copied_path}")

        return prediction
