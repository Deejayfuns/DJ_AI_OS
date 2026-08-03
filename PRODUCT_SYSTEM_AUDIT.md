# DJ AI OS System Audit

## Current Truth

DJ AI OS has a strong prototype core: scanner, analyzer, genre intelligence,
duplicate review, set building, show planning, Rekordbox export, remix planning,
FL Studio handoff, and commercial licensing stubs exist.

The main product risk is not lack of features. The main risk is trust.
A professional DJ must trust that the app will never damage, duplicate, bury,
or confuse the music archive.

## Critical Archive Problems Found

1. Archive copy behavior used to create `_1`, `_2`, `_3` files when a target
   filename already existed. This can explode HDD usage and destroy confidence.
2. Archive identity was path/name-heavy. A track moved to another folder could
   be treated as new even if the audio content already existed.
3. Duplicate detection was mostly metadata/name based. It caught similar titles,
   but it was not enough for exact binary/audio duplicate protection.
4. Multiple legacy modules carried their own copy logic instead of using one
   archive authority.
5. Existing messy archives needed a cleanup plan, not automatic deletion.

## Fixes Already Added

1. `Organizer.safe_copy()` now checks:
   - source already inside archive
   - exact content fingerprint already in archive
   - same target filename with same content
2. `ArchiveAuditor` now reports renamed duplicate groups such as `_1`, `_2`,
   `(1)`, and copy/kopya patterns.
3. `ArchiveReconciler` now creates a safe cleanup plan for exact duplicates.
   It reports what to keep, what is duplicate, and reclaimable space.
4. Archive audit now writes both health report and cleanup plan.
5. Legacy `LibraryBrain.store()` now routes through `Organizer`.

## Archive Vision

The archive system should become the product's crown jewel:

1. Never copy the same audio twice.
2. Never delete automatically.
3. Always explain why a file is kept, linked, moved, or flagged.
4. Treat `DJ_LIBRARY_OUTPUT` as a curated export/archive, not a dumping ground.
5. Preserve original source folders unless the DJ explicitly asks for migration.
6. Build a stable identity for each track:
   - content fingerprint
   - acoustic fingerprint later
   - normalized artist/title
   - duration
   - BPM/key confidence
   - bitrate/file quality
7. Separate exact duplicates from version duplicates:
   - exact duplicate: same content, keep one
   - quality duplicate: same song, better bitrate/version exists
   - creative version: remix/edit/extended/acapella/instrumental, keep as version
8. Create DJ-safe crates:
   - Clean Main Archive
   - Needs Review
   - Better Version Exists
   - Event/Wedding
   - Rescue Crate
   - Rekordbox Ready

## Next Engineering Priorities

1. Add persistent `content_fingerprint` and `archive_status` to the database.
2. Add a UI screen for Archive Guardian:
   - exact duplicates
   - renamed duplicates
   - reclaimable space
   - keep/delete candidates
   - quarantine plan
3. Add a safe quarantine action that moves duplicates to `DJ_EXPORTS/QUARANTINE`
   only after explicit confirmation.
4. Add version intelligence:
   - Original Mix
   - Extended Mix
   - Radio Edit
   - Remix
   - Acapella
   - Instrumental
5. Add audio fingerprinting later for same song with different encodes.
6. Add a dry-run mode before every archive write.
7. Add a rollback manifest for every archive operation.

## Product Direction

The program should not feel like a file sorter. It should feel like a trusted
AI music archivist and performance co-pilot.

The killer workflow:

1. Scan without copying.
2. Diagnose archive health.
3. Show exact risks clearly.
4. Let the DJ approve cleanup.
5. Build Rekordbox-ready crates.
6. Build a gig pack.
7. Learn from DJ feedback.

Only then should remix generation, FL Studio mastering, and live control become
the visible magic on top of a trustworthy archive core.
