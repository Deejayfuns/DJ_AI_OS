#!/usr/bin/env python3
"""
DJ AI OS — Version Policy Validation (CI gate)

Ensures single source of truth for version:
- app/config/version.py: AUTHORITATIVE (APP_VERSION)
- pyproject.toml: MUST match APP_VERSION
- build_exe.py: MUST read from APP_VERSION (already does)

Exit codes:
  0 = all in sync
  1 = mismatch detected
  2 = file missing or parse error
"""

import sys
import re
import tomllib
from pathlib import Path

# Add project root to path for version import
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.version import APP_VERSION


def get_pyproject_version() -> str:
    """Read version from pyproject.toml."""
    pyproject_path = ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    version = data.get("project", {}).get("version")
    if not version:
        raise ValueError("pyproject.toml: [project].version not found")
    return version


def get_build_exe_version_read_method() -> str:
    """
    Verify build_exe.py reads version from app.config.version.APP_VERSION.
    Returns the method used.
    """
    build_path = ROOT / "build_exe.py"
    if not build_path.exists():
        raise FileNotFoundError(f"build_exe.py not found at {build_path}")

    content = build_path.read_text(encoding="utf-8")

    # Check it imports from app.config.version (various patterns)
    # Pattern 1: standard import
    if "from app.config.version import" in content or "import app.config.version" in content:
        if "APP_VERSION" in content or "version()" in content:
            return "reads_from_app_config_version"

    # Pattern 2: dynamic import via importlib (used by build_exe.py for standalone runs)
    if "app/config/version.py" in content and "APP_VERSION" in content:
        if "importlib.util" in content or "spec_from_file_location" in content:
            return "reads_from_app_config_version"

    # Fallback: check if it has its own version definition
    match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return f"hardcoded:{match.group(1)}"

    return "unknown"


def validate_version_sync() -> tuple[bool, list[str]]:
    """
    Validate all version sources are in sync.
    Returns (ok, messages).
    """
    messages = []
    ok = True

    # 1. Authoritative version
    authoritative = APP_VERSION
    messages.append(f"Authoritative (app/config/version.py): {authoritative}")

    # 2. pyproject.toml
    try:
        pyproject_ver = get_pyproject_version()
        messages.append(f"pyproject.toml: {pyproject_ver}")
        if pyproject_ver != authoritative:
            messages.append(f"  ❌ MISMATCH: pyproject.toml != authoritative")
            ok = False
        else:
            messages.append(f"  ✅ MATCH")
    except Exception as e:
        messages.append(f"  ❌ ERROR reading pyproject.toml: {e}")
        ok = False

    # 3. build_exe.py
    try:
        build_method = get_build_exe_version_read_method()
        messages.append(f"build_exe.py: {build_method}")
        if build_method != "reads_from_app_config_version":
            messages.append(f"  ❌ build_exe.py does not read from app.config.version")
            ok = False
        else:
            messages.append(f"  ✅ Reads from authoritative source")
    except Exception as e:
        messages.append(f"  ❌ ERROR checking build_exe.py: {e}")
        ok = False

    return ok, messages


def main():
    print("=== DJ AI OS Version Policy Validation ===\n")

    ok, messages = validate_version_sync()

    for msg in messages:
        print(msg)

    print()
    if ok:
        print("✅ ALL VERSION SOURCES IN SYNC")
        return 0
    else:
        print("❌ VERSION SYNC FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())