"""
DJ AI OS — System Probe (boot diagnostics)

Gathers REAL machine state for the cinematic boot sequence and the
captain greeting. No fake numbers: every value is read live from the
hardware / OS / app on every boot.

Each probe returns:
    (title, status, [ (glyph, text, color_key), ... ])
where status is one of "ok" / "warn" / "info" and glyph is one of
"✓" (ok), "⚠" (warn), "✗" (fail), "✦" (info), "▶" (running).

Everything is wrapped so a missing device / driver can never block boot.
"""

import os
import platform
import threading
import time

TRANSCRIPT = []      # boot console lines, forwarded to the main log on launch
BOOT_STARTED = time.time()


# ============================================================
# helpers
# ============================================================

def _fmt_gb(n):
    return f"{n / (1024 ** 3):.1f} GB"


def _neural_model_path():
    for cand in (os.path.join("DJ_EXPORTS", "neural_models"),
                 os.path.join(os.getcwd(), "DJ_EXPORTS", "neural_models")):
        for name in ("default_quick.pt", "custom_quick.pt"):
            p = os.path.join(cand, name)
            if os.path.exists(p):
                return p
    return None


def _find_rekordbox_xml():
    """Bounded search (never scans whole drives) for a Rekordbox export."""
    roots = [os.path.expanduser("~"), os.path.expanduser("~/Documents"),
             os.path.expanduser("~/Music"), os.getcwd()]
    for root in dict.fromkeys(roots):
        if not root or not os.path.isdir(root):
            continue
        p = os.path.join(root, "rekordbox.xml")
        if os.path.isfile(p):
            return p
        # one level down, bounded
        try:
            for entry in os.listdir(root):
                cand = os.path.join(root, entry, "rekordbox.xml")
                if os.path.isfile(cand):
                    return cand
        except OSError:
            continue
    return None


# ============================================================
# probes
# ============================================================

def probe_platform():
    sys = platform.system()
    rel = platform.release()
    arch = platform.machine()
    return ("PLATFORM", "info", [
        ("✦", f"KERNEL {sys} {rel} · {arch}", "blue"),
    ])


def probe_version():
    try:
        from app.ai.version_detector import detect_version
        ver = detect_version()
    except Exception:
        ver = "v24 ULTRA PRODUCER"
    return ("ÇEKİRDEK", "info", [
        ("✦", f"DJ AI OS {ver} · nöral çekirdek", "blue"),
    ])


def probe_cpu():
    try:
        import psutil
        pct = psutil.cpu_percent(interval=0.2)
        freqs = psutil.cpu_freq()
        ghz = f" · {freqs.current / 1000:.1f} GHz" if freqs else ""
        status = "ok" if pct < 70 else "warn"
        color = "green" if pct < 70 else "amber"
        return ("İŞLEMCİ", status, [
            (f"✓" if status == "ok" else "⚠", f"YÜK {pct:.0f}%{ghz} · {psutil.cpu_count(logical=True)} mantıksal çekirdek", color),
        ])
    except Exception as e:
        return ("İŞLEMCİ", "warn", [("⚠", f"ölçülemedi ({type(e).__name__})", "amber")])


def probe_ram():
    try:
        import psutil
        vm = psutil.virtual_memory()
        status = "ok" if vm.percent < 85 else "warn"
        color = "green" if vm.percent < 85 else "amber"
        return ("BELLEK", status, [
            (f"✓" if status == "ok" else "⚠", f"%{vm.percent:.0f} · {_fmt_gb(vm.used)} / {_fmt_gb(vm.total)}", color),
        ])
    except Exception as e:
        return ("BELLEK", "warn", [("⚠", f"ölçülemedi ({type(e).__name__})", "amber")])


def probe_audio():
    try:
        import sounddevice as sd
        names = []
        for i, dev in enumerate(sd.query_devices()):
            if dev.get("max_output_channels", 0) > 0:
                names.append(dev.get("name", f"device {i}"))
        if names:
            label = names[0] if len(names) == 1 else names[0]
            return ("SES MOTORU", "ok", [
                ("✓", f"{label}  (+{len(names) - 1} çıkış)", "green"),
            ])
        return ("SES MOTORU", "warn", [("⚠", "çıkış aygıtı bulunamadı", "amber")])
    except Exception as e:
        return ("SES MOTORU", "warn", [("⚠", f"sounddevice ({type(e).__name__})", "amber")])


def probe_midi():
    try:
        import mido
        ins = mido.get_input_names()
        outs = mido.get_output_names()
        total = len(ins) + len(outs)
        if total:
            shown = ", ".join((ins or outs)[:3])
            return ("MIDI", "ok", [
                ("✓", f"{total} port · {shown}", "green"),
            ])
        return ("MIDI", "warn", [("⚠", "hiçbir MIDI portu yok — Pioneer bağlantısı bekleniyor", "amber")])
    except Exception as e:
        return ("MIDI", "warn", [("⚠", f"mido ({type(e).__name__})", "amber")])


def probe_neural():
    p = _neural_model_path()
    if p:
        return ("NÖRAL MODEL", "ok", [
            ("✓", f"VAE önbellekte hazır · {os.path.basename(os.path.dirname(p))}", "green"),
        ])
    return ("NÖRAL MODEL", "info", [
        ("✦", "ilk sentezde eğitilecek (~18 sn, tek seferlik)", "blue"),
    ])


def probe_rekordbox():
    p = _find_rekordbox_xml()
    if p:
        return ("REKORDBOX", "ok", [
            ("✓", f"export bulundu · {os.path.basename(os.path.dirname(p))}", "green"),
        ])
    return ("REKORDBOX", "info", [
        ("✦", "xml bulunamadı — Rekordbox panelinden içe aktar", "blue"),
    ])


# ============================================================
# runner
# ============================================================

def boot_plan():
    """Ordered (title, probe_fn) list shown during the cinematic boot."""
    return [
        ("platform", probe_platform),
        ("version", probe_version),
        ("cpu", probe_cpu),
        ("ram", probe_ram),
        ("audio", probe_audio),
        ("midi", probe_midi),
        ("neural", probe_neural),
        ("rekordbox", probe_rekordbox),
    ]


def note(line, color="dim"):
    """Append a console line to the shared transcript (used by boot + greeting)."""
    TRANSCRIPT.append((line, color))


def transcript_lines():
    return list(TRANSCRIPT)
