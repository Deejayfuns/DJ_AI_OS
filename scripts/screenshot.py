"""Dev tool: launch the app, render a view, and capture a screenshot.

Usage (from repo root):
    python scripts/screenshot.py out.png [view] [wait_seconds]

Requires the UI dependency subset (Faz0): customtkinter, pygame, librosa...
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import ImageGrab

from app.ui.main_window import MainWindow


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "ui_before.png"
    view = sys.argv[2] if len(sys.argv) > 2 else "dashboard"
    wait_s = float(sys.argv[3]) if len(sys.argv) > 3 else 8.0

    app = MainWindow()

    def show_view():
        try:
            app.set_view(view)
        except Exception as exc:
            print(f"set_view({view}) failed: {exc}")

    app.after(800, show_view)

    deadline = time.time() + wait_s
    while time.time() < deadline:
        app.update()
        time.sleep(0.05)

    app.update_idletasks()
    app.lift()
    try:
        app.attributes("-topmost", True)
    except Exception:
        pass
    app.update()

    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(out)
    print(f"SAVED {out} size={img.size} view={view}")
    app.destroy()


if __name__ == "__main__":
    main()
