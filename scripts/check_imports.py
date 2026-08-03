"""Dev tool: verify every active module's local imports resolve to a file.

Run from repo root:
    python scripts/check_imports.py

Exits 1 if any active module imports a module that no longer exists
(e.g. after moving dead code into legacy/). External/third-party
imports are ignored.
"""

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOCAL_TOP = {"app", "data", "scripts", "tests"}


def active_files():
    files = []
    for pattern in ("app/**/*.py", "data/**/*.py", "scripts/**/*.py", "tests/**/*.py"):
        files += glob.glob(os.path.join(ROOT, pattern), recursive=True)
    files += [os.path.join(ROOT, "main.py"), os.path.join(ROOT, "app.py")]
    return [f for f in files if "__pycache__" not in f]


def resolves(name):
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        base = os.path.join(ROOT, *parts[:i])
        if os.path.exists(base + ".py") or os.path.exists(os.path.join(base, "__init__.py")):
            return True
    return False


def check():
    problems = 0
    for f in active_files():
        try:
            tree = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError as exc:
            print(f"SYNTAX ERROR in {os.path.relpath(f, ROOT)}: {exc}")
            problems += 1
            continue

        pkg_dir = os.path.dirname(f)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in LOCAL_TOP and not resolves(alias.name):
                        print(f"MISSING: {os.path.relpath(f, ROOT)} -> import {alias.name}")
                        problems += 1
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    if node.module.split(".")[0] in LOCAL_TOP and not resolves(node.module):
                        print(f"MISSING: {os.path.relpath(f, ROOT)} -> from {node.module} import")
                        problems += 1
                elif node.level > 0:
                    parts = pkg_dir.split(os.sep)
                    base_parts = parts[: len(parts) - node.level]
                    if node.module:
                        base_parts += node.module.split(".")
                    cand = os.path.join(*base_parts)
                    if not (os.path.exists(cand + ".py") or os.path.exists(os.path.join(cand, "__init__.py"))):
                        print(f"MISSING (relative): {os.path.relpath(f, ROOT)} -> level {node.level} {node.module}")
                        problems += 1

    total = len(active_files())
    print(f"\nActive modules checked: {total}")
    print(f"Problems: {problems}")
    return problems


if __name__ == "__main__":
    sys.exit(1 if check() else 0)
