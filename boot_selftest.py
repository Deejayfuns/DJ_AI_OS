"""Self-test: boot the app with a faulthandler watchdog.

If boot hangs, dump a traceback to boot_selftest_out.txt after N seconds and
exit. Print progress markers so we can see how far construction got.
"""
import faulthandler
import sys
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "boot_selftest_out.txt")


def _log(msg):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# Reset out file
with open(OUT, "w", encoding="utf-8") as f:
    f.write("")

# Watchdog: dump traceback after 90s of apparent hang.
faulthandler.dump_traceback_later(90, exit=True, file=open(OUT, "a", encoding="utf-8"))

_log("T0 boot starting")

try:
    from app.ui.boot_splash import run_boot
    app = run_boot(chime=False)
    if app is None:
        _log("run_boot returned None")
        sys.exit(2)
    _log("MAIN WINDOW CONSTRUCTED OK")
    app.after(3000, app.quit)
    app.mainloop()
    _log("MAINLOOP EXITED CLEANLY — BOOT OK")
    sys.exit(0)
except Exception:
    import traceback
    with open(OUT, "a", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    sys.exit(3)
