"""
Convert MIDI drum tracks into 16-step binary patterns per bar.

Functions:
- `midi_to_patterns(midi_path, resolution=16, instruments=None)` -> list of numpy arrays (steps, n_instruments)
- `folder_to_dataset(folder, out_path)` -> scans MIDI files and saves a .npz dataset

Notes:
- Uses `mido` (already in requirements).
- Default instrument mapping: kick (36,35), snare (38,40), hat (42,44,46).
- Each bar is represented as a (resolution x n_instruments) array with 0/1 values.
"""

import os
import numpy as np

try:
    import mido
except Exception:
    mido = None


DEFAULT_INSTRUMENTS = {
    'kick': {36, 35},
    'snare': {38, 40},
    'hat': {42, 44, 46},
}


def note_to_instrument_idx(note, instruments_map=None):
    """Return instrument index or None if note not mapped."""
    instruments_map = instruments_map or DEFAULT_INSTRUMENTS
    for i, (name, notes) in enumerate(instruments_map.items()):
        if note in notes:
            return i
    return None


def midi_to_patterns(midi_path, resolution=16, instruments_map=None):
    """Convert a single MIDI file to a list of (steps x instruments) arrays.

    Each bar (4/4) becomes one array of `resolution` steps (commonly 16).
    """
    if mido is None:
        raise RuntimeError('mido is required to parse MIDI files')

    instruments_map = instruments_map or DEFAULT_INSTRUMENTS
    n_instruments = len(instruments_map)

    mid = mido.MidiFile(midi_path)
    ppq = mid.ticks_per_beat

    # Merge tracks to get a single event stream
    merged = mido.merge_tracks(mid.tracks)

    total_ticks = 0
    patterns = []

    tempo = 500000  # default microseconds per beat (120bpm)

    for msg in merged:
        total_ticks += msg.time
        if msg.type == 'set_tempo':
            tempo = msg.tempo

        if msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0:
            note = msg.note
            # compute beat position (quarter notes)
            beats = total_ticks / ppq
            # sixteenth index across the file
            sixteenth_index = int(beats * 4)
            bar_index = sixteenth_index // resolution
            step = sixteenth_index % resolution

            inst_idx = note_to_instrument_idx(note, instruments_map)
            if inst_idx is None:
                continue

            # ensure pattern for bar exists
            while len(patterns) <= bar_index:
                patterns.append(np.zeros((resolution, n_instruments), dtype=np.uint8))

            patterns[bar_index][step, inst_idx] = 1

    return patterns


def folder_to_dataset(folder, out_path, resolution=16, instruments_map=None, extensions=('.mid', '.midi')):
    """Scan a folder of MIDI files and save a numpy dataset (.npz) of patterns."""
    files = []
    for root, dirs, filenames in os.walk(folder):
        for f in filenames:
            if f.lower().endswith(extensions):
                files.append(os.path.join(root, f))

    all_patterns = []
    for path in files:
        try:
            pats = midi_to_patterns(path, resolution=resolution, instruments_map=instruments_map)
            all_patterns.extend(pats)
        except Exception:
            continue

    if not all_patterns:
        raise RuntimeError('No patterns extracted from folder')

    arr = np.stack(all_patterns)
    np.savez_compressed(out_path, patterns=arr)
    return arr.shape


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    p.add_argument('--out', default='midi_patterns.npz')
    p.add_argument('--resolution', type=int, default=16)
    args = p.parse_args()

    shape = folder_to_dataset(args.folder, args.out, resolution=args.resolution)
    print('Saved dataset:', args.out, 'shape=', shape)
