"""End-to-end update chain test: real FastAPI server → engine download → verify → apply."""
import os
import json
import hashlib
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Set manifest before importing app
os.environ["DJ_AI_OS_UPDATE_MANIFEST"] = "update_manifest_signed.json"
os.environ["DJ_AI_OS_UPDATE_ARTIFACTS"] = "dist/update_artifacts"

from app.server.api import create_app
from app.cloud.update_engine import UpdateEngine
from app.license import signature as sig
from app.config.version import APP_VERSION


MODULE_A = "app/config/version.py"
MODULE_B = "app/cloud/update_engine.py"


@pytest.fixture(scope="module")
def test_keys():
    """Generate test Ed25519 key pair."""
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


@pytest.fixture(scope="module")
def test_artifacts_dir(tmp_path_factory):
    """Create a temporary artifacts dir with test module files."""
    artifacts_dir = tmp_path_factory.mktemp("artifacts")

    # Module A content
    content_a = b'APP_VERSION = "0.2.0"\n'
    mod_a = artifacts_dir / MODULE_A
    mod_a.parent.mkdir(parents=True)
    mod_a.write_bytes(content_a)

    # Module B content
    content_b = b"# test update_engine v0.2.0\n"
    mod_b = artifacts_dir / MODULE_B
    mod_b.parent.mkdir(parents=True)
    mod_b.write_bytes(content_b)

    return artifacts_dir, content_a, content_b


@pytest.fixture(scope="module")
def test_manifest(test_keys, test_artifacts_dir):
    """Create a signed manifest pointing to test artifacts."""
    private_pem, public_pem = test_keys
    artifacts_dir, content_a, content_b = test_artifacts_dir

    manifest = {
        "version": "0.2.0",
        "min_client_version": APP_VERSION,
        "released_at": "2026-08-14T00:00:00Z",
        "critical": False,
        "changelog": "E2E test manifest",
        "download_url": "http://testserver/api/update",  # TestClient base
        "modules": [
            {
                "name": MODULE_A,
                "version": "0.2.0",
                "sha256": hashlib.sha256(content_a).hexdigest(),
                "size": len(content_a),
                "hot_reload": False,
            },
            {
                "name": MODULE_B,
                "version": "0.2.0",
                "sha256": hashlib.sha256(content_b).hexdigest(),
                "size": len(content_b),
                "hot_reload": False,
            },
        ],
    }
    manifest["signature"] = sig.sign(manifest, private_key_pem=private_pem)
    return manifest, public_pem


@pytest.fixture(scope="module")
def test_server(test_manifest, test_artifacts_dir, test_keys, tmp_path_factory):
    """Spin up a real FastAPI TestClient with test manifest + artifacts path."""
    manifest, public_pem = test_manifest
    artifacts_dir, _, _ = test_artifacts_dir
    private_pem, _ = test_keys

    # Override vendor public key for verification
    original_pub = sig.VENDOR_PUBLIC_KEY_PEM
    sig.VENDOR_PUBLIC_KEY_PEM = public_pem

    # Write test manifest to a temp file and point server at it
    manifest_file = tmp_path_factory.mktemp("manifest") / "update_manifest_signed.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    original_manifest_env = os.environ.get("DJ_AI_OS_UPDATE_MANIFEST")
    os.environ["DJ_AI_OS_UPDATE_MANIFEST"] = str(manifest_file)

    app = create_app()
    client = TestClient(app)

    # Patch artifacts root for the module endpoint
    original_artifacts_env = os.environ.get("DJ_AI_OS_UPDATE_ARTIFACTS")
    os.environ["DJ_AI_OS_UPDATE_ARTIFACTS"] = str(artifacts_dir)

    yield client, manifest

    # Cleanup
    sig.VENDOR_PUBLIC_KEY_PEM = original_pub
    if original_manifest_env is not None:
        os.environ["DJ_AI_OS_UPDATE_MANIFEST"] = original_manifest_env
    else:
        os.environ.pop("DJ_AI_OS_UPDATE_MANIFEST", None)
    if original_artifacts_env is not None:
        os.environ["DJ_AI_OS_UPDATE_ARTIFACTS"] = original_artifacts_env
    else:
        os.environ.pop("DJ_AI_OS_UPDATE_ARTIFACTS", None)

    # Explicitly close the TestClient to dispose its event-loop-bound portal
    try:
        client.close()
    except Exception:
        pass


def _make_engine(tmp_path):
    """Create UpdateEngine with a fake app_root containing old module versions."""
    app_root = tmp_path / "app_root"
    app_root.mkdir()

    # Old versions
    (app_root / MODULE_A).parent.mkdir(parents=True)
    (app_root / MODULE_A).write_text('APP_VERSION = "0.1.0"\n', encoding="utf-8")

    (app_root / MODULE_B).parent.mkdir(parents=True)
    (app_root / MODULE_B).write_text("# old update_engine v0.1.0\n", encoding="utf-8")

    update_dir = tmp_path / "updates"
    return UpdateEngine(app_root=str(app_root), update_dir=str(update_dir))


