#!/usr/bin/env python3
"""
DJ AI OS — Train the Neural Timbre VAE on YOUR library
======================================================
Trains the NeuralSynthPlugin's latent model on your own tracks/sounds.
The model learns "what your DJ library sounds like" and the plugin can
then imagine new timbres inside that manifold, morph between them, and
play them at any pitch.

Usage:
    python scripts/train_neural_timbre.py                      # app's synth corpus
    python scripts/train_neural_timbre.py --folder DJ_MUSIC    # your tracks
    python scripts/train_neural_timbre.py --folder DJ_MUSIC --epochs 60 --out DJ_EXPORTS/neural_models/my_style.pt

Tip: point --folder at a folder of WAV/FLAC/MP3 (stems work great — a
vocals-only folder learns a vocal timbre manifold; a drums folder learns
a drum manifold). Center 0.3s crops are used as training windows.
"""
import argparse
import os
import time

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai.instruments.neural_synth import NeuralTimbreVAE, MODEL_DIR


def main():
    ap = argparse.ArgumentParser(description="Train Neural Timbre VAE")
    ap.add_argument("--folder", default=None,
                    help="folder of wav/flac/mp3 to learn from "
                         "(default: app's own synth_core corpus)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--latent", type=int, default=48)
    ap.add_argument("--out", default=None,
                    help=f"model output path (default {MODEL_DIR}/custom_timbre.pt)")
    args = ap.parse_args()

    os.makedirs(MODEL_DIR, exist_ok=True)
    out = args.out or os.path.join(MODEL_DIR, "custom_timbre.pt")

    print("=" * 60)
    print("   NEURAL TIMBRE VAE — TRAINING")
    print("=" * 60)

    vae = NeuralTimbreVAE(latent_dim=args.latent, sr=44100)

    if args.folder:
        print(f"  loading corpus from: {args.folder}")
        sounds = NeuralTimbreVAE.from_folder(args.folder)
        if len(sounds) < 8:
            print(f"  only {len(sounds)} usable sounds found — check folder.")
            sys.exit(1)
        print(f"  corpus: {len(sounds)} sounds")
    else:
        print("  corpus: DJ AI OS synth_core (kick/snare/bass/pluck/roll/arp)")
        sounds = NeuralTimbreVAE.synth_corpus(n_per_class=140, sr=44100)
        print(f"  corpus: {len(sounds)} generated sounds")

    t0 = time.time()
    vae.train(sounds, epochs=args.epochs, verbose=True)
    print(f"\n  trained in {time.time()-t0:.1f}s")

    vae.save(out)
    print(f"  model saved: {out}")
    print("  -> plugin auto-loads this on next use (it picks the first")
    print("     model in DJ_EXPORTS/neural_models/).")


if __name__ == "__main__":
    main()
