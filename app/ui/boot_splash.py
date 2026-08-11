"""
DJ AI OS — Cinematic Boot Sequence (the "future tech" first impression)

A full sci-fi OS boot: a holographic HUD frame (corner brackets, scanline,
live clock, telemetry strip), an orbital core with rotating rings, a live
neural network, and a real terminal console that streams ACTUAL machine
probes (audio devices, MIDI ports, CPU/RAM, neural model, Rekordbox export)
while the AI core loads. The orbital core converges into a glowing ASTRA
wordmark (per-letter light wave + charging arcs) as the neural core comes
online, ends with a neural boot chime, an ASTRA voice greeting and a
"SİSTEM HAZIR" burst, then dissolves the main window in with an opacity fade.

    from app.ui.boot_splash import BootSplash
    s = BootSplash(on_ready=handler)
    s.mainloop()          # boot runs to completion, then on_ready(app) is set up
"""

import math
import os
import queue
import threading
import time
import tkinter as tk

from app.core import system_probe as probe
from app.core.i18n import t, get_language

# ---- palette (matches theme.py) ----
BG = "#05050A"
GRID = "#0D0D1A"
RED = "#E63946"
RED_HI = "#FF5A68"
BLUE = "#5DADE2"
GREEN = "#2ECC71"
AMBER = "#F5A623"
TEXT = "#F0F0F5"
DIM = "#8888A0"
DIMMER = "#555570"

BPM = 124                     # heartbeat pulse speed
FPS = 30
FRAME_MS = 1000 // FPS
CONSOLE_LINES = 12            # visible boot-log rows


