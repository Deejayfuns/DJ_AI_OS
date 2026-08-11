"""
DJ AI OS — Main Entry Point

Opens with the cinematic boot sequence (orbital core, live neural net,
real system diagnostics, boot chime), then hands off to the main window
where the ASTRA captain greeting reports the boot result.

    python main.py
"""

import sys
import os
import tkinter as tk


def main():
    from app.ui.boot_splash import run_boot

    app = run_boot()
    if app is None:
        print("[DJ AI OS] boot failed — falling back to direct launch.")
        from app.ui.main_window import MainWindow
        app = MainWindow()

    app.mainloop()


if __name__ == "__main__":
    main()
