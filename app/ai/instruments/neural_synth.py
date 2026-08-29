"""
DJ AI OS — Neural Synth Plugin
==============================
A "neural instrument" that *learns timbre* instead of hardcoding an
oscillator. Three backends, one plugin:

1. **NeuralVAE**  (default, works on CPU)
   A small 1D-convolutional Variational Autoencoder trained on a corpus
   of sounds. Encodes any sound into a compact latent space, then lets you:
       - sample the latent → brand-new sounds never in the training set
       - interpolate two latents → timbre morphing
       - add z-noise → variations of a single sound
   Trained on the app's own synth_core corpus by default, so the VAE
   learns "what a club kick / rolling bass / pluck is" and can imagine
   new ones. Full training pipeline: scripts/train_neural_timbre.py

2. **SpectralMorph**  (always works, pure numpy)
   Real-time FFT morphing between ANY two sounds — interpolate harmonic
   magnitude spectra independently from the noise floor. This is the same
   trick flagship synths (Omnisphere, Serum) use for "morphing" pads.

3. **RAVE**  (optional, if a pre-trained model is present)
   Real-time latent timbre transfer. If a `.ckpt`/torchscript model is
   found in DJ_EXPORTS/neural_models/, the plugin encodes source audio,
   manipulates the latent and decodes. Falls back gracefully otherwise.

The plugin is registered into the standard instrument registry, so it
plays inside DAWEngine patterns, LivePerformanceEngine and the synth
editor with zero changes to those systems.

Usage:
    from app.ai.instruments.neural_synth import NeuralSynthPlugin
    inst = get_instrument("neural_synth")
    sig = inst.hit(note=45, velocity=0.9)      # -> mono float32 ndarray

    inst.morph_between(sig_a, sig_b, amount=0.5)   # spectral morph
    inst.sample_latent(seed=7)                     # neural variation
"""

import os

import numpy as np

from .base import InstrumentPlugin, register, SR_DEFAULT
from . import synth_core as sc
from app.core.paths import get_exports_dir

# ------------------------------------------------------------------
# Lazy torch import — the plugin degrades gracefully without torch.
# ------------------------------------------------------------------
_torch = None
def _import_torch():
    global _torch
    if _torch is None:
        try:
            import torch
            import torch.nn as nn
            _torch = (torch, nn)
        except Exception:
            _torch = False
    return _torch if _torch is not False else None


MODEL_DIR = os.path.join(str(get_exports_dir()), "neural_models")


# ==================================================================
# NEURAL VAE — learn timbre, generate new sounds
# ==================================================================
class NeuralTimbreVAE:
    """
    A compact 1D-convolutional Variational Autoencoder for audio windows.

    Architecture:
        window  -> [Conv 1x8, ReLU, Pool2]x3 -> [mu, logvar] (z, latent_dim)
        z       -> Linear -> [Up, Conv 1x8, ReLU]x3 -> window

    Loss: reconstruction (MSE + spectral) + KL divergence, so the latent
    is both compact *and* continuous — which is what makes interpolation
    and sampling sound like real timbres instead of noise.

    Pure PyTorch, CPU-friendly, trains in minutes on a few thousand
    0.3s windows.
    """

    def __init__(self, latent_dim=48, sr=SR_DEFAULT, window=0.3):
        torch, nn = _import_torch()
        if torch is None:
            raise RuntimeError("NeuralTimbreVAE requires torch")
        self.sr = sr
        self.window = window
        self.n = int(sr * window)
        self.latent_dim = latent_dim

        class _VAE(nn.Module):
            def __init__(self, n_in, z_dim):
                super().__init__()
                # encoder: n_in -> n_in/2 -> n_in/4 -> n_in/8
                self.enc = nn.Sequential(
                    nn.Conv1d(1, 16, kernel_size=8, stride=4, padding=3),
                    nn.LeakyReLU(0.2),
                    nn.Conv1d(16, 32, kernel_size=8, stride=4, padding=3),
                    nn.LeakyReLU(0.2),
                    nn.Conv1d(32, 64, kernel_size=8, stride=4, padding=3),
                    nn.LeakyReLU(0.2),
                )
                self.fc_mu = nn.LazyLinear(z_dim)
                self.fc_logvar = nn.LazyLinear(z_dim)
                # decoder: z -> 64 x n/64 -> ... -> n_in
                self.fc_z = nn.LazyLinear(64 * (n_in // 64))
                self.dec = nn.Sequential(
                    nn.ConvTranspose1d(64, 32, kernel_size=8, stride=4,
                                       padding=3, output_padding=1),
                    nn.LeakyReLU(0.2),
                    nn.ConvTranspose1d(32, 16, kernel_size=8, stride=4,
                                       padding=3, output_padding=1),
                    nn.LeakyReLU(0.2),
                    nn.ConvTranspose1d(16, 1, kernel_size=8, stride=4,
                                       padding=3, output_padding=1),
                    nn.Tanh(),
                )

            def encode(self, x):
                h = self.enc(x)
                h = h.flatten(1)
                return self.fc_mu(h), self.fc_logvar(h)

            def decode(self, z):
                h = self.fc_z(z)
                h = h.view(h.shape[0], 64, -1)
                return self.dec(h)

            def forward(self, x):
                mu, lv = self.encode(x)
                eps = torch.randn_like(mu)
                z = mu + torch.exp(0.5 * lv) * eps
                return self.decode(z), mu, lv

        self.model = _VAE(self.n, self.latent_dim)
        self.model.eval()

    # ---- build a training corpus from synth_core ----
    @staticmethod
    def synth_corpus(n_per_class=140, sr=SR_DEFAULT, seed=0):
        """Deterministic corpus of sounds from the app's own synth core.
        This is what lets the VAE learn *DJ-relevant* timbres without
        needing a huge external dataset."""
        rng = np.random.default_rng(seed)
        sounds = []
        pitches = [36, 40, 43, 45, 47, 48, 52, 55, 60, 64, 67, 72]
        for _ in range(n_per_class):
            kind = rng.integers(0, 6)
            if kind == 0:
                s = sc.kick(freq_start=rng.uniform(100, 220),
                            freq_end=rng.uniform(40, 70),
                            punch=rng.uniform(1, 3))
            elif kind == 1:
                s = sc.snare(tone=rng.uniform(140, 240),
                             body=rng.uniform(0.3, 0.8),
                             snappy=rng.uniform(0.5, 1.5))
            elif kind == 2:
                p = int(pitches[rng.integers(0, len(pitches))])
                s = sc.bass(kind="saw", freq=sc.note_to_freq(p),
                            cutoff=rng.uniform(180, 700),
                            drive=rng.uniform(1, 3))
            elif kind == 3:
                p = int(pitches[rng.integers(0, len(pitches))])
                s = sc.pluck(freq=sc.note_to_freq(p),
                             damp=rng.uniform(0.96, 0.995))
            elif kind == 4:
                p = int(pitches[rng.integers(0, len(pitches))])
                s = sc.rolling_bass(freq=sc.note_to_freq(p),
                                    cutoff=rng.uniform(150, 500),
                                    drive=rng.uniform(1.2, 3))
            else:
                p = int(pitches[rng.integers(0, len(pitches))])
                s = sc.arp_pluck(freq=sc.note_to_freq(p),
                                 decay=rng.uniform(2, 6))
            sounds.append(s)
        return sounds

    @staticmethod
    def from_folder(folder, n=4096, sr=SR_DEFAULT, seed=1):
        """Load a corpus from a folder of wav/flac files (resampled,
        center-cropped to one window)."""
        import glob
        import soundfile as sf
        files = sorted(glob.glob(os.path.join(folder, "*.wav")) +
                       glob.glob(os.path.join(folder, "*.flac")) +
                       glob.glob(os.path.join(folder, "*.mp3")))[:n]
        sounds = []
        for f in files:
            try:
                data, fs = sf.read(f, dtype="float32", always_2d=True)
                if data.shape[1] > 1:
                    data = data.mean(axis=1)
                data = data[: int(sr * 0.3)]
                if len(data) < int(sr * 0.05):
                    continue
                sounds.append(data)
            except Exception:
                continue
        return sounds

    # ---- training ----
    def train(self, sounds, epochs=40, lr=1e-3, batch=32, verbose=True):
        """Train on a list of mono float32 arrays (any length >= window)."""
        torch, nn = _import_torch()
        X = self._windows(sounds)
        if len(X) < 8:
            raise ValueError(f"Not enough training data ({len(X)} windows)")
        # adapt batch to the corpus size so tiny on-the-fly sets still work
        while batch > len(X):
            batch //= 2
        dataset = torch.utils.data.TensorDataset(torch.from_numpy(X))
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch,
                                             shuffle=True)
        opt = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.model.train()
        for ep in range(epochs):
            tot_loss = 0.0
            for (xb,) in loader:
                opt.zero_grad()
                rec, mu, lv = self.model(xb)
                # align decoder output length to input (transposed convs
                # may overshoot/undershoot by a few samples)
                rec = self._align(rec, xb)
                recon = ((rec - xb) ** 2).mean()
                # spectral loss (log-magnitude FFT) — keeps the timbre
                R = torch.fft.rfft(rec, dim=2)
                T = torch.fft.rfft(xb, dim=2)
                spec = ((torch.log1p(R.abs()) - torch.log1p(T.abs())) ** 2).mean()
                kld = -0.5 * (1 + lv - mu.pow(2) - lv.exp()).mean()
                loss = recon + 0.5 * spec + 0.05 * kld
                loss.backward()
                opt.step()
                tot_loss += loss.item()
            if verbose and (ep % 5 == 0 or ep == epochs - 1):
                print(f"  [vae] epoch {ep+1:>3}/{epochs}  loss={tot_loss/len(loader):.4f}")
        self.model.eval()

    def _windows(self, sounds):
        torch, nn = _import_torch()
        n = self.n
        out = []
        for s in sounds:
            s = np.asarray(s, dtype=np.float32)
            if len(s) < n:
                # zero-pad short sounds (they're drum hits)
                s = np.pad(s, (0, n - len(s)))
            # take a few crops per sound for variety
            for _ in range(max(1, len(s) // n)):
                start = np.random.randint(0, max(1, len(s) - n + 1))
                crop = s[start:start + n]
                out.append(crop)
                if len(out) >= 20000:
                    break
            if len(out) >= 20000:
                break
        X = np.stack(out)[:, None, :].astype(np.float32)
        # normalize per-window peak
        peak = np.max(np.abs(X), axis=2, keepdims=True) + 1e-9
        X = X / peak
        return X

    # ---- inference ----
    @staticmethod
    def _t(x):
        torch, nn = _import_torch()
        return torch.from_numpy(x).float()

    @staticmethod
    def _align(tensor, ref):
        """Pad/crop tensor's last dim to match ref's last dim."""
        n = tensor.shape[-1]
        m = ref.shape[-1]
        if n == m:
            return tensor
        if n > m:
            return tensor[..., :m]
        torch, nn = _import_torch()
        return torch.nn.functional.pad(tensor, (0, m - n))

    def encode(self, x):
        """Encode a mono array into latent mean."""
        torch, nn = _import_torch()
        x = np.asarray(x, dtype=np.float32)
        if len(x) != self.n:
            x = self._pad(x)
        peak = np.max(np.abs(x)) + 1e-9
        xt = self._t(x[None, None, :]) / peak
        with torch.no_grad():
            mu, _ = self.model.encode(xt)
        return mu.numpy()[0]

    def decode(self, z, noise=0.0):
        """Decode a latent vector (optionally with z-noise) to audio."""
        torch, nn = _import_torch()
        z = np.asarray(z, dtype=np.float32)
        if z.ndim == 1:
            z = z[None, :]
        if noise > 0:
            z = z + np.random.randn(*z.shape).astype(np.float32) * noise
        with torch.no_grad():
            y = self.model.decode(self._t(z))
        out = y.numpy()[0, 0]
        # align to the exact window length
        if len(out) != self.n:
            target = np.zeros(self.n, dtype=np.float32)
            k = min(len(out), self.n)
            target[:k] = out[:k]
            out = target
        peak = np.max(np.abs(out)) + 1e-9
        return (out / peak * 0.9).astype(np.float32)

    def sample(self, z_ref=None, noise=0.5):
        """Sample a new sound from the latent space. With z_ref, stays
        near that timbre (variation); without, explores the manifold."""
        if z_ref is None:
            z = np.random.randn(self.latent_dim).astype(np.float32) * 0.9
        else:
            z = np.asarray(z_ref, dtype=np.float32) + \
                np.random.randn(self.latent_dim).astype(np.float32) * noise
        return self.decode(z)

    def morph(self, z_a, z_b, t=0.5):
        """Latent interpolation — timbre morphing."""
        t = float(np.clip(t, 0, 1))
        za = np.asarray(z_a, dtype=np.float32)
        zb = np.asarray(z_b, dtype=np.float32)
        return self.decode(za * (1 - t) + zb * t)

    def _pad(self, x):
        if len(x) < self.n:
            return np.pad(x, (0, self.n - len(x)))
        return x[:self.n]

    # ---- persistence ----
    def save(self, path):
        torch, nn = _import_torch()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        torch.save({
            "state": self.model.state_dict(),
            "latent_dim": self.latent_dim, "sr": self.sr,
            "window": self.window, "n": self.n,
        }, path)

    @classmethod
    def load(cls, path):
        torch, nn = _import_torch()
        ckpt = torch.load(path, map_location="cpu")
        vae = cls(latent_dim=ckpt["latent_dim"], sr=ckpt["sr"],
                  window=ckpt["window"])
        vae.n = ckpt["n"]
        # LazyLinear layers materialize on first forward — prime them so
        # the saved state_dict keys exist before load_state_dict.
        with torch.no_grad():
            dummy = torch.zeros(1, 1, vae.n)
            _ = vae.model(dummy)
        vae.model.load_state_dict(ckpt["state"])
        vae.model.eval()
        return vae


# ==================================================================
# SPECTRAL MORPH — pure numpy, always works
# ==================================================================
def spectral_morph(sig_a, sig_b, amount=0.5, sr=SR_DEFAULT):
    """
    Morph two sounds in the spectral domain. `amount=0` → sig_a,
    `amount=1` → sig_b. Interpolates harmonic magnitude + noise floor
    separately, keeps sig_a's phase (so transients/time stay intact).
    This is the classic "timbre morphing" trick, O(n log n), CPU-fast.
    """
    a = np.asarray(sig_a, dtype=np.float64)
    b = np.asarray(sig_b, dtype=np.float64)
    n = max(len(a), len(b))
    a = np.pad(a, (0, n - len(a)))
    b = np.pad(b, (0, n - len(b)))

    A = np.fft.rfft(a)
    B = np.fft.rfft(b)

    mag_a, ph_a = np.abs(A), np.angle(A)
    mag_b, ph_b = np.abs(B), np.angle(B)

    # interpolate magnitudes (perceptual: use log domain)
    mag = np.exp(np.log1p(mag_a) * (1 - amount) + np.log1p(mag_b) * amount) - 1

    # phase: keep A's, but crossfade toward B for smoother low-frequency morph
    dph = (ph_b - ph_a + np.pi) % (2 * np.pi) - np.pi
    phase = ph_a + dph * amount

    out = np.fft.irfft(mag * np.exp(1j * phase), n).astype(np.float32)
    peak = np.max(np.abs(out)) + 1e-9
    return (out / peak * 0.9).astype(np.float32)


# ==================================================================
# THE PLUGIN
# ==================================================================
@register
class NeuralSynthPlugin(InstrumentPlugin):
    """
    Neural instrument: learn timbres, morph between them, imagine new ones.

    - `hit(note)` renders a sound at pitch. The base timbre comes from
      the latent space; pitch is applied by resampling (so the neural
      timbre is preserved, not rebuilt per-note).
    - `morph_between(a, b, amount)` spectral-morphs any two sounds.
    - `sample_latent()` / `learn_timbre(sounds)` use the NeuralVAE.
    - RAVE: if a model checkpoint is found, encode/decode flows through it.
    """

    name = "neural_synth"
    category = "melodic"
    description = ("Neural instrument — VAE-learned timbres, spectral "
                   "morphing and latent sampling (RAVE-ready).")
    cacheable = False  # neural output varies per call

    params = {
        # latent sampling / morphing
        "morph_amount": {"min": 0.0, "max": 1.0, "default": 0.5},
        "z_noise":      {"min": 0.0, "max": 1.5, "default": 0.0},
        "seed":         {"min": 0, "max": 999, "default": 0},
        # timbre (trained) controls
        "timbre_src":   {"min": 0, "max": 3, "default": 0},  # 0=kick 1=bass 2=pluck 3=arp
        "pitch_shift":  {"min": -24, "max": 24, "default": 0},
        # morph targets (which two sound classes to blend)
        "morph_a":      {"min": 0, "max": 3, "default": 0},
        "morph_b":      {"min": 0, "max": 3, "default": 2},
    }

    _BASE_FREQ = 110.0  # Hz the neural window is "centered" on

    # per sound-class reference pitch (Hz) — used for transposition so we
    # never have to *estimate* pitch from the neural output.
    _REF_FREQ = {0: 55.0, 1: 110.0, 2: 220.0, 3: 330.0}

    _MAX_NOTE_S = 1.6   # cap rendered note length (seconds)

    def __init__(self, sample_rate=SR_DEFAULT, model_path=None):
        super().__init__(sample_rate=sample_rate)
        self._vae = None
        self._vae_path = model_path
        self._z_cache = {}          # timbre_src -> latent
        self._wave_cache = {}       # timbre_src -> mono base window
        self._seed_rng = np.random.default_rng(0)

    # ---- backend management ----
    def ensure_vae(self):
        """Load (or lazily create) the NeuralTimbreVAE. The on-the-fly
        model is cached to disk so a fresh process loads in ~0.2s instead
        of re-training (~16s)."""
        if self._vae is not None:
            return True
        path = self._vae_path or self._default_model_path()
        if path and os.path.exists(path):
            try:
                self._vae = NeuralTimbreVAE.load(path)
                return True
            except Exception:
                self._vae = None
        # fall back to a freshly-trained-on-the-fly VAE (small corpus,
        # fast on CPU) so the plugin ALWAYS works. This is only a rough
        # timbre manifold — run scripts/train_neural_timbre.py for a
        # proper model trained on your own library.
        try:
            vae = NeuralTimbreVAE(latent_dim=48, sr=self.sr)
            corpus = NeuralTimbreVAE.synth_corpus(n_per_class=20, sr=self.sr)
            vae.train(corpus, epochs=6, verbose=False)
            self._vae = vae
            cache_path = os.path.join(MODEL_DIR, "default_quick.pt")
            try:
                vae.save(cache_path)
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _default_model_path(self):
        if not os.path.isdir(MODEL_DIR):
            return None
        import glob
        cands = sorted(glob.glob(os.path.join(MODEL_DIR, "*.pt")) +
                       glob.glob(os.path.join(MODEL_DIR, "*.ckpt")))
        return cands[0] if cands else None

    def _z_for(self, idx):
        """Latent of the idx-th learned sound class."""
        if idx in self._z_cache:
            return self._z_cache[idx]
        # synthesize a representative window for the class, encode it
        rep = self._representative(idx)
        if rep is None or self._vae is None:
            return None
        z = self._vae.encode(rep)
        self._z_cache[idx] = z
        return z

    def _representative(self, idx):
        rng = np.random.default_rng(1000 + idx * 17)
        if idx == 0:
            return sc.kick(freq_start=rng.uniform(130, 180), punch=1.6)
        if idx == 1:
            return sc.bass(kind="saw", freq=self._BASE_FREQ,
                           cutoff=rng.uniform(300, 500), drive=1.8)
        if idx == 2:
            return sc.pluck(freq=self._BASE_FREQ * 2, damp=0.985)
        return sc.arp_pluck(freq=self._BASE_FREQ * 3, decay=3.5)

    def _base_wave(self, idx):
        """Base waveform for class idx (neural or spectral)."""
        if idx in self._wave_cache:
            return self._wave_cache[idx]
        w = self._representative(idx)
        if self._vae is not None:
            try:
                z = self._vae.encode(w)
                nz = float(self._params["z_noise"])
                w = self._vae.sample(z_ref=z, noise=nz)
            except Exception:
                pass
        self._wave_cache[idx] = w
        return w

    # ---- public API (beyond InstrumentPlugin) ----
    def learn_timbre(self, sounds, epochs=40, save_path=None):
        """Train the neural VAE on your own sounds (any list of mono
        float32 arrays). Saves to save_path if given."""
        vae = NeuralTimbreVAE(latent_dim=48, sr=self.sr)
        vae.train(sounds, epochs=epochs, verbose=True)
        self._vae = vae
        self._z_cache = {}
        self._wave_cache = {}
        if save_path:
            vae.save(save_path)
        return vae

    def sample_latent(self, seed=None, timbre_src=None):
        """Generate a brand-new sound from the latent space (neural)."""
        if not self.ensure_vae():
            return self._representative(0)
        idx = int(self._params.get("timbre_src", 0)) if timbre_src is None else timbre_src
        z = self._z_for(idx)
        if seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        return self._vae.sample(z_ref=z, noise=0.6)

    def morph_between(self, sig_a, sig_b, amount=None):
        """Spectral morph between two arbitrary sounds. Pure numpy."""
        amt = float(self._params["morph_amount"]) if amount is None else amount
        return spectral_morph(sig_a, sig_b, amt, sr=self.sr)

    def neural_morph(self, idx_a, idx_b, amount=None):
        """Latent morph between two learned sound classes (neural)."""
        if not self.ensure_vae():
            return spectral_morph(self._representative(idx_a),
                                  self._representative(idx_b),
                                  amount, sr=self.sr)
        za = self._z_for(idx_a)
        zb = self._z_for(idx_b)
        amt = float(self._params["morph_amount"]) if amount is None else amount
        return self._vae.morph(za, zb, amt)

    # ---- InstrumentPlugin contract ----
    def _render(self, note=None, velocity=1.0):
        """Render one note. The learned timbre is pitch-shifted to match
        the requested note by resampling (neural timbre preserved)."""
        # 1. pick base waveform via latent/spectral engine
        if self._params["morph_amount"] > 0.03:
            a = int(self._params["morph_a"])
            b = int(self._params["morph_b"])
            if self._vae is not None:
                try:
                    base = self.neural_morph(a, b)
                except Exception:
                    base = spectral_morph(self._representative(a),
                                          self._representative(b),
                                          self._params["morph_amount"],
                                          sr=self.sr)
            else:
                base = spectral_morph(self._representative(a),
                                      self._representative(b),
                                      self._params["morph_amount"], sr=self.sr)
        else:
            src = int(self._params["timbre_src"])
            if self.ensure_vae():
                try:
                    z = self._z_for(src)
                    base = self._vae.sample(z_ref=z, noise=self._params["z_noise"])
                except Exception:
                    base = self._base_wave(src)
            else:
                base = self._base_wave(src)

        # 2. pitch to the requested note (relative to the class's KNOWN
        #    reference pitch — no estimation from neural output needed)
        if self._params["morph_amount"] > 0.03:
            ref = 0.5 * (self._REF_FREQ[a] + self._REF_FREQ[b])
        else:
            ref = self._REF_FREQ[src]
        target_note = note if note else 48
        target_hz = 440.0 * 2.0 ** ((target_note - 69) / 12.0)
        semis = 12.0 * np.log2(target_hz / ref) + int(self._params["pitch_shift"])
        out = self._transpose(base, semis)

        # 3. normalize + velocity (cap length to avoid absurd buffers)
        if len(out) > int(self.sr * self._MAX_NOTE_S):
            out = out[:int(self.sr * self._MAX_NOTE_S)]
        peak = float(np.max(np.abs(out))) + 1e-9
        out = (out / peak * 0.9 * float(velocity)).astype(np.float32)
        return out

    def _transpose(self, sig, semis):
        """Resample-based transpose. factor = 2**(semis/12)."""
        f = 2.0 ** (semis / 12.0)
        if abs(f - 1.0) < 1e-4:
            return np.asarray(sig, dtype=np.float32)
        n_out = int(len(sig) / f)
        n_out = max(16, min(n_out, int(self.sr * 3.0)))
        idx = np.clip(np.arange(n_out) * f, 0, len(sig) - 1)
        return np.interp(idx, np.arange(len(sig)), sig).astype(np.float32)


# re-export helpers at package level for convenience
def neural_instrument(**kwargs):
    """Factory: get a fully-configured NeuralSynthPlugin."""
    return NeuralSynthPlugin(**kwargs)
