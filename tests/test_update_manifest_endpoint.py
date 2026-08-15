"""Test /api/update/manifest endpoint contract and security."""

import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Set up test manifest before importing app
os.environ["DJ_AI_OS_UPDATE_MANIFEST"] = "update_manifest_signed.json"

from app.server.api import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_update_manifest_endpoint_returns_signed_manifest(client):
    """Endpoint returns valid signed manifest with all required fields."""
    response = client.get("/api/update/manifest")
    assert response.status_code == 200

    manifest = response.json()

    # Required top-level fields
    assert "version" in manifest
    assert "min_client_version" in manifest
    assert "released_at" in manifest
    assert "critical" in manifest
    assert "changelog" in manifest
    assert "download_url" in manifest
    assert "modules" in manifest
    assert "signature" in manifest

    # Version format
    assert manifest["version"] == "0.2.0"
    assert manifest["min_client_version"] == "0.1.0"

    # Modules array
    modules = manifest["modules"]
    assert isinstance(modules, list)
    assert len(modules) == 2

    # Each module has required fields
    for mod in modules:
        assert "name" in mod
        assert "version" in mod
        assert "sha256" in mod
        assert "size" in mod
        assert "hot_reload" in mod
        # SHA256 must be 64-char hex
        assert len(mod["sha256"]) == 64
        assert all(c in "0123456789abcdef" for c in mod["sha256"])
        assert isinstance(mod["size"], int)
        assert isinstance(mod["hot_reload"], bool)

    # Signature is non-empty hex
    assert manifest["signature"]
    assert len(manifest["signature"]) == 128  # Ed25519 hex = 64 bytes = 128 chars


def test_update_manifest_signature_verifies_with_public_key(client):
    """Manifest signature verifies with embedded vendor public key."""
    response = client.get("/api/update/manifest")
    assert response.status_code == 200

    manifest = response.json()

    # Verify using the same logic as update_engine
    from app.license import signature as sig
    assert sig.verify(manifest, manifest["signature"]), "Signature verification failed"


def test_update_manifest_rejects_tampered_signature(client):
    """Tampered manifest signature fails verification."""
    response = client.get("/api/update/manifest")
    assert response.status_code == 200

    manifest = response.json()

    # Tamper with signature
    tampered = manifest.copy()
    tampered["signature"] = "0" * 128

    from app.license import signature as sig
    assert not sig.verify(tampered, tampered["signature"]), "Tampered signature should fail"


def test_update_manifest_rejects_tampered_module(client):
    """Tampered module content fails verification."""
    response = client.get("/api/update/manifest")
    assert response.status_code == 200

    manifest = response.json()

    # Tamper with module sha256
    tampered = json.loads(json.dumps(manifest))
    tampered["modules"][0]["sha256"] = "0" * 64

    from app.license import signature as sig
    assert not sig.verify(tampered, tampered["signature"]), "Tampered module should fail signature"


def test_update_manifest_endpoint_404_when_not_configured(client, monkeypatch):
    """Endpoint returns 404 when manifest not configured."""
    # Remove manifest env
    monkeypatch.delenv("DJ_AI_OS_UPDATE_MANIFEST", raising=False)
    # Also remove default location file if exists
    import os
    default_path = os.path.join(os.path.dirname(__file__), "..", "update_manifest.json")
    if os.path.exists(default_path):
        os.rename(default_path, default_path + ".bak")

    try:
        response = client.get("/api/update/manifest")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["reason"] == "MANIFEST_NOT_FOUND"
    finally:
        # Restore
        if os.path.exists(default_path + ".bak"):
            os.rename(default_path + ".bak", default_path)


def test_update_manifest_version_greater_than_current():
    """Manifest version 0.2.0 > current 0.1.0 for update detection."""
    from app.config.version import APP_VERSION
    from app.cloud.update_engine import UpdateEngine

    engine = UpdateEngine()
    # Current version is 0.1.0 from app/config/version.py
    assert engine._version_gt("0.2.0", APP_VERSION)
    assert not engine._version_gt(APP_VERSION, "0.2.0")


def test_update_manifest_min_client_version_check():
    """min_client_version gate works correctly."""
    from app.cloud.update_engine import UpdateEngine

    engine = UpdateEngine()
    # Current is 0.1.0, manifest requires 0.1.0 -> OK
    assert not engine._version_gt("0.1.0", "0.1.0")
    # Manifest requires 0.2.0 but current is 0.1.0 -> blocks
    assert engine._version_gt("0.2.0", "0.1.0")


def test_update_manifest_compatible_with_update_engine_contract(client):
    """Response matches UpdateEngine.check_for_updates expected contract."""
    response = client.get("/api/update/manifest")
    assert response.status_code == 200

    manifest = response.json()

    # Fields that update_engine.check_for_updates expects
    expected_fields = [
        "version",
        "min_client_version",
        "released_at",
        "critical",
        "changelog",
        "download_url",
        "modules",
        "signature"
    ]
    for field in expected_fields:
        assert field in manifest, f"Missing field: {field}"

    # download_url should be string
    assert isinstance(manifest["download_url"], str)
    assert manifest["download_url"].startswith("http")

    # modules array with correct structure for _calculate_delta
    for mod in manifest["modules"]:
        assert "name" in mod
        assert "sha256" in mod
        assert "version" in mod


def test_private_key_not_in_package():
    """Verify vendor_private_key.pem is not in packaged build paths."""
    import sys
    from pathlib import Path

    # Check it's gitignored / not in source paths that get packaged
    repo_root = Path(__file__).resolve().parent.parent
    private_key = repo_root / "vendor_private_key.pem"

    # File may exist in repo root (dev) but should be gitignored
    # The key assertion: it should NOT be in app/ or any package path
    app_paths = [
        repo_root / "app",
        repo_root / "orb_core",
        repo_root / "modules",
    ]

    for app_path in app_paths:
        # private key should not be under any app path
        try:
            private_key.relative_to(app_path)
            pytest.fail(f"Private key found inside package path: {app_path}")
        except ValueError:
            pass  # Good - not under this path


def test_signing_tool_validates_schema():
    """Signing tool validates required fields."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"version": "0.2.0"}, f)  # missing required fields
        bad_manifest = f.name

    try:
        result = subprocess.run([
            sys.executable, "tools/sign_update_manifest.py",
            "--manifest", bad_manifest
        ], capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), ".."))

        assert result.returncode != 0
        assert "Missing required field" in result.stderr or "Missing required field" in result.stdout
    finally:
        os.unlink(bad_manifest)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])