# DJ AI OS Development Roadmap

## Product Vision

DJ AI OS is a desktop-first music library assistant for professional DJs.
Its first job is to reduce the time spent sorting large music folders by
learning genre, energy, BPM, key, quality, and DJ usefulness from audio files
and file metadata.

The demo version targets up to 1000 archived tracks. The paid version unlocks
larger libraries, licensing, and update delivery for new music intelligence.

## MVP Demo

1. Scan a folder of MP3/WAV/FLAC files.
2. Extract safe metadata and lightweight audio intelligence.
3. Classify tracks by genre, mood, energy, BPM, key, quality, and role.
4. Save analyzed tracks into SQLite.
5. Show the archive in the desktop UI.
6. Generate DJ-ready set suggestions from the archive.
7. Enforce a 1000-track demo limit when no valid license exists.

## Pro Version

1. License key validation per machine.
2. Paid plans with `max_tracks` limits.
3. First 3 months of update access included through `updates_until`.
4. Update packages for genre knowledge, keyword models, and set-building rules.
5. Optional Rekordbox/Serato export workflows.

## Long-Term AI Direction

1. Build a music ear that learns how a professional DJ organizes tracks.
2. Improve genre detection from both audio features and DJ-world keywords.
3. Learn from skipped, replayed, selected, and exported tracks.
4. Recommend crates and set flow by warmup, groove, peak time, closing, and mood.
5. Eventually support live assistant behavior with controller/DJ software sync.

## Immediate Engineering Priorities

1. Stabilize the archive pipeline.
2. Unify scanner, analyzer, classifier, and database fields.
3. Add proper UI views for Library, Analyze, Set Builder, License, and Settings.
4. Add import/export actions for DJ workflows.
5. Add smoke tests for demo limit, classifier, set builder, and database save/load.
