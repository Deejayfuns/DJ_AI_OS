"""
Glue code: generate beat patterns from the neural model and render with SynthEngine.
Provides `play_generated_beat()` for CLI or UI integration.
"""
import os
import torch
import numpy as np

from app.ai.synth_engine import SynthEngine
from app.ai.neural_beat_generator import BeatTransformer, generate


def load_model(path, device=None):
    device = device or (torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))
    model = BeatTransformer(n_instruments=3, steps=16)
    if path and os.path.exists(path):
        state = torch.load(path, map_location=device)
        model.load_state_dict(state)
    return model


def pattern_tensor_to_sequence(arr):
    # arr: steps x instruments (0/1)
    # synth engine expects sequences per instrument as lists
    steps, instr = arr.shape
    return {
        'kick': [int(x) for x in arr[:, 0]],
        'hat': [int(x) for x in arr[:, 1]],
        'snare': [int(x) for x in arr[:, 2]],
    }


def play_generated_beat(model_path=None, bpm=120, bars=4, temperature=1.0, play=True, export_path=None):
    model = load_model(model_path)
    pattern = generate(model, temperature=temperature)

    seq = np.array(pattern)
    pattern_dict = pattern_tensor_to_sequence(seq)

    synth = SynthEngine()
    audio = synth.generate_beat(pattern_dict, bpm=bpm, bars=bars)

    if export_path:
        synth.export_wav(audio, export_path)

    if play:
        try:
            synth.play(audio)
        except Exception as exc:
            print("Playback failed:", exc)

    return {
        'pattern': pattern_dict,
        'audio_length_seconds': len(audio) / synth.sample_rate,
        'exported': bool(export_path),
    }


if __name__ == '__main__':
    # quick demo
    res = play_generated_beat(model_path=None, bpm=120, bars=2, temperature=1.0, play=False)
    print('Generated pattern:', res['pattern'])
