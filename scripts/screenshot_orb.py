"""Capture the ORB TRON neon UI window.

Usage:  python scripts/screenshot_orb.py out.png [wait_seconds]
"""
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "orb_ui.png"
    wait_s = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0

    from orb_core import Kernel

    kernel = Kernel(Path(ROOT / "orb_manifest.yaml"))
    loop = threading.Event()

    # Kernel in background thread
    def _boot():
        import asyncio
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_until_complete(kernel.start())
        loop.run_forever()

    t = threading.Thread(target=_boot, daemon=True)
    t.start()

    # Wait for ui_host running
    host = None
    for _ in range(100):
        host = kernel.get_module("ui_host")
        st = kernel.get_status()["modules"].get("ui_host")
        if host is not None and st and st["state"] == "running":
            break
        time.sleep(0.1)

    root = host.open_window("DJ AI OS — ORB NEXUS")

    # Let it render
    deadline = time.time() + wait_s
    while time.time() < deadline:
        root.update()
        time.sleep(0.05)

    root.update_idletasks()
    root.lift()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    root.update()

    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img.save(out)
    print(f"SAVED {out} size={img.size}")

    root.destroy()

    # Stop kernel
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        asyncio.get_event_loop().run_until_complete(kernel.stop())
    except Exception:
        pass


if __name__ == "__main__":
    main()