def test_e2e_server_manifest_to_apply(tmp_path, test_server, test_keys):
    """
    Full chain:
    1. Client calls GET /api/update/manifest (via TestClient)
    2. Engine verifies signature with embedded public key
    3. Engine downloads each module via GET /api/update/modules/<path>
    4. Engine verifies SHA256 of each downloaded artifact
    5. Engine applies update via atomic swap
    """
    client, server_manifest = test_server
    private_pem, public_pem = test_keys
    engine = _make_engine(tmp_path)

    # Patch engine's network methods to route through TestClient
    # (TestClient is not a real server, so urllib would fail)
    def fetch_manifest_via_client(base_url=None, offline_dir=None):
        resp = client.get("/api/update/manifest")
        if resp.status_code != 200:
            return None
        return resp.json()

    def fetch_module_via_client(base, name, dst):
        # Convert <base>/modules/<name> → /api/update/modules/<name>
        path = f"/api/update/modules/{name}"
        resp = client.get(path)
        if resp.status_code != 200:
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(resp.content)
        return True

    original_fetch = engine._fetch_manifest
    original_module = engine._fetch_module
    engine._fetch_manifest = fetch_manifest_via_client
    engine._fetch_module = fetch_module_via_client

    try:
        # 1. CHECK FOR UPDATES
        result = engine.check_for_updates({"entitlements": {"updates_active": True}})

        assert result["available"] is True, f"Update should be available: {result}"
        assert result["latest"] == "0.2.0"
        assert result["current"] == APP_VERSION
        assert "manifest" in result
        assert len(result["manifest"]["modules"]) == 2

        manifest = result["manifest"]

        # 2. APPLY UPDATE (downloads modules via server endpoint)
        res = engine.apply_update(manifest, user_approved=True)

        assert res["ok"] is True, f"Apply failed: {res}"
        assert res["hot_swapped"] == 2
        assert res["needs_restart"] is True

        # 3. VERIFY FILES SWAPPED CORRECTLY
        app_root = tmp_path / "app_root"

        new_a = (app_root / MODULE_A).read_text(encoding="utf-8")
        assert 'APP_VERSION = "0.2.0"' in new_a, f"Module A not updated: {new_a}"

        new_b = (app_root / MODULE_B).read_text(encoding="utf-8")
        assert "test update_engine v0.2.0" in new_b, f"Module B not updated: {new_b}"

        # 4. VERIFY LOCAL MANIFEST SAVED
        local_manifest_path = Path(engine.update_dir) / "manifest.json"
        assert local_manifest_path.exists()
        local_manifest = json.loads(local_manifest_path.read_text(encoding="utf-8"))
        assert local_manifest["version"] == "0.2.0"
        assert local_manifest["signature"] == manifest["signature"]

    finally:
        engine._fetch_manifest = original_fetch
        engine._fetch_module = original_module


def test_e2e_module_endpoint_directly(test_server, test_artifacts_dir):
    """Verify the module artifact endpoint serves correct content."""
    client, _ = test_server
    artifacts_dir, content_a, content_b = test_artifacts_dir

    # Fetch module A
    resp = client.get(f"/api/update/modules/{MODULE_A}")
    assert resp.status_code == 200
    assert resp.content == content_a
    assert resp.headers["content-type"] == "application/octet-stream"

    # Fetch module B
    resp = client.get(f"/api/update/modules/{MODULE_B}")
    assert resp.status_code == 200
    assert resp.content == content_b


def test_e2e_module_endpoint_path_traversal_blocked(test_server):
    """Path traversal attempts must be rejected (400 or 404 both safe)."""
    client, _ = test_server

    # Directory traversal - Starlette normalizes path before routing → 404 is acceptable
    resp = client.get("/api/update/modules/../../etc/passwd")
    assert resp.status_code in (400, 404)

    # Absolute path attempt
    resp = client.get("/api/update/modules/C:/Windows/System32")
    assert resp.status_code in (400, 404)


def test_e2e_module_endpoint_404_missing(test_server):
    """Non-existent module returns 404."""
    client, _ = test_server

    resp = client.get("/api/update/modules/nonexistent/file.py")
    assert resp.status_code == 404
    assert resp.json()["detail"]["reason"] == "MODULE_NOT_FOUND"


def test_e2e_bad_signature_rejected(tmp_path, test_server, test_keys):
    """Manifest with tampered signature must be rejected."""
    client, server_manifest = test_server
    private_pem, public_pem = test_keys
    engine = _make_engine(tmp_path)

    # Tamper with the manifest signature
    bad_manifest = json.loads(json.dumps(server_manifest))
    bad_manifest["signature"] = "0" * 128

    # Direct apply with bad signature (bypasses check_for_updates)
    res = engine.apply_update(bad_manifest, user_approved=True)

    assert res["ok"] is False
    assert res["reason"] == "manifest_bad_signature"


def test_e2e_tampered_module_rejected(tmp_path, test_server, test_keys):
    """Manifest with tampered module SHA256 must be rejected at apply time."""
    client, server_manifest = test_server
    private_pem, public_pem = test_keys
    engine = _make_engine(tmp_path)

    # Patch network methods (same as apply test)
    def fetch_manifest_via_client(base_url=None, offline_dir=None):
        return server_manifest

    def fetch_module_via_client(base, name, dst):
        # Serve WRONG content (tampered) to force checksum fail
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"TAMPERED CONTENT\ndoes not match sha256\n")
        return True

    original_fetch = engine._fetch_manifest
    original_module = engine._fetch_module
    engine._fetch_manifest = fetch_manifest_via_client
    engine._fetch_module = fetch_module_via_client

    try:
        # Tamper module SHA256 but keep signature valid (sign with test key)
        bad_manifest = json.loads(json.dumps(server_manifest))
        bad_manifest["modules"][0]["sha256"] = "0" * 64
        bad_manifest["signature"] = sig.sign(bad_manifest, private_key_pem=private_pem)

        res = engine.apply_update(bad_manifest, user_approved=True)

        assert res["ok"] is False
        assert res["reason"] == "checksum_failed"

        # Original files preserved (rollback)
        app_root = tmp_path / "app_root"
        assert 'APP_VERSION = "0.1.0"' in (app_root / MODULE_A).read_text(encoding="utf-8")
    finally:
        engine._fetch_manifest = original_fetch
        engine._fetch_module = original_module


if __name__ == "__main__":
    pytest.main([__file__, "-v"])