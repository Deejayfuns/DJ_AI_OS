"""
ORB Neon — Renderer
===================
Real-time visualizer for waveforms, spectrums, and particle effects.
"""
import math
import random
import time
from typing import Dict, List, Optional, Tuple

from .theme import Theme, Glow


class WaveformRenderer:
    """Real-time waveform renderer."""

    def __init__(self, theme: Theme = None, canvas=None):
        self.theme = theme or Theme()
        self.canvas = canvas
        self._samples = []

    def set_samples(self, samples: List[float]):
        """Set waveform samples."""
        self._samples = samples

    def draw(self, canvas=None, width: int = 400, height: int = 100,
             position: float = 0.0, playing: bool = False):
        """Draw waveform on canvas."""
        c = canvas or self.canvas
        if not c:
            return

        c.delete("waveform")
        color = self.theme.c("waveform_playing" if playing else "waveform")
        mid = height / 2

        if not self._samples:
            c.create_line(0, mid, width, mid, fill=self.theme.c("border"),
                         tags="waveform", width=1)
            return

        # Downsample to fit width
        step = max(1, len(self._samples) // max(1, width))
        points = []
        for i in range(0, len(self._samples), step):
            x = int(i / max(1, len(self._samples)) * width)
            y = mid - self._samples[i] * mid
            points.append((x, y))

        if len(points) > 1:
            c.create_line(*[coord for p in points for coord in p],
                         fill=color, tags="waveform", width=1.5)

        # Play position marker
        marker_x = int(position * width)
        c.create_line(marker_x, 0, marker_x, height,
                     fill=self.theme.c("accent2"), tags="waveform",
                     width=1, dash=(3, 2))

        # Glow effect (soft underlay)
        if len(points) > 1:
            c.create_line(*[coord for p in points for coord in p],
                         fill=Glow.pulse(color, 0.4),
                         tags="waveform_glow", width=4)


class SpectrumRenderer:
    """Real-time frequency spectrum bars."""

    def __init__(self, theme: Theme = None, canvas=None):
        self.theme = theme or Theme()
        self.canvas = canvas
        self._bands: List[float] = [0.0] * 32
        self._peak: List[float] = [0.0] * 32

    def update_fft(self, fft_magnitudes: List[float]):
        """Update from FFT magnitudes."""
        if not fft_magnitudes:
            return
        n_bands = len(self._bands)
        for i in range(n_bands):
            start = int(i * len(fft_magnitudes) / n_bands)
            end = int((i + 1) * len(fft_magnitudes) / n_bands)
            band = sum(fft_magnitudes[start:end]) / max(1, end - start)
            self._bands[i] = band
            self._peak[i] = max(self._peak[i] * 0.98, band)

    def draw(self, canvas=None, width: int = 400, height: int = 100):
        """Draw spectrum bars."""
        c = canvas or self.canvas
        if not c:
            return
        c.delete("spectrum")

        n = len(self._bands)
        bar_w = width / n
        color = self.theme.c("spectrum")

        for i, level in enumerate(self._bands):
            bar_h = int(level * height)
            x = i * bar_w
            col = Glow.lerp(self.theme.c("bg_dark"), color, level)
            c.create_rectangle(x, height - bar_h, x + bar_w - 2, height,
                             fill=col, outline="", tags="spectrum")
            peak_y = height - int(self._peak[i] * height)
            c.create_line(x, peak_y, x + bar_w - 2, peak_y,
                         fill=self.theme.c("fg_bright"), width=1, tags="spectrum")

    def idle_animation(self):
        """Generate idle animation data when no audio."""
        for i in range(len(self._bands)):
            self._bands[i] = max(0.0, self._bands[i] - 0.01)
            self._peak[i] = max(0.0, self._peak[i] - 0.005)


class ParticleEffect:
    """Simple particle system for effects."""

    def __init__(self, theme: Theme = None):
        self.theme = theme or Theme()
        self.particles: List[Dict] = []

    def spawn_burst(self, x: float, y: float, count: int = 20,
                    color: str = None, speed: float = 100.0):
        """Spawn particle burst."""
        color = color or self.theme.c("accent")
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            vx = math.cos(angle) * random.uniform(0.3, 1.0) * speed
            vy = math.sin(angle) * random.uniform(0.3, 1.0) * speed
            self.particles.append({
                "x": x, "y": y, "vx": vx, "vy": vy,
                "life": random.uniform(0.5, 1.5),
                "max_life": 1.5,
                "color": color,
                "size": random.uniform(1, 3),
            })

    def spawn_stream(self, x: float, y: float, dx: float, dy: float,
                     color: str = None, rate: int = 5):
        """Spawn continuous particle stream."""
        color = color or self.theme.c("accent2")
        for _ in range(rate):
            self.particles.append({
                "x": x, "y": y, "vx": dx + random.uniform(-20, 20),
                "vy": dy + random.uniform(-20, 20),
                "life": random.uniform(0.3, 1.0),
                "max_life": 1.0,
                "color": color,
                "size": random.uniform(1, 2.5),
            })

    def update(self, dt: float):
        """Update particles."""
        alive = []
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.98
            p["vy"] *= 0.98
            p["life"] -= dt
            if p["life"] > 0:
                alive.append(p)
        self.particles = alive

    def draw(self, canvas, width: int, height: int):
        """Draw particles."""
        if not canvas:
            return
        canvas.delete("particles")
        for p in self.particles:
            alpha = max(0.0, p["life"] / p["max_life"])
            color = Glow.pulse(p["color"], alpha)
            x, y = int(p["x"]), int(p["y"])
            if 0 <= x <= width and 0 <= y <= height:
                canvas.create_oval(x - p["size"], y - p["size"],
                                  x + p["size"], y + p["size"],
                                  fill=color, outline="", tags="particles")

    def clear(self):
        self.particles.clear()


class Renderer:
    """Unified renderer combining all visual elements."""

    def __init__(self, theme: Theme = None):
        self.theme = theme or Theme()
        self.waveform = WaveformRenderer(self.theme)
        self.spectrum = SpectrumRenderer(self.theme)
        self.particles = ParticleEffect(self.theme)

    def set_theme(self, theme: Theme):
        """Update theme for all renderers."""
        self.theme = theme
        self.waveform.theme = theme
        self.spectrum.theme = theme
        self.particles.theme = theme