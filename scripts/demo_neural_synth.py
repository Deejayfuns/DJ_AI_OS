#!/usr/bin/env python3
"""
DJ AI OS — Neural Synth Demo
============================
Renders a set of WAVs showing what the neural instrument can do:
  1. Neural bassline  — a bassline played by a VAE-learned timbre
  2. Timbre morph     — kick morphing into a pluck (spectral, pure numpy)
  3. Neural morph     — two learned sound classes blended in LATENT space
  4. Neural variation — one kick re-imagined as 4 different kicks (latent)
  5. Neural stab      — a "new" sound sampled from the manifold

Output lands in DJ_EXPORTS/neural_demo/. Open the folder and listen —
the surprises are #3 (latent morph produces timbres that never existed)
and #4 (the same kick, four bodies).
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import soundfile as sf

from app.ai.instruments import get_instrument
from app.ai.instruments.neural_synth import NeuralTimbreVAE

OUT = os.path.join("DJ_EXPORTS", "neural_demo")


def _note_freq(n):
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


def render_bassline(inst, notes, note_len=0.42, sr=44100):
    """Sequence notes (MIDI) into one mono track with a tiny gap."""
    gap = 0.02
    tracks = []
    for n in notes:
        seg = inst.hit(note=n, velocity=1.0)
        n_samples = int(note_len * sr)
        if len(seg) < n_samples:
            seg = np.pad(seg, (0, n_samples - len(seg)))
        else:
            seg = seg[:n_samples]
        # fade the tail so the bassline breathes
        f = int(0.05 * sr)
        seg[-f:] *= np.linspace(1, 0, f)
        tracks.append(seg)
        tracks.append(np.zeros(int(gap * sr), dtype=np.float32))
    return np.concatenate(tracks)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("=" * 60)
    print("   NEURAL SYNTH — DEMO  (çıktılar: DJ_EXPORTS/neural_demo/)")
    print("=" * 60)

    # Ensure a model exists (cached on-the-fly if none trained yet)
    inst = get_instrument("neural_synth")
    t0 = time.time()
    print("\n[1/5] hazırlanıyor (VAE yükle/önbellek)...")
    inst.ensure_vae()
    print(f"      VAE hazır ({time.time()-t0:.1f}s)")

    sr = 44100

    # ---- 1. Neural bassline (A minor-ish, E1→A2 range) ----
    print("[2/5] neural bassline üretiliyor (VAE timbre) ...")
    inst.set_param("morph_amount", 0.0)
    inst.set_param("timbre_src", 1)     # bass class
    inst.set_param("z_noise", 0.25)     # slight neural drift per note
    bass_notes = [33, 40, 36, 43, 33, 40, 38, 45,
                  33, 40, 36, 43, 31, 38, 34, 41]
    bass = render_bassline(inst, bass_notes, sr=sr)
    sf.write(os.path.join(OUT, "1_neural_bassline.wav"), bass, sr)
    print(f"      -> 1_neural_bassline.wav ({len(bass)/sr:.1f}s)")

    # ---- 2. Spectral morph: kick -> pluck ----
    print("[3/5] spektral morph üretiliyor (kick -> pluck) ...")
    kick = inst._representative(0)
    pluck = inst._representative(2)
    morph_chain = []
    for amt in [0.0, 0.25, 0.5, 0.75, 1.0]:
        seg = inst.morph_between(kick, pluck, amount=amt)
        # repeat each morph step 3x so it's audible
        morph_chain.extend([seg, seg, seg])
    morph = np.concatenate(morph_chain)
    sf.write(os.path.join(OUT, "2_spectral_morph.wav"), morph, sr)
    print(f"      -> 2_spectral_morph.wav (kick→pluck 5 kademe)")

    # ---- 3. Neural (latent) morph: kick class -> arp class ----
    print("[4/5] neural latent morph üretiliyor (VAE z-uzayı) ...")
    z_kick = inst._z_for(0)
    z_arp = inst._z_for(3)
    vae = inst._vae
    latent_chain = []
    for t in np.linspace(0.0, 1.0, 8):
        seg = vae.morph(z_kick, z_arp, t)
        latent_chain.extend([seg, seg])
    lat = np.concatenate(latent_chain)
    sf.write(os.path.join(OUT, "3_latent_morph.wav"), lat, sr)
    print(f"      -> 3_latent_morph.wav (z-space: kick -> arp)")

    # ---- 4. Neural variation: one kick, four bodies ----
    print("[5/5] neural varyasyon üretiliyor (aynı kick, 4 bodies) ...")
    var_track = []
    for seed in [1, 2, 3, 4]:
        seg = inst.sample_latent(seed=seed, timbre_src=0)
        var_track.extend([seg, np.zeros(int(0.15 * sr), dtype=np.float32)])
    var = np.concatenate(var_track)
    sf.write(os.path.join(OUT, "4_neural_variations.wav"), var, sr)
    print(f"      -> 4_neural_variations.wav (4 varyasyon)")

    print("\n" + "=" * 60)
    print("   TAMAM. Şu klasörü aç ve dinle:")
    print(f"   {os.path.abspath(OUT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
