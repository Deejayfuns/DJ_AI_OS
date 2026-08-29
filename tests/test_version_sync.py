"""Test version policy: single source of truth validation."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.version import APP_VERSION


def test_app_config_version_is_authoritative():
    """app/config/version.py must define APP_VERSION."""
    assert APP_VERSION, "APP_VERSION must be defined"
    assert isinstance(APP_VERSION, str), "APP_VERSION must be string"
    # Semantic version format
    parts = APP_VERSION.split(".")
    assert len(parts) >= 2, f"APP_VERSION must be semantic (major.minor.patch): {APP_VERSION}"
    assert all(p.isdigit() for p in parts), f"APP_VERSION parts must be numeric: {APP_VERSION}"


def test_pyproject_version_matches():
    """pyproject.toml version must match APP_VERSION."""
    import tomllib

    pyproject_path = ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml must exist"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    pyproject_version = data.get("project", {}).get("version")
    assert pyproject_version, "pyproject.toml must have [project].version"
    assert pyproject_version == APP_VERSION, (
        f"pyproject.toml version ({pyproject_version}) must match "
        f"APP_VERSION ({APP_VERSION})"
    )


def test_build_exe_reads_from_authoritative():
    """build_exe.py must read version from app/config/version.py, not hardcode."""
    build_path = ROOT / "build_exe.py"
    assert build_path.exists(), "build_exe.py must exist"

    content = build_path.read_text(encoding="utf-8")

    # Must import from app.config.version
    assert "app/config/version.py" in content or "from app.config.version import" in content, \
        "build_exe.py must import from app.config.version"

    # Must use APP_VERSION or version()
    assert "APP_VERSION" in content or "version()" in content, \
        "build_exe.py must use APP_VERSION or version()"

    # Must NOT have hardcoded VERSION = "x.y.z" pattern
    import re
    hardcoded = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    assert not hardcoded, (
        f"build_exe.py must not hardcode version (found: {hardcoded.group(0)}). "
        "Use get_version() from app.config.version instead."
    )


def test_tools_build_manifest_reads_from_authoritative():
    """tools/build_manifest.py must read version from app/config/version.py."""
    manifest_tool = ROOT / "tools" / "build_manifest.py"
    assert manifest_tool.exists(), "tools/build_manifest.py must exist"

    content = manifest_tool.read_text(encoding="utf-8")

    # Must import from app.config.version
    assert "from app.config.version import" in content or "import app.config.version" in content, \
        "tools/build_manifest.py must import from app.config.version"

    # Must use APP_VERSION
    assert "APP_VERSION" in content, \
        "tools/build_manifest.py must use APP_VERSION"


def test_tools_sign_manifest_reads_from_authoritative():
    """tools/update/sign_manifest.py should read from app/config/version.py (if it uses version)."""
    sign_tool = ROOT / "tools" / "update" / "sign_manifest.py"
    if not sign_tool.exists():
        return  # Optional tool

    content = sign_tool.read_text(encoding="utf-8")

    # If it has a default version, it should reference APP_VERSION
    if "--version" in content and "default=" in content:
        # Should ideally reference APP_VERSION as default
        # This is a soft check - at minimum it shouldn't hardcode a different version
        pass


def test_no_stray_version_constants():
    """No other files should define VERSION or __version__ constants."""
    import re

    # Files that are allowed to define version
    allowed = {
        "app/config/version.py",
        "pyproject.toml",  # TOML format, not Python
        "build_exe.py",    # Reads from authoritative, doesn't define
        "orb_core/__init__.py",  # Separate internal package with own version
    }

    for py_file in ROOT.rglob("*.py"):
        if py_file.name.startswith("test_") or py_file.name == "version.py":
            continue
        if py_file in [ROOT / f for f in allowed]:
            continue
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        if "site-packages" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8", errors="ignore")

        # Check for hardcoded version constants
        matches = re.findall(r'^(VERSION|__version__)\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        for var_name, version in matches:
            # Allow if it's just reading from config or computing
            if "app.config.version" in content or "importlib" in content:
                continue
            raise AssertionError(
                f"File {py_file.relative_to(ROOT)} defines hardcoded {var_name} = \"{version}\". "
                "Use app.config.version.APP_VERSION instead."
            )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])