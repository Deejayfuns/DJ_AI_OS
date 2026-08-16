#!/usr/bin/env python3
"""CI helper: verify build_exe.py imports cleanly and reports version."""
import build_exe
print('build_exe.py imports OK')
print('Version:', build_exe.get_version())
