"""Dev tool: online overlay + power-down shutdown sequence smoke test.

Run from repo root:
    python scripts/test_powerdown.py

Builds the real MainWindow, pumps the event loop so the ASTRA ONLINE
entrance overlay animates its full cycle and peels away, then triggers
the animated power-down close and verifies the window destroys cleanly.
Exits 0 on success.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from app.ui.main_window import MainWindow

    app = MainWindow()
    app.update()
    print("window ready, running ASTRA ONLINE overlay...")

    # let the entrance overlay run its full cycle and peel away
    overlay_created = None
    deadline = time.time() + 8.0
    while time.time() < deadline:
        app.update()
        ov = getattr(app, "_online_canvas", None)
        if ov is not None:
            overlay_created = True
            try:
                alive = ov.winfo_exists()
            except Exception:
                alive = False
            if not alive:
                break
        time.sleep(0.02)

    peeled = bool(overlay_created) and alive is False
    print(f"online overlay created={bool(overlay_created)}  peeled_and_gone={peeled}")

    # if the overlay is still alive, wait a bit more for the peel destroy
    if not peeled and overlay_created:
        extra_deadline = time.time() + 2.0
        while time.time() < extra_deadline:
            app.update()
            ov = getattr(app, "_online_canvas", None)
            if ov is None:
                peeled = True
                break
            try:
                if not ov.winfo_exists():
                    peeled = True
                    break
            except Exception:
                peeled = True
                break
            time.sleep(0.02)
        print(f"  after extra wait: peeled={peeled}")

    # trigger the cinematic power-down
    app._on_app_close()
    destroyed = False
    deadline = time.time() + 8.0
    while time.time() < deadline:
        try:
            app.update()
        except Exception:
            destroyed = True
            break
        # check if window was destroyed
        try:
            if not app.winfo_exists():
                destroyed = True
                break
        except Exception:
            destroyed = True
            break
        time.sleep(0.02)

    print(f"power-down overlay animated and window destroyed={destroyed}")

    if not (peeled and destroyed):
        print("POWER-DOWN SMOKE FAILED")
        sys.exit(1)
    print("POWER-DOWN SMOKE OK")


if __name__ == "__main__":
    main()
