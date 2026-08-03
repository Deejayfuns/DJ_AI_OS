Neural Beat Generator

This folder contains a minimal PyTorch-based beat pattern generator prototype.

Quick start (after installing requirements including `torch` and `torchaudio`):

```bash
python scripts/train_beat_model.py --epochs 5 --out beat_model.pt
```

Generate from a saved model (example):

```python
from app.ai.neural_beat_generator import BeatTransformer, generate
import torch
model = BeatTransformer(n_instruments=3, steps=16)
model.load_state_dict(torch.load('beat_model.pt'))
pattern = generate(model)
print(pattern.astype(int))
```

Notes:
- This is a prototype. For production-quality generation, prepare proper MIDI/rhythm datasets, expand model capacity, and add conditional inputs (genre, tempo, swing).
- You can integrate generated patterns with `app.ai.synth_engine.SynthEngine` to render audio.