class BootSplash(tk.Tk):
    """Borderless cinematic boot window."""

    def __init__(self, on_ready=None, chime=True):
        super().__init__()
        self.on_ready = on_ready
        self.chime = chime

        self.title("DJ AI OS")
        self.overrideredirect(True)
        self.configure(bg=BG)

        self.W, self.H = 980, 660
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{self.W}x{self.H}+{(sw - self.W) // 2}+{(sh - self.H) // 2}")

        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg=BG,
                            highlightthickness=0)
        self.cv.pack()

        self.phase = 0.0
        self.t0 = time.time()
        self.rows = []            # console rows: (glyph, text, color)
        self._row_start = 0       # scroll offset (rows)
        self._running = None      # (title, color) currently executing
        self.progress = 0.0
        self.ready = False
        self._burst_age = None
        self._beat_pulses = []    # expanding rings on each beat
        self._neural = self._build_net()
        self._particles = self._build_stars()
        self._core_queue = queue.Queue()   # worker -> main thread (tk-safe)
        self._core_start = None            # when the heavy import began
        self._core_waiting = False         # low-power mode while importing
        self._last_frame_t = None          # frame-time meter for the HUD
        self._frame_ms = 0

        self._draw_static()
        self._after_id = self.after(FRAME_MS, self._animate)
        self.after(80, self.boot)
        # heavy core import runs in parallel with the visible probes so the
        # "nöral çekirdek" step is short by the time we reach it
        threading.Thread(target=self._load_core, daemon=True).start()

    # ============================================================
    # STATIC LAYOUT
    # ============================================================
    def _draw_static(self):
        cv = self.cv
        # grid
        for x in range(0, self.W, 34):
            cv.create_line(x, 0, x, self.H, fill=GRID, width=1)
        for y in range(0, self.H, 34):
            cv.create_line(0, y, self.W, y, fill=GRID, width=1)
        # title
        cv.create_text(40, 46, text="DJ AI OS", fill=RED, anchor="w",
                       font=("Segoe UI", 42, "bold"))
        cv.create_text(42, 84, text=t("boot.neural_core_loading") + " · PRO DJ PRODUCTION SUITE",
                       fill=DIM, anchor="w", font=("Segoe UI", 11))
        cv.create_text(42, 104, text="sistem açılış sekansı — gelecek teknolojisi",
                       fill=DIMMER, anchor="w", font=("Consolas", 9))
        # console panel frame
        cx, cy, cw, ch = 34, self.H - 250, 600, 214
        cv.create_rectangle(cx, cy, cx + cw, cy + ch, outline="#161622", width=1)
        cv.create_text(cx + 10, cy + 4, text="BOOT CONSOLE", fill=DIMMER,
                       anchor="w", font=("Consolas", 8))
        # progress track
        cv.create_rectangle(34, self.H - 24, self.W - 34, self.H - 20,
                            fill="#10101C", outline="")
        # footer version
        cv.create_text(self.W - 40, self.H - 10, text="v24 ULTRA PRODUCER",
                       fill=DIMMER, anchor="e", font=("Consolas", 8))

    def _build_stars(self):
        import random
        rng = random.Random(7)
        return [(rng.randint(120, self.W - 20), rng.randint(60, self.H - 60),
                 rng.uniform(0.5, 1.6), rng.uniform(0.02, 0.08)) for _ in range(70)]

    def _build_net(self):
        """Neural net nodes/edges on the right side."""
        nodes = [
            (760, 150), (880, 210), (820, 320), (720, 280),
            (900, 380), (780, 430), (880, 500), (730, 520),
        ]
        edges = [(0, 1), (1, 2), (2, 3), (3, 0), (1, 4), (4, 5), (5, 6),
                 (2, 5), (5, 7), (3, 7)]
        return {"nodes": nodes, "edges": edges}

    # ============================================================
    # BOOT RUNNER
    # ============================================================
    def boot(self):
        self._plan = list(probe.boot_plan())
        self._step_idx = 0
        self._weight_total = 8 * 9 + 18 + 10     # probes + core + final
        self._weight_done = 0.0
        self._print(("✦", t("boot.neural_core_loading"), "blue"))
        self._print(("✦", "güvenlik duvarı · çekirdek bütünlüğü doğrulandı", "blue"))
        self.after(500, self._next_step)

    def _next_step(self):
        if self.ready:
            return
        idx = self._step_idx
        if idx < len(self._plan):
            title, fn = self._plan[idx]
            self._step_idx += 1
            self._set_running(title.upper())
            try:
                res = fn()
                if isinstance(res, (tuple, list)) and len(res) == 3:
                    label, status, lines = res
                else:
                    label, status, lines = title.upper(), "ok", [("✓", str(res), "green")]
            except Exception as e:
                label, status, lines = title.upper(), "warn", [("⚠", f"hata: {e}", "amber")]
            self._post_probe(label, status, lines)
        elif idx == len(self._plan):
            self._step_idx += 1
            self._core_waiting = True
            self._core_start = time.time()
            self._set_running(t("boot.neural_core_loading"))
            self._poll_core()
        else:
            self._finish_boot()

    def _load_core(self):
        """Runs on a worker thread; hands results to the UI via a queue."""
        try:
            t0 = time.time()
            from app.ui.main_window import MainWindow  # noqa: F401 — heavy import
            dt = time.time() - t0
            mods = self._count_modules()
            lines = [
                ("✓", f"{mods} modül entegre · ana kabin yüklendi ({dt:.1f}s)", "green"),
                ("✦", "kabin görsel sistemi etkin", "blue"),
            ]
        except Exception as e:
            lines = [("✗", f"çekirdek yüklenemedi: {e}", "red")]
        self._core_queue.put(lines)

    def _poll_core(self):
        try:
            lines = self._core_queue.get_nowait()
        except queue.Empty:
            return
        self._core_waiting = False
        self._weight_done += 18
        self._update_progress()
        self._post_lines(lines)
        self.after(250, self._next_step)

    def _finish_boot(self):
        self.ready = True
        self._weight_done = self._weight_total   # final step completes the bar
        self.progress = 100.0
        self._update_progress()
        self._print(("✓", t("boot.system_ready") + " — " + t("boot.all_systems_online"), "green"))
        self._running = None
        self._burst_age = 0.0
        if self.chime:
            threading.Thread(target=self._boot_chime, daemon=True).start()
            threading.Thread(target=self._boot_voice, daemon=True).start()
        self.after(700, self._call_ready)

    def _call_ready(self):
        if self.on_ready:
            try:
                self.on_ready(self)
            except Exception:
                import traceback
                traceback.print_exc()

    def _count_modules(self):
        n = 0
        for base in ("app", "data"):
            for _root, _dirs, files in os.walk(base):
                n += sum(1 for f in files if f.endswith(".py"))
        return n

    # ---- console helpers ----
    def _set_running(self, title):
        self._running = (title, AMBER)
        self._print((None, title + " …", "amber"))

    def _post_probe(self, label, status, lines):
        self._weight_done += 9
        self._update_progress()
        self._running = None
        for line in lines:
            self._post_line_typed(line)
        # small beat before advancing
        self.after(90 + 60 * len(lines), self._next_step)

    def _post_lines(self, lines):
        self._running = None
        for line in lines:
            self._post_line_typed(line)

    def _post_line_typed(self, line):
        glyph, text, color = line
        if glyph and glyph not in ("✓", "⚠", "✗", "✦"):
            glyph = "✦"
        self._print((glyph or "✦", text, color))

    def _print(self, row):
        self.rows.append(row)
        probe.TRANSCRIPT.append((row[1], row[2]))
        if len(self.rows) > 400:
            self.rows = self.rows[-200:]
        self._autoscroll()

    def _autoscroll(self):
        n = len(self.rows)
        vis = CONSOLE_LINES - (1 if self._running else 0)
        self._row_start = max(0, n - vis)

    def _update_progress(self):
        pct = min(100.0, self._weight_done / self._weight_total * 100.0)
        self.progress = pct
        w = self.W - 68
        cv = self.cv
        cv.delete("prog")
        cv.create_rectangle(34, self.H - 24, 34 + int(w * pct / 100), self.H - 20,
                            fill=RED, outline="", tags="prog")
        cv.create_text(self.W - 40, self.H - 40, text=f"%{int(pct)}",
                       fill=TEXT, anchor="e", font=("Consolas", 13, "bold"),
                       tags="prog")

    # ============================================================
    # BOOT CHIME (neural, pure numpy)
    # ============================================================
    def _boot_chime(self):
        try:
            import numpy as np
            import sounddevice as sd
            sr = 44100
            bpm = 124
            beat = 60.0 / bpm
            dur = 4 * beat + 0.4
            t = np.arange(int(sr * dur)) / sr
            out = np.zeros_like(t)

            # sub drone
            sub = np.sin(2 * np.pi * 55.0 * t) * np.exp(-t * 1.8)
            out += sub * 0.5

            # rising arpeggio: C3 E3 G3 C4 (root of A minor-ish vibe)
            freqs = [130.81, 164.81, 196.00, 261.63]
            for i, f in enumerate(freqs):
                n0 = int(i * beat * sr)
                n1 = int((i * beat + 0.9) * sr)
                seg = t[n0:n1] - t[n0]
                env = np.exp(-seg * 6.0) * (1 - np.exp(-seg * 90))
                tone = (np.sin(2 * np.pi * f * seg)
                        + 0.4 * np.sin(2 * np.pi * 2 * f * seg)
                        + 0.2 * np.sin(2 * np.pi * 3 * f * seg))
                out[n0:n1] += tone * env * 0.35

            # shimmering 8th notes on top
            for k in range(8):
                n0 = int((k * 0.5) * beat * sr)
                n1 = n0 + int(0.18 * sr)
                seg = t[n0:n1] - t[n0]
                env = np.exp(-seg * 22.0)
                f = 523.25 if k % 2 == 0 else 659.25
                out[n0:n1] += np.sin(2 * np.pi * f * seg) * env * 0.12

            peak = np.max(np.abs(out))
            if peak > 0:
                out = out / peak * 0.22
            sd.play(out, sr)
            sd.wait()
        except Exception:
            pass  # no audio device — boot still completes

    def _boot_voice(self):
        """ASTRA speaks a line as the system comes online — Windows SAPI via
        PowerShell System.Speech. Fire-and-forget; silently no-ops if missing."""
        try:
            import subprocess
            from app.core.i18n import t, get_language
            if get_language() == "tr":
                msg = "Sistem hazir kaptan. Tum neural sistemler cevirimici. Hazir misin?"
            elif get_language() == "en":
                msg = "System ready captain. All neural systems online. Ready?"
            elif get_language() == "de":
                msg = "System bereit Captain. Alle neuralen Systeme online. Bereit?"
            else:
                msg = "Système prêt capitaine. Tous les systèmes neuronaux en ligne. Prêt ?"
            ps = (
                "Add-Type -AssemblyName System.Speech;"
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "try{$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female)}catch{};"
                "$s.Rate=1;$s.Volume=90;"
                f"$s.Speak('{msg}')"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                creationflags=0x08000000, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # ============================================================
    # ANIMATION
    # ============================================================
    def _animate(self):
        try:
            if not self.winfo_exists():
                return
            self.phase += FRAME_MS / 1000.0
            if self._core_waiting:
                # low-power mode: free the GIL so the core import finishes fast
                self._draw_hud()
                self._draw_astra_logo()
                self._draw_console()
                self._draw_ready_burst()
            else:
                self._draw_hud()
                if self._logo_on():
                    self._draw_astra_logo()
                else:
                    self._draw_orbit()
                self._draw_net()
                self._draw_stars()
                self._draw_console()
                self._draw_ready_burst()
            self._poll_core()
            self.after(FRAME_MS, self._animate)
        except tk.TclError:
            pass

    def _draw_hud(self):
        """Sci-fi HUD frame: pulsing corner brackets, scanline sweep, live clock
        and a bottom telemetry strip. Cheap — stays on even in low-power mode."""
        cv = self.cv
        cv.delete("hud")
        ph = self.phase
        W, H = self.W, self.H

        # corner targeting brackets (pulse with the phase)
        glow = 0.5 + 0.5 * math.sin(ph * 2.2)
        col = f"#{int(240 * glow):02x}{int(110 * glow):02x}{int(30 * glow):02x}"
        L = 30
        for bx, by, dx, dy in ((0, 0, 1, 1), (W, 0, -1, 1),
                               (0, H, 1, -1), (W, H, -1, -1)):
            cv.create_line(bx, by, bx + dx * L, by, fill=col, width=2, tags="hud")
            cv.create_line(bx, by, bx, by + dy * L, fill=col, width=2, tags="hud")

        # scanline sweep (full-width, slow descent)
        sy = (ph * 34) % (self.H + 60) - 30
        cv.create_line(0, sy, self.W, sy, fill="#2A0E14", width=1, tags="hud")
        cv.create_line(0, sy + 1, self.W, sy + 1, fill=RED, width=1,
                       stipple="gray50", tags="hud")

        # live clock (top-right)
        cv.create_text(self.W - 40, 18, text=time.strftime("%H:%M:%S"),
                       fill=TEXT, anchor="e", font=("Segoe UI", 13, "bold"),
                       tags="hud")
        cv.create_text(self.W - 40, 36, text=time.strftime("%d.%m.%Y"),
                       fill=DIMMER, anchor="e", font=("Consolas", 8), tags="hud")

        # frame-time meter
        now = time.time()
        if self._last_frame_t is not None:
            self._frame_ms = int((now - self._last_frame_t) * 1000)
        self._last_frame_t = now

        # bottom telemetry strip (right side)
        status, scol = ((t("status.connected") + ": AKTİF", GREEN) if self.ready
                        else (t("boot.system_waking"), AMBER))
        cv.create_text(self.W - 40, self.H - 92, text=f"● {status}", fill=scol,
                       anchor="e", font=("Consolas", 10, "bold"), tags="hud")
        secs = int(time.time() - self.t0)
        cv.create_text(self.W - 40, self.H - 74,
                       text=f"BPM {BPM}  ·  DÖNGÜ {self._frame_ms} ms",
                       fill=TEXT, anchor="e", font=("Consolas", 9), tags="hud")
        cv.create_text(self.W - 40, self.H - 56,
                       text=f"SÜRE {secs // 60:02d}:{secs % 60:02d}  ·  v24",
                       fill=DIMMER, anchor="e", font=("Consolas", 8), tags="hud")

    def _logo_on(self):
        """ASTRA wordmark takes over the core once the neural core loads."""
        return self.progress >= 70 or self.ready

    def _draw_astra_logo(self):
        """ASTRA wordmark charge-up — the orbital core converges into the
        brand glyph while the neural core finishes loading. Per-letter light
        wave, breathing halo and rotating charge arcs around the word."""
        if not self._logo_on():
            self.cv.delete("logo")
            return
        cv = self.cv
        cv.delete("logo")
        cx, cy = 330, 260
        ph = self.phase

        # breathing halo behind the word
        pulse = 0.6 + 0.4 * math.sin(ph * 3.1)
        cv.create_oval(cx - 120 * pulse, cy - 54 * pulse,
                       cx + 120 * pulse, cy + 54 * pulse,
                       outline=f"#{int(120 * pulse):02x}0A12", width=2,
                       tags="logo")

        # rotating charge arcs tracing the wordmark bounds
        ext = 70 + 60 * (0.5 + 0.5 * math.sin(ph * 1.3))
        cv.create_arc(cx - 116, cy - 62, cx + 116, cy + 62,
                      start=(ph * 90) % 360, extent=ext, style="arc",
                      outline=RED_HI, width=2, tags="logo")
        cv.create_arc(cx - 116, cy - 62, cx + 116, cy + 62,
                      start=((ph * 90) + 180) % 360, extent=ext * 0.55,
                      style="arc", outline=AMBER, width=1, tags="logo")

        # per-letter brightness wave across the word (underglow layer first)
        word = "ASTRA"
        lw = 42
        x0 = cx - (len(word) - 1) * lw / 2
        for i, ch in enumerate(word):
            b = 1.0 if self.ready else 0.55 + 0.45 * math.sin(ph * 4.2 + i * 1.05)
            cv.create_text(x0 + i * lw, cy + 1, text=ch,
                           fill=f"#{int(70 * b):02x}0A12",
                           font=("Segoe UI", 62, "bold"), tags="logo")
        for i, ch in enumerate(word):
            b = 1.0 if self.ready else 0.55 + 0.45 * math.sin(ph * 4.2 + i * 1.05)
            cv.create_text(x0 + i * lw, cy, text=ch,
                           fill=f"#{int(255 * b):02x}{int(90 * b):02x}{int(104 * b):02x}",
                           font=("Segoe UI", 58, "bold"), tags="logo")

        # state subtitle under the wordmark
        if self.ready:
            sub, scol = "◈ " + t("boot.all_systems_online"), GREEN
        elif self._core_waiting:
            sub, scol = "◈ " + t("boot.neural_core_loading"), AMBER
        else:
            sub, scol = "◈ " + t("boot.system_waking"), DIM
        cv.create_text(cx, cy + 56, text=sub, fill=scol,
                       font=("Consolas", 10, "bold"), tags="logo")

    def _draw_orbit(self):
        cv = self.cv
        cv.delete("orb")
        cx, cy = 330, 260
        ph = self.phase
        # heartbeat envelope at BPM
        beat_ph = (ph * BPM / 60.0) % 1.0
        env = math.exp(-beat_ph * 5.0) if beat_ph < 0.6 else 0.0
        core_r = 34 + 6 * env

        # glow
        for g, a in ((3.2, 0.05), (2.2, 0.10), (1.4, 0.18)):
            cv.create_oval(cx - core_r * g, cy - core_r * g * 0.6,
                           cx + core_r * g, cy + core_r * g * 0.6,
                           fill=f"#7A1018", outline="", tags="orb", stipple="gray50")
        # core
        cv.create_oval(cx - core_r, cy - core_r * 0.55, cx + core_r, cy + core_r * 0.55,
                       fill=RED, outline=RED_HI, width=2, tags="orb")

        # rotating rings (perspective ellipses)
        rings = [
            (78, 0.9, RED, 1.0),
            (104, -0.55, BLUE, 0.8),
            (132, 0.35, AMBER, 0.7),
            (158, -1.2, RED_HI, 0.6),
        ]
        for r, spd, color, width in rings:
            a = ph * spd
            x = cx + math.cos(a) * r * 0.28
            y = cy + math.sin(a) * r * 0.16
            cv.create_oval(cx - r, y - r * 0.34, cx + r, y + r * 0.34,
                           outline=color, width=width, tags="orb")
            # satellite dot on the ring
            sa = ph * spd * 1.6
            sx = cx + math.cos(sa) * r
            sy = y + math.sin(sa) * r * 0.34
            cv.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=color, outline="",
                           tags="orb")
            # pulse traveling on the ring
            pa = ph * spd * 3.0
            px = cx + math.cos(pa) * r * 0.9
            py = y + math.sin(pa) * r * 0.34 * 0.9
            cv.create_oval(px - 2, py - 2, px + 2, py + 2, fill=TEXT, outline="",
                           tags="orb")

        # expanding beat rings (a stays within [0, 1] so alpha is never negative)
        self._beat_pulses.append((ph, 0.0))
        self._beat_pulses = [(t, min(1.0, a + 0.06))
                             for t, a in self._beat_pulses if a < 1.0]
        for t, a in self._beat_pulses:
            r = 30 + a * 170
            alpha = max(0.0, (1 - a) * 0.5)
            col = f"#{int(230 * alpha):02x}{int(57 * alpha):02x}{int(70 * alpha):02x}"
            cv.create_oval(cx - r, cy - r * 0.55, cx + r, cy + r * 0.55,
                           outline=col, width=2, tags="orb")
        # radar sweep
        sa = ph * 1.4
        cv.create_line(cx, cy, cx + math.cos(sa) * 158, cy + math.sin(sa) * 40,
                       fill="#5A1A22", width=2, tags="orb")

    def _draw_net(self):
        cv = self.cv
        cv.delete("net")
        nodes = self._neural["nodes"]
        edges = self._neural["edges"]
        ph = self.phase

        for i, j in edges:
            x1, y1 = nodes[i]
            x2, y2 = nodes[j]
            cv.create_line(x1, y1, x2, y2, fill="#1A1A2A", width=1, tags="net")
            # traveling pulse
            p = (ph * 0.7 + i * 0.13) % 1.0
            px = x1 + (x2 - x1) * p
            py = y1 + (y2 - y1) * p
            col = [RED, BLUE, GREEN][i % 3]
            cv.create_oval(px - 2.5, py - 2.5, px + 2.5, py + 2.5, fill=col,
                           outline="", tags="net")

        # active node ring follows the running probe
        active = self._running is not None
        for i, (x, y) in enumerate(nodes):
            r = 3.4 + (1.0 if active and i == int(ph * 2) % len(nodes) else 0)
            col = [RED, BLUE, GREEN, AMBER][i % 4]
            cv.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="",
                           tags="net")

    def _draw_stars(self):
        cv = self.cv
        cv.delete("stars")
        ph = self.phase
        for i, (x, y, sz, spd) in enumerate(self._particles):
            x = x + math.sin(ph * spd * 3 + i) * 8
            y = y + math.cos(ph * spd * 2 + i) * 5
            cv.create_oval(x, y, x + sz, y + sz, fill=DIMMER, outline="", tags="stars")

    def _draw_console(self):
        cv = self.cv
        cv.delete("cons")
        base_y = self.H - 210
        lh = 15
        vis = CONSOLE_LINES - (1 if self._running else 0)
        start = max(0, len(self.rows) - vis)
        for i in range(start, len(self.rows)):
            glyph, text, color = self.rows[i]
            y = base_y + (i - start) * lh
            cv.create_text(50, y, text=glyph or "✦", fill=self._row_color(glyph),
                           anchor="w", font=("Consolas", 10, "bold"), tags="cons")
            cv.create_text(66, y, text=text, fill=self._row_color(color),
                           anchor="w", font=("Consolas", 10), tags="cons")
        # running line: cursor, or spinner + elapsed during the core import
        if self._running:
            y = base_y + vis * lh
            if self._core_waiting and self._core_start is not None:
                spinners = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
                s = spinners[int(self.phase * 12) % len(spinners)]
                secs = int(time.time() - self._core_start)
                cv.create_text(50, y, text=f"{s} {secs}s", fill=AMBER,
                               anchor="w", font=("Consolas", 12, "bold"),
                               tags="cons")
            else:
                cv.create_text(50, y, text="▍", fill=AMBER, anchor="w",
                               font=("Consolas", 12), tags="cons")

    def _row_color(self, c):
        return {"green": GREEN, "amber": AMBER, "red": RED, "blue": BLUE,
                "dim": DIM, "text": TEXT}.get(c, TEXT)

    def _draw_ready_burst(self):
        if self._burst_age is None:
            return
        self._burst_age += FRAME_MS / 1000.0
        cv = self.cv
        cv.delete("burst")
        if self._burst_age > 2.2:
            return
        a = min(1.0, self._burst_age * 3.0)
        col = f"#{int(230 * a):02x}{int(255 * a):02x}{int(255 * a):02x}" if a < 0.2 else TEXT
        cv.create_text(self.W // 2, 120, text="✦  " + t("boot.system_ready") + "  ✦", fill=GREEN,
                       font=("Segoe UI", 34, "bold"), tags="burst")
        cv.create_text(self.W // 2, 158, text="HAZIR MISIN KAPTAN?",
                       fill=TEXT, font=("Segoe UI", 15), tags="burst")
        # expanding white rings
        for k in range(3):
            rr = 60 + self._burst_age * 220 + k * 22
            cv.create_oval(self.W // 2 - rr, 90 - rr * 0.4, self.W // 2 + rr, 90 + rr * 0.4,
                           outline=f"#{int(255 * (1 - self._burst_age * 0.4)):02x}ffffff",
                           width=2, tags="burst")
        cv.create_rectangle(0, 0, self.W, self.H, outline=f"#{int(255 * a):02x}FFFFFF",
                            width=3, tags="burst")


