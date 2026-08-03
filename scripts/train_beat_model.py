"""
Simple CLI to train the neural beat generator on synthetic patterns.
Usage: python scripts/train_beat_model.py --epochs 10 --out model.pt
"""

import argparse
from app.ai.neural_beat_generator import synth_random_patterns, SequenceDataset, BeatTransformer, train
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--out", type=str, default="beat_model.pt")
    args = p.parse_args()

    patterns = synth_random_patterns(512)
    ds = SequenceDataset(patterns)
    model = BeatTransformer(n_instruments=3, steps=16)
    model = train(model, ds, epochs=args.epochs, batch_size=64)
    torch.save(model.state_dict(), args.out)
    print("Saved:", args.out)


if __name__ == "__main__":
    main()
