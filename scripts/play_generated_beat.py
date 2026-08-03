"""
CLI: play a generated beat using the neural model and SynthEngine.

Usage:
    python scripts/play_generated_beat.py --model beat_model.pt --bpm 120 --bars 4 --play
"""

import argparse
from app.ai.beat_playback import play_generated_beat


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=str, default=None)
    p.add_argument('--bpm', type=int, default=120)
    p.add_argument('--bars', type=int, default=4)
    p.add_argument('--temperature', type=float, default=1.0)
    p.add_argument('--no-play', dest='play', action='store_false')
    p.add_argument('--export', type=str, default=None)
    args = p.parse_args()

    res = play_generated_beat(
        model_path=args.model,
        bpm=args.bpm,
        bars=args.bars,
        temperature=args.temperature,
        play=args.play,
        export_path=args.export,
    )

    print('Result:', res)

if __name__ == '__main__':
    main()
