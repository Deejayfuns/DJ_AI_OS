#!/usr/bin/env python3
"""
DJ AI OS - Windows Authenticode Signing Helper

Development/test signing infrastructure for CI and local builds.
Does NOT require a production certificate - works with self-signed dev cert.

Usage:
    python tools/ci/sign_exe.py sign <exe_path>          # Sign EXE
    python tools/ci/sign_exe.py verify <exe_path>        # Verify signature

Environment variables:
    SIGNTOOL_PATH        - Optional explicit path to signtool.exe
    CODESIGN_PFX_BASE64  - Base64-encoded PFX certificate (dev or production)
    CODESIGN_PASSWORD    - PFX password
    CODESIGN_TSA_URL     - RFC3161 timestamp server URL (optional but recommended)

Examples:
    # Development with self-signed cert
    export CODESIGN_PFX_BASE64=$(base64 -w0 dev_cert.pfx)
    export CODESIGN_PASSWORD=devpass
    python tools/ci/sign_exe.py sign dist/DJ_AI_OS/DJ_AI_OS.exe

    # Verify
    python tools/ci/sign_exe.py verify dist/DJ_AI_OS/DJ_AI_OS.exe
"""

import argparse
import base64
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_signtool(explicit_path: str | None = None) -> Path | None:
    """Locate signtool.exe on Windows."""
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        return None

    # Common Windows SDK locations
    candidates = [
        Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"),
        Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"),
        Path(r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"),
        Path(r"C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe"),
        Path(r"C:\Program Files\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"),
        Path(r"C:\Program Files\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"),
    ]

    # Also check PATH
    path_signtool = shutil.which("signtool.exe")
    if path_signtool:
        candidates.insert(0, Path(path_signtool))

    for c in candidates:
        if c.exists():
            return c

    return None


def load_certificate() -> tuple[bytes | None, str | None]:
    """Load certificate from environment. Returns (pfx_bytes, password)."""
    pfx_b64 = os.environ.get("CODESIGN_PFX_BASE64")
    password = os.environ.get("CODESIGN_PASSWORD")

    if not pfx_b64:
        return None, None

    try:
        pfx_bytes = base64.b64decode(pfx_b64)
        return pfx_bytes, password or ""
    except Exception as e:
        print(f"ERROR: Failed to decode CODESIGN_PFX_BASE64: {e}", file=sys.stderr)
        return None, None


def get_tsa_url() -> str | None:
    """Get timestamp server URL from environment."""
    return os.environ.get("CODESIGN_TSA_URL")


def sign_exe(exe_path: Path, signtool: Path, pfx_bytes: bytes, password: str, tsa_url: str | None) -> bool:
    """Sign the EXE with Authenticode."""
    with tempfile.NamedTemporaryFile(suffix=".pfx", delete=False) as tmp:
        tmp.write(pfx_bytes)
        pfx_path = Path(tmp.name)

    try:
        cmd = [
            str(signtool),
            "sign",
            "/fd", "sha256",
            "/f", str(pfx_path),
            "/p", password,
        ]

        if tsa_url:
            cmd.extend(["/tr", tsa_url, "/td", "sha256"])

        cmd.append(str(exe_path))

        print(f"Signing: {exe_path}")
        print(f"Command: {' '.join(cmd[:-1])} <exe>")  # Don't log full path with potential spaces

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"SIGN FAILED (exit {result.returncode}):", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return False

        print("Sign successful")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: signtool timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"ERROR: Signing failed: {e}", file=sys.stderr)
        return False
    finally:
        # Clean up temp PFX
        try:
            pfx_path.unlink()
        except Exception:
            pass


def verify_exe(exe_path: Path, signtool: Path) -> tuple[bool, str]:
    """Verify Authenticode signature. Returns (success, details)."""
    cmd = [
        str(signtool),
        "verify",
        "/pa",   # Use default Authenticode verification policy
        "/v",    # Verbose
        str(exe_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr

        if result.returncode == 0:
            # Check for actual signature validity in output
            if "Successfully verified" in output or "Signature verified" in output:
                return True, output
            # signtool verify returns 0 even for unsigned files sometimes, check explicitly
            if "No signature found" in output or "not signed" in output.lower():
                return False, output
            return True, output
        else:
            return False, output

    except subprocess.TimeoutExpired:
        return False, "signtool verify timed out"
    except Exception as e:
        return False, f"Verification error: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="DJ AI OS Authenticode signing helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("action", choices=["sign", "verify"], help="Action to perform")
    parser.add_argument("exe_path", type=Path, help="Path to EXE file")
    parser.add_argument("--signtool", help="Explicit signtool.exe path (or SIGNTOOL_PATH env)")

    args = parser.parse_args()

    # Platform check
    if platform.system() != "Windows":
        print("ERROR: Authenticode signing only works on Windows", file=sys.stderr)
        return 2

    exe_path = args.exe_path.resolve()
    if not exe_path.exists():
        print(f"ERROR: EXE not found: {exe_path}", file=sys.stderr)
        return 1

    if not exe_path.suffix.lower() == ".exe":
        print(f"ERROR: Not an EXE file: {exe_path}", file=sys.stderr)
        return 1

    # Find signtool
    signtool = find_signtool(args.signtool or os.environ.get("SIGNTOOL_PATH"))
    if not signtool:
        print("ERROR: signtool.exe not found. Install Windows SDK or set SIGNTOOL_PATH.", file=sys.stderr)
        return 1

    print(f"Using signtool: {signtool}")

    if args.action == "sign":
        pfx_bytes, password = load_certificate()
        if not pfx_bytes:
            print("ERROR: No certificate configured. Set CODESIGN_PFX_BASE64 and CODESIGN_PASSWORD.", file=sys.stderr)
            return 1

        tsa_url = get_tsa_url()
        if not tsa_url:
            print("WARNING: No timestamp server (CODESIGN_TSA_URL). Signature will not be timestamped.", file=sys.stderr)

        success = sign_exe(exe_path, signtool, pfx_bytes, password, tsa_url)
        if not success:
            return 1

        # Verify after signing
        print("\nVerifying signature...")
        verified, details = verify_exe(exe_path, signtool)
        if not verified:
            print("VERIFICATION FAILED:", file=sys.stderr)
            print(details, file=sys.stderr)
            return 1

        print("VERIFICATION PASSED")
        print(details)
        return 0

    elif args.action == "verify":
        verified, details = verify_exe(exe_path, signtool)
        if verified:
            print("VERIFICATION PASSED")
            print(details)
            return 0
        else:
            print("VERIFICATION FAILED", file=sys.stderr)
            print(details, file=sys.stderr)
            return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())