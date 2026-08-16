#!/usr/bin/env python3
"""CI helper: verify build_exe.py imports cleanly and reports version."""
import sys
from pathlib import Path
# Repo root must be in sys.path for build_exe import
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import build_exe
print('build_exe.py imports OK')
print('Version:', build_exe.get_version())
