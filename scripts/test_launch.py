"""Dev tool: full launch integration test — boot -> MainWindow handoff.

Run from repo root:
    python scripts/test_launch.py

Drives the cinematic boot to completion, constructs the real MainWindow,
pumps the event loop so the ASTRA captain greeting card builds, then
tears everything down. Exits 0 on success.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app.ui.boot_splash import run_boot
    from app.core import system_probe as probe

    app = run_boot(chime=False)
    if app is None:
        print("LAUNCH FAILED: run_boot returned None")
        sys.exit(1)

    # pump until the captain greeting has built
    deadline = time.time() + 20.0
    card = None
    while time.time() < deadline:
        try:
            app.update()
        except Exception:
            break
        card = getattr(app, "_welcome_card", None)
        if card is not None and card.winfo_exists():
            break
        time.sleep(0.03)

    boot_logged = getattr(app, "_boot_logged", 0)
    n_ai_log = len(getattr(app, "ai_messages", []))
    print(f"main window ready: title={app.title()}  lib={len(app.saved_tracks or [])}")
    print(f"welcome_card_built={card is not None and card.winfo_exists()}")
    print(f"boot_lines_into_log={boot_logged}  ai_messages={n_ai_log}")

    try:
        if card is not None and card.winfo_exists():
            card.destroy()
    except Exception:
        pass
    try:
        app.destroy()
    except Exception:
        pass

    if card is None:
        print("LAUNCH FAILED: welcome card never built")
        sys.exit(1)
    print("LAUNCH SMOKE OK")


if __name__ == "__main__":
    main()
