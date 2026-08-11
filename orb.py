#!/usr/bin/env python3
"""
ORB Bootstrap — DJ AI OS Modular Launcher
==========================================
Boots the ORB kernel from orb_manifest.yaml and starts all modules.

Usage:
    python orb.py                  # headless boot (prints status, auto-stops)
    python orb.py --ui             # open the TRON neon control window
    python orb.py --hold           # keep running until Ctrl+C (headless)
    python orb.py --status         # print module grid then exit
    python orb.py --reload MIDI    # hot-reload a module by name then exit
"""
import argparse
import asyncio
import os
import signal
import sys
import threading
import time
from pathlib import Path

# Reconfigure stdout/stderr to UTF-8 so the neon banner and module grid
# (◢ ◣ ◉ ○ ─) survive Turkish/cp1254 Windows consoles.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def parse_args():
    p = argparse.ArgumentParser(description="DJ AI OS — ORB launcher")
    p.add_argument("--manifest", default=str(ROOT / "orb_manifest.yaml"),
                   help="path to orb_manifest.yaml")
    p.add_argument("--ui", action="store_true", help="open TRON neon UI window")
    p.add_argument("--hold", action="store_true", help="keep running until Ctrl+C")
    p.add_argument("--status", action="store_true", help="print status then exit")
    p.add_argument("--reload", metavar="MODULE", help="hot-reload a module")
    p.add_argument("--theme", default="tron", help="neon theme name")
    return p.parse_args()


def print_banner():
    print("=" * 60)
    print("   ◢  DJ AI OS — ORB NEXUS CORE  ◣")
    print("   Astra Nexus Runtime · Modular · Cross-Platform")
    print("=" * 60)


def print_module_grid(status):
    """Render module grid as text."""
    print("─" * 60)
    print("   MODULE GRID")
    for name, info in sorted(status["modules"].items()):
        icon = "◉" if info["state"] == "running" else "○"
        err = f"  <{info['error']}>" if info.get("error") else ""
        print(f"   {icon} {name:<16} {info['type']:<12} {info['state']:<8} v{info['version']}{err}")
    print("─" * 60)
    running = sum(1 for i in status["modules"].values() if i["state"] == "running")
    print(f"   {running}/{len(status['modules'])} modules running")
    print(f"   capabilities: {len(status['capabilities'])} registered")


async def run_headless(kernel, hold: bool, reload_name: str = None):
    """Boot, optionally reload a module, report status."""
    await kernel.start()

    if reload_name:
        try:
            await kernel.reload_module(reload_name)
            print(f"  reloaded: {reload_name}")
        except Exception as e:
            print(f"  reload failed: {e}")

    status = kernel.get_status()
    print_module_grid(status)

    if hold:
        print("\n  running... Ctrl+C to stop")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        await asyncio.sleep(0.5)

    await kernel.stop()
    print("  ORB shutdown complete")


def run_ui(kernel):
    """Run kernel in background thread + Tk UI on main thread."""
    loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(kernel.start())
            loop.run_forever()
        finally:
            loop.run_until_complete(kernel.stop())

    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()

    # Wait until ui_host is actually loaded AND running
    host = None
    for _ in range(100):
        host = kernel.get_module("ui_host")
        status = kernel.get_status()
        ui = status["modules"].get("ui_host")
        if host is not None and ui and ui["state"] == "running":
            break
        time.sleep(0.1)

    if host is None:
        print("  ui_host module not loaded — check manifest")
        sys.exit(1)

    host.open_window("DJ AI OS — ORB NEXUS")
    host.run_mainloop()

    # Stop kernel after UI closes
    loop.call_soon_threadsafe(loop.stop)


def main():
    args = parse_args()
    print_banner()

    from orb_core import Kernel

    try:
        kernel = Kernel(Path(args.manifest))
    except Exception as e:
        print(f"  manifest load failed: {e}")
        sys.exit(1)

    errors = kernel.manifest.validate()
    if errors:
        print("  manifest errors:")
        for e in errors:
            print(f"    ✗ {e}")
        sys.exit(1)

    if args.ui:
        run_ui(kernel)
    else:
        asyncio.run(run_headless(kernel, args.hold, args.reload))

    if args.status or not args.hold:
        # Already printed grid
        pass


if __name__ == "__main__":
    main()