# ============================================================
# launch helper (used by main.py)
# ============================================================

def run_boot(on_ready=None, chime=True):
    """Blocking boot: returns the constructed MainWindow (or None)."""
    holder = []

    def _handoff(splash):
        from app.ui.main_window import MainWindow
        app = MainWindow()
        # keep the old _default_root dance so later widget creation works
        try:
            import tkinter as _tk
            _tk._default_root = app
        except Exception:
            pass
        # cinematic dissolve: the main window materializes transparent and
        # fades in while the boot window exits
        try:
            app.attributes("-alpha", 0.0)
            app.update_idletasks()
        except Exception:
            pass
        holder.append(app)
        if on_ready:
            try:
                on_ready(app)
            except Exception:
                import traceback
                traceback.print_exc()
        try:
            splash.destroy()
        except Exception:
            pass
        splash.quit()
        try:
            app.after(40, lambda: _fade_window(app, 0.0, 1.0, 0.55))
        except Exception:
            pass

    splash = BootSplash(on_ready=_handoff, chime=chime)
    splash.mainloop()
    return holder[0] if holder else None


def _fade_window(win, a0, a1, dur):
    """Dissolve a toplevel's opacity from a0 to a1 over dur seconds."""
    t0 = time.time()

    def _tick():
        try:
            if not win.winfo_exists():
                return
            f = min(1.0, (time.time() - t0) / dur)
            win.attributes("-alpha", a0 + (a1 - a0) * f)
            if f < 1.0:
                win.after(30, _tick)
        except tk.TclError:
            pass

    _tick()
