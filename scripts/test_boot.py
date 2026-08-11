"""Dev tool: drive the cinematic boot to completion (smoke test).

Run from repo root:
    python scripts/test_boot.py

Pumps the tk event loop until the boot reaches "SİSTEM HAZIR", then
verifies real probes landed in the console transcript and progress hit
100%. Skips the audio chime so the test is deterministic.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app.ui.boot_splash import BootSplash
    from app.core import system_probe as probe

    splash = BootSplash(on_ready=None, chime=False)

    deadline = time.time() + 90.0
    while time.time() < deadline:
        try:
            splash.update()
        except Exception as exc:
            print("UPDATE EXC:", type(exc).__name__, exc)
            break
        if getattr(splash, "ready", False):
            break
        time.sleep(0.03)

    ok = getattr(splash, "ready", False)
    n_console = len(splash.rows)
    n_transcript = len(probe.transcript_lines())
    pct = splash.progress
    has_ready = any("SİSTEM HAZIR" in r[1] for r in splash.rows)

    print(f"ready={ok}  progress={pct:.0f}%  console_rows={n_console}  "
          f"transcript={n_transcript}  system_hazir={has_ready}")
    print("--- last 8 console rows (ascii-safe) ---")
    for row in splash.rows[-8:]:
        glyph, text, color = row
        safe = (glyph or "").encode("ascii", "replace").decode() + " " + \
               text.encode("ascii", "replace").decode()
        print("   ", safe, "|", color)

    try:
        splash.destroy()
    except Exception:
        pass

    if not (ok and pct >= 100 and has_ready and n_console > 5):
        print("BOOT SMOKE FAILED")
        sys.exit(1)
    print("BOOT SMOKE OK")


if __name__ == "__main__":
    main()
