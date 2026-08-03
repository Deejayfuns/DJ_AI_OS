"""
Convert a folder of MIDI files into a step-pattern dataset for training.

Usage:
  python scripts/midi_to_dataset.py /path/to/midi_folder --out patterns.npz
"""

import argparse
from app.ai.midi_to_steps import folder_to_dataset


def main():
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    p.add_argument('--out', default='midi_patterns.npz')
    p.add_argument('--resolution', type=int, default=16)
    args = p.parse_args()

    shape = folder_to_dataset(args.folder, args.out, resolution=args.resolution)
    print('Saved dataset:', args.out, 'shape=', shape)

if __name__ == '__main__':
    main()
