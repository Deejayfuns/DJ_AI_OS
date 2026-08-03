"""MFCC-based genre classifier using sklearn.

Replaces the keyword heuristics with real audio feature classification.
Trains on existing labeled tracks (from GenreKnowledgeBase labels),
extracts MFCC features via AudioAnalyzer, and predicts genre.

Fallback: if no trained model exists, returns None so MusicAI
can fall back to the existing keyword heuristics.
"""

import os
import json

try:
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "app", "config")
MODEL_PATH = os.path.join(MODEL_DIR, "genre_classifier.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "classifier_metadata.json")


class MFCCClassifier:

    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_map = {}  # index -> genre name
        self.reverse_map = {}  # genre name -> index
        self._loaded = False

    def load(self):
        """Load a pre-trained model from disk."""
        if not SKLEARN_AVAILABLE:
            return False

        if not os.path.exists(MODEL_PATH):
            return False

        try:
            self.model = joblib.load(MODEL_PATH)
            self.scaler = joblib.load(MODEL_PATH.replace(".pkl", "_scaler.pkl"))

            with open(METADATA_PATH, "r") as f:
                meta = json.load(f)
            self.label_map = {int(k): v for k, v in meta.get("labels", {}).items()}
            self.reverse_map = {v: k for k, v in self.label_map.items()}
            self._loaded = True
            return True
        except Exception:
            return False

    def predict(self, features):
        """Predict genre from audio features dict.

        Args:
            features: dict from AudioAnalyzer.analyze() containing
                      mfcc, energy, brightness, danceability, etc.

        Returns:
            dict with genre, confidence, or None if model not available.
        """
        if not self._loaded:
            return None

        try:
            feature_vector = self._extract_vector(features)
            if feature_vector is None:
                return None

            X = self.scaler.transform([feature_vector])
            prediction = self.model.predict(X)[0]
            proba = self.model.predict_proba(X)[0]

            genre = self.label_map.get(int(prediction), "UNKNOWN")
            confidence = float(max(proba))

            return {
                "genre": genre,
                "confidence": round(confidence, 3),
                "source": "MFCC_ML",
            }
        except Exception:
            return None

    def train(self, tracks, audio_features_map):
        """Train the classifier on labeled tracks.

        Args:
            tracks: list of track dicts with 'genre' labels
            audio_features_map: dict mapping track_id -> AudioAnalyzer features

        Returns:
            dict with training stats
        """
        if not SKLEARN_AVAILABLE:
            return {"ok": False, "error": "sklearn not available"}

        X = []
        y = []

        for track in tracks:
            track_id = track.get("id", "")
            genre = track.get("genre", "")
            features = audio_features_map.get(track_id)

            if not features or not genre:
                continue

            vector = self._extract_vector(features)
            if vector is None:
                continue

            X.append(vector)
            y.append(genre)

        if len(X) < 20:
            return {"ok": False, "error": f"Not enough training data ({len(X)} samples, need 20+)"}

        # Build label mapping
        unique_genres = sorted(set(y))
        self.label_map = {i: g for i, g in enumerate(unique_genres)}
        self.reverse_map = {g: i for i, g in self.label_map.items()}
        y_encoded = [self.reverse_map[g] for g in y]

        X = np.array(X)
        y_array = np.array(y_encoded)

        # Train
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        self.model.fit(X_scaled, y_array)

        # Save
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.scaler, MODEL_PATH.replace(".pkl", "_scaler.pkl"))

        with open(METADATA_PATH, "w") as f:
            json.dump({
                "labels": {str(k): v for k, v in self.label_map.items()},
                "n_samples": len(X),
                "n_classes": len(unique_genres),
                "accuracy": float(self.model.score(X_scaled, y_array)),
            }, f, indent=2)

        self._loaded = True

        return {
            "ok": True,
            "n_samples": len(X),
            "n_classes": len(unique_genres),
            "accuracy": round(float(self.model.score(X_scaled, y_array)), 3),
            "genres": unique_genres[:10],
        }

    def _extract_vector(self, features):
        """Extract a fixed-size feature vector from AudioAnalyzer output."""
        if not features:
            return None

        mfcc = features.get("mfcc", [])
        if not mfcc or len(mfcc) < 13:
            # Use available features as fallback
            vector = [
                float(features.get("energy", 0) or 0),
                float(features.get("brightness", 0) or 0),
                float(features.get("roughness", 0) or 0),
                float(features.get("danceability", 0) or 0),
                float(features.get("drop_strength", 0) or 0),
            ]
            # Pad to 13
            vector.extend([0.0] * (13 - len(vector)))
        else:
            vector = [float(x) for x in mfcc[:13]]

        # Add derived features
        vector.extend([
            float(features.get("energy", 0) or 0),
            float(features.get("brightness", 0) or 0),
            float(features.get("roughness", 0) or 0),
            float(features.get("danceability", 0) or 0),
            float(features.get("drop_strength", 0) or 0),
        ])

        return vector

    def is_available(self):
        return self._loaded and SKLEARN_AVAILABLE
