"""
Neural beat generator prototype using PyTorch.
- Provides a SequenceDataset for symbolic beat sequences (16-step patterns)
- Simple Transformer model to predict next-step probabilities per instrument
- Training loop sketch and a generate() helper

This is a minimal scaffold — training requires rhythm dataset (MIDI-to-step or collected patterns).
"""

import math
import random
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np


class SequenceDataset(Dataset):
    """Dataset of beat step sequences.

    Each sample is a tensor of shape (steps, instruments), values 0/1.
    For prototyping, you can synthesize random patterns or convert MIDI.
    """

    def __init__(self, patterns):
        # patterns: list of numpy arrays (steps, instruments)
        self.patterns = [torch.tensor(p, dtype=torch.float32) for p in patterns]

    def __len__(self):
        return len(self.patterns)

    def __getitem__(self, idx):
        seq = self.patterns[idx]
        return seq


class BeatTransformer(nn.Module):
    def __init__(self, n_instruments=3, steps=16, d_model=128, nhead=4, num_layers=3):
        super().__init__()
        self.n_instruments = n_instruments
        self.steps = steps
        self.d_model = d_model

        self.input_proj = nn.Linear(n_instruments, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.out = nn.Linear(d_model, n_instruments)

    def forward(self, x):
        # x: batch, steps, instruments
        b, s, i = x.shape
        h = self.input_proj(x)  # b,s,d
        h = h.permute(1, 0, 2)  # s,b,d for transformer
        h = self.transformer(h)
        h = h.permute(1, 0, 2)
        out = self.out(h)
        return out  # logits per step per instrument


def train(model, dataset, epochs=10, batch_size=32, lr=1e-3, device=None):
    device = device or (torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    for epoch in range(epochs):
        total_loss = 0.0
        model.train()
        for batch in loader:
            batch = batch.to(device)
            logits = model(batch)
            loss = loss_fn(logits, batch)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item() * batch.size(0)

        avg = total_loss / len(dataset)
        print(f"Epoch {epoch+1}/{epochs} avg_loss={avg:.6f}")

    return model


def generate(model, primer=None, steps=16, temperature=1.0, device=None):
    device = device or (torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))
    model = model.to(device)
    model.eval()

    n_instr = model.n_instruments
    seq = torch.zeros((1, steps, n_instr), device=device)

    if primer is not None:
        p = torch.tensor(primer, dtype=torch.float32).unsqueeze(0).to(device)
        seq[:, :p.shape[1], :] = p

    with torch.no_grad():
        logits = model(seq)
        probs = torch.sigmoid(logits / max(1e-6, temperature))
        sampled = (probs > 0.5).float()

    return sampled.squeeze(0).cpu().numpy()


# -- Utilities for quick synthetic data and demo

def synth_random_patterns(n=512, steps=16, instruments=3):
    patterns = []
    for _ in range(n):
        pat = np.zeros((steps, instruments), dtype=np.float32)
        # Kick on 1 + some variation
        for s in range(steps):
            if s % 4 == 0 and random.random() > 0.1:
                pat[s, 0] = 1.0
            if random.random() < 0.2:
                pat[s, 1] = 1.0
            if random.random() < 0.15:
                pat[s, 2] = 1.0
        patterns.append(pat)
    return patterns


if __name__ == "__main__":
    # quick smoke test: synth data, train few epochs, generate
    patterns = synth_random_patterns(256)
    ds = SequenceDataset(patterns)
    model = BeatTransformer(n_instruments=3, steps=16)
    model = train(model, ds, epochs=3, batch_size=32)
    out = generate(model)
    print(out.astype(int))
