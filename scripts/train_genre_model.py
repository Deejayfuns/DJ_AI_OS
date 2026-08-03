"""Train the MFCC genre classifier on existing audio files.

Usage (from repo root):
    python scripts/train_genre_model.py [audio_folder]

If no folder is given, uses the DJ_LIBRARY_OUTPUT archive.
The script:
1. Scans for audio files with valid genre labels in the DB
2. Extracts MFCC features via AudioAnalyzer
3. Trains GradientBoostingClassifier
4. Saves model to app/config/genre_classifier.pkl

Run this after scanning a music library to improve genre classification.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.mfcc_classifier import MFCCClassifier
from data.db.ai_library_db import AILibraryDB


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "DJ_LIBRARY_OUTPUT"

    print(f"[TRAIN] Loading database...")
    db = AILibraryDB()
    tracks = db.load_all()
    print(f"[TRAIN] {len(tracks)} tracks in database")

    # Filter: only tracks with genre labels and existing audio files
    labeled = []
    for track in tracks:
        genre = track.get("genre", "")
        path = track.get("archived_path") or track.get("path") or ""

        if not genre or genre.startswith("DISCOVERED") or genre == "UNKNOWN":
            continue

        if path and os.path.exists(path):
            labeled.append(track)

    print(f"[TRAIN] {len(labeled)} labeled tracks with existing audio files")

    if len(labeled) < 20:
        print(f"[TRAIN] Need at least 20 labeled tracks. Found {len(labeled)}.")
        print("[TRAIN] Scan a music folder first to build the database.")
        return

    analyzer = AudioAnalyzer()
    features_map = {}
    errors = 0

    print(f"[TRAIN] Extracting MFCC features...")
    for i, track in enumerate(labeled):
        track_id = track.get("id", "")
        path = track.get("archived_path") or track.get("path", "")

        try:
            features = analyzer.analyze(path)
            if features and features.get("analysis_status") == "FULL":
                features_map[track_id] = features
            else:
                errors += 1
        except Exception as e:
            errors += 1

        if (i + 1) % 50 == 0:
            print(f"[TRAIN]   {i + 1}/{len(labeled)} processed, {len(features_map)} OK, {errors} errors")

    print(f"[TRAIN] Feature extraction complete: {len(features_map)} features from {len(labeled)} tracks")

    if len(features_map) < 20:
        print(f"[TRAIN] Not enough valid features ({len(features_map)}). Need at least 20.")
        return

    print(f"[TRAIN] Training MFCC classifier...")
    classifier = MFCCClassifier()
    result = classifier.train(labeled, features_map)

    if result.get("ok"):
        print(f"[TRAIN] Model trained successfully!")
        print(f"[TRAIN]   Samples: {result['n_samples']}")
        print(f"[TRAIN]   Classes: {result['n_classes']}")
        print(f"[TRAIN]   Accuracy: {result['accuracy']:.1%}")
        print(f"[TRAIN]   Genres: {', '.join(result['genres'][:8])}")
        print(f"[TRAIN]   Model saved to: app/config/genre_classifier.pkl")
    else:
        print(f"[TRAIN] Training failed: {result.get('error')}")


if __name__ == "__main__":
    main()
