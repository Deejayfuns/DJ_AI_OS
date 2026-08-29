"""Tests for tools/ci/sign_exe.py - Windows Authenticode signing helper."""

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
SIGN_HELPER = PROJECT_ROOT / "tools" / "ci" / "sign_exe.py"


def _signtool_available():
    """Check if signtool.exe is available on this system."""
    if platform.system() != "Windows":
        return False
    import shutil
    return shutil.which("signtool.exe") is not None


@pytest.mark.skipif(platform.system() != "Windows", reason="Authenticode signing is Windows-only")
class TestSignExeWindows:
    """Tests that require Windows and signtool.exe."""

    def test_signtool_available(self):
        """Verify signtool.exe can be found on Windows."""
        # This test just checks the helper can locate signtool
        # The actual find_signtool is internal, so we test via subprocess
        result = subprocess.run([
            sys.executable, str(SIGN_HELPER), "verify",
            str(SIGN_HELPER)  # Use self as dummy EXE
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)

        # Should fail because signtool is not signing a real EXE, but should not crash
        # Exit code 1 = verification failed (expected for non-EXE)
        # Exit code 2 = platform error (should not happen on Windows)
        assert result.returncode in (1, 2)

    @pytest.mark.skipif(not _signtool_available(), reason="signtool.exe not installed")
    def test_sign_missing_exe(self):
        """Signing missing EXE should fail clearly."""
        result = subprocess.run([
            sys.executable, str(SIGN_HELPER), "sign",
            "nonexistent.exe"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT, env={
            **os.environ,
            "CODESIGN_PFX_BASE64": "invalid",
            "CODESIGN_PASSWORD": "test"
        })

        assert result.returncode == 1
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower()

    @pytest.mark.skipif(not _signtool_available(), reason="signtool.exe not installed")
    def test_sign_without_certificate(self):
        """Signing without certificate config should fail clearly."""
        # Create a dummy EXE
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ")  # Minimal EXE header
            dummy_exe = f.name

        try:
            result = subprocess.run([
                sys.executable, str(SIGN_HELPER), "sign", dummy_exe
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)

            assert result.returncode == 1
            assert "certificate" in result.stderr.lower() or "certificate" in result.stdout.lower()
        finally:
            Path(dummy_exe).unlink(missing_ok=True)

    @pytest.mark.skipif(not _signtool_available(), reason="signtool.exe not installed")
    def test_sign_with_invalid_base64(self):
        """Invalid base64 certificate should fail clearly."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ")
            dummy_exe = f.name

        try:
            result = subprocess.run([
                sys.executable, str(SIGN_HELPER), "sign", dummy_exe
            ], capture_output=True, text=True, cwd=PROJECT_ROOT, env={
                **os.environ,
                "CODESIGN_PFX_BASE64": "not-valid-base64!!!",
                "CODESIGN_PASSWORD": "test"
            })

            assert result.returncode == 1
            assert "decode" in result.stderr.lower() or "decode" in result.stdout.lower()
        finally:
            Path(dummy_exe).unlink(missing_ok=True)

    @pytest.mark.skipif(not _signtool_available(), reason="signtool.exe not installed")
    def test_verify_unsigned_exe(self):
        """Verifying an unsigned EXE should fail."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ")
            dummy_exe = f.name

        try:
            result = subprocess.run([
                sys.executable, str(SIGN_HELPER), "verify", dummy_exe
            ], capture_output=True, text=True, cwd=PROJECT_ROOT)

            # Should fail verification (unsigned)
            assert result.returncode == 1
            # Output should mention no signature or verification failed
            output = (result.stdout + result.stderr).lower()
            assert "not signed" in output or "no signature" in output or "failed" in output
        finally:
            Path(dummy_exe).unlink(missing_ok=True)


class TestSignExeCrossPlatform:
    """Tests that work on any platform."""

    def test_help_output(self):
        """Help should display without error."""
        result = subprocess.run([
            sys.executable, str(SIGN_HELPER), "--help"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)

        assert result.returncode == 0
        assert "sign" in result.stdout
        assert "verify" in result.stdout
        assert "CODESIGN_PFX_BASE64" in result.stdout

    def test_invalid_action(self):
        """Invalid action should fail."""
        result = subprocess.run([
            sys.executable, str(SIGN_HELPER), "invalid_action", "test.exe"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)

        assert result.returncode != 0
        assert "invalid" in (result.stdout + result.stderr).lower() or "usage" in (result.stdout + result.stderr).lower()

    def test_missing_exe_path(self):
        """Missing EXE path argument should fail."""
        result = subprocess.run([
            sys.executable, str(SIGN_HELPER), "sign"
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)

        assert result.returncode != 0

    @pytest.mark.skipif(platform.system() == "Windows", reason="Non-Windows behavior test")
    def test_non_windows_rejection(self):
        """Non-Windows should reject signing."""
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ")
            dummy_exe = f.name

        try:
            result = subprocess.run([
                sys.executable, str(SIGN_HELPER), "sign", dummy_exe
            ], capture_output=True, text=True, cwd=PROJECT_ROOT, env={
                **os.environ,
                "CODESIGN_PFX_BASE64": "dummy",
                "CODESIGN_PASSWORD": "test"
            })

            assert result.returncode == 2
            assert "windows" in result.stderr.lower()
        finally:
            Path(dummy_exe).unlink(missing_ok=True)

    def test_sign_exe_imports(self):
        """Verify sign_exe.py can be imported without errors (syntax check)."""
        # This ensures no import-time errors
        import importlib.util
        spec = importlib.util.spec_from_file_location("sign_exe", SIGN_HELPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check key functions exist
        assert hasattr(module, "find_signtool")
        assert hasattr(module, "load_certificate")
        assert hasattr(module, "sign_exe")
        assert hasattr(module, "verify_exe")
        assert hasattr(module, "main")


class TestSignExeCommandConstruction:
    """Test command line construction logic (unit-style, no subprocess)."""

    def test_find_signtool_prefers_explicit(self):
        """Explicit path should be preferred."""
        from tools.ci.sign_exe import find_signtool

        # Non-existent explicit path returns None
        result = find_signtool(r"C:\nonexistent\signtool.exe")
        assert result is None

    def test_load_certificate_missing_env(self):
        """Missing env vars returns (None, None)."""
        from tools.ci.sign_exe import load_certificate

        # Clear env
        old_pfx = os.environ.pop("CODESIGN_PFX_BASE64", None)
        old_pwd = os.environ.pop("CODESIGN_PASSWORD", None)

        try:
            pfx, pwd = load_certificate()
            assert pfx is None
            assert pwd is None
        finally:
            if old_pfx:
                os.environ["CODESIGN_PFX_BASE64"] = old_pfx
            if old_pwd:
                os.environ["CODESIGN_PASSWORD"] = old_pwd

    def test_load_certificate_valid_base64(self):
        """Valid base64 returns decoded bytes."""
        from tools.ci.sign_exe import load_certificate

        test_data = b"test certificate data"
        b64 = __import__("base64").b64encode(test_data).decode()

        old_pfx = os.environ.pop("CODESIGN_PFX_BASE64", None)
        old_pwd = os.environ.pop("CODESIGN_PASSWORD", None)

        try:
            os.environ["CODESIGN_PFX_BASE64"] = b64
            os.environ["CODESIGN_PASSWORD"] = "testpass"

            pfx, pwd = load_certificate()
            assert pfx == test_data
            assert pwd == "testpass"
        finally:
            if old_pfx:
                os.environ["CODESIGN_PFX_BASE64"] = old_pfx
            else:
                os.environ.pop("CODESIGN_PFX_BASE64", None)
            if old_pwd:
                os.environ["CODESIGN_PASSWORD"] = old_pwd
            else:
                os.environ.pop("CODESIGN_PASSWORD", None)

    def test_load_certificate_invalid_base64(self):
        """Invalid base64 returns (None, None) and logs error."""
        from tools.ci.sign_exe import load_certificate

        old_pfx = os.environ.pop("CODESIGN_PFX_BASE64", None)
        old_pwd = os.environ.pop("CODESIGN_PASSWORD", None)

        try:
            os.environ["CODESIGN_PFX_BASE64"] = "invalid!!!"
            os.environ["CODESIGN_PASSWORD"] = "test"

            pfx, pwd = load_certificate()
            assert pfx is None
            assert pwd is None
        finally:
            if old_pfx:
                os.environ["CODESIGN_PFX_BASE64"] = old_pfx
            else:
                os.environ.pop("CODESIGN_PFX_BASE64", None)
            if old_pwd:
                os.environ["CODESIGN_PASSWORD"] = old_pwd
            else:
                os.environ.pop("CODESIGN_PASSWORD", None)

    def test_get_tsa_url(self):
        """TSA URL from environment."""
        from tools.ci.sign_exe import get_tsa_url

        old_tsa = os.environ.pop("CODESIGN_TSA_URL", None)

        try:
            assert get_tsa_url() is None

            os.environ["CODESIGN_TSA_URL"] = "http://timestamp.digicert.com"
            assert get_tsa_url() == "http://timestamp.digicert.com"
        finally:
            if old_tsa:
                os.environ["CODESIGN_TSA_URL"] = old_tsa
            else:
                os.environ.pop("CODESIGN_TSA_URL", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])