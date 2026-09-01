#!/usr/bin/env python3
"""
Admin License Management / Customer Operations — Phase 3.1 Tests

Covers:
- Customer CRUD (create / list / get detail)
- License issue (with custom params, machine_id)
- License download (signed payload, machine_id verification)
- Entitlement correctness (ENTERPRISE)
- Renew / change plan / deactivate machine / revoke
- Full E2E lifecycle
- Security: wrong machine, expired, revoked, deactivated, invalid plan,
  duplicate machine, unauthorized, malformed, tampered signature, private key leakage
- Audit events for all operations

Uses isolated in-memory SQLite. Does NOT touch production DB.
"""

import sys
import os
import json
import pytest
import pytest_asyncio
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJ_AI_OS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.license import signature as sig
from app.license.machine_id import MachineID
from app.license.license_manager import LicenseManager
from app.license.entitlements import EntitlementManager
from app.server.db.connection import reset_db, init_db, get_db_session, close_db
from app.server.db.models import User, License, MachineActivation, AuditLog
from app.server.services.admin_service import AdminService
from sqlalchemy import select
import asyncio


@pytest_asyncio.fixture(autouse=True)
async def isolated_db():
    """Reset + init isolated in-memory DB for each test."""
    await reset_db()
    await init_db()
    yield
    await close_db()


def _machine_id() -> str:
    return MachineID().generate()


# --- Test keypair fixture (ephemeral, vendor key'e dokunmaz) ---
def _make_test_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.generate()
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


_TEST_PRIVATE_PEM, _TEST_PUBLIC_PEM = _make_test_keypair()


@pytest.fixture(autouse=True)
def _patch_vendor_keys(monkeypatch: pytest.MonkeyPatch):
    """Patch vendor keys for admin license tests. Uses ephemeral test keypair."""
    monkeypatch.setattr(sig, "VENDOR_PUBLIC_KEY_PEM", _TEST_PUBLIC_PEM)
    # Also set env so has_signing_key() returns True and _load_private_key_pem works
    monkeypatch.setenv("DJ_AI_OS_LICENSE_PRIVATE_KEY", _TEST_PRIVATE_PEM)


async def _create_customer(session, email=None, name="Test Customer",
                            company="Test Co") -> str:
    if email is None:
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@test.local"
    service = AdminService(session)
    from app.server.admin_api import CreateCustomerRequest
    result = await service.create_customer(email=email, name=name, company_name=company)
    return result["id"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. CREATE CUSTOMER
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_customer():
    async with get_db_session() as session:
        email = "test.customer@test.local"
        cid = await _create_customer(session, email=email)
        assert cid is not None
        # Verify persisted with company_name
        result = await session.execute(select(User).where(User.id == cid))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.email == email
        assert user.company_name == "Test Co"
        assert user.is_admin is False
        assert user.is_active is True


async def test_create_customer_duplicate_email_fails():
    async with get_db_session() as session:
        await _create_customer(session, email="dup@test.local")
        with pytest.raises(Exception):
            await _create_customer(session, email="dup@test.local")


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIST CUSTOMERS
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_customers():
    async with get_db_session() as session:
        await _create_customer(session, email="c1@test.local", name="C1")
        await _create_customer(session, email="c2@test.local", name="C2")
        service = AdminService(session)
        customers = await service.list_customers()
        emails = [c["email"] for c in customers]
        assert "c1@test.local" in emails
        assert "c2@test.local" in emails


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET CUSTOMER DETAIL
# ─────────────────────────────────────────────────────────────────────────────

async def test_get_customer_detail():
    async with get_db_session() as session:
        email = "test.customer@test.local"
        cid = await _create_customer(session, email=email, company="DetailCo")
        service = AdminService(session)
        detail = await service.get_customer_detail(cid)
        assert detail["id"] == cid
        assert detail["email"] == email
        assert detail["company_name"] == "DetailCo"
        assert "created_at" in detail


async def test_get_customer_detail_not_found():
    async with get_db_session() as session:
        service = AdminService(session)
        detail = await service.get_customer_detail("nonexistent")
        assert detail is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. ISSUE LICENSE — ENTERPRISE
# ─────────────────────────────────────────────────────────────────────────────

async def test_issue_license_enterprise():
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(cid, "ENTERPRISE", 12, actor="admin")
        assert result["plan"] == "ENTERPRISE"
        assert result["key"].startswith("ENT-")
        detail = await service.get_license_detail(result["id"])
        assert detail["plan"] == "ENTERPRISE"
        assert detail["max_tracks"] == EntitlementManager.PLAN_FEATURES["ENTERPRISE"]["max_tracks"]


# ─────────────────────────────────────────────────────────────────────────────
# 5. ISSUE LICENSE WITH MACHINE_ID
# ─────────────────────────────────────────────────────────────────────────────

async def test_issue_license_with_machine_id():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "STUDIO", 12, machine_id=mid, actor="admin"
        )
        detail = await service.get_license_detail(result["id"])
        assert len(detail["machine_activations"]) == 1
        assert detail["machine_activations"][0]["machine_id"] == mid
        assert detail["machine_activations"][0]["is_active"] is True


async def test_issue_license_custom_expiry_and_max_tracks():
    future = (datetime.now(timezone.utc) + timedelta(days=180)).strftime("%Y-%m-%d")
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "PRO", 12, expiry=future, max_tracks=77777, actor="admin"
        )
        detail = await service.get_license_detail(result["id"])
        assert detail["max_tracks"] == 77777
        assert detail["expires_at"].startswith(future)


# ─────────────────────────────────────────────────────────────────────────────
# 6. LICENSE DOWNLOAD — SIGNED PAYLOAD
# ─────────────────────────────────────────────────────────────────────────────

async def test_download_license_returns_signed_payload():
    mid = _machine_id()
    async with get_db_session() as session:
        email = "test.customer@test.local"
        cid = await _create_customer(session, email=email)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        license_id = result["id"]
        # Simulate download endpoint payload generation
        payload = await service.generate_download_payload(license_id, mid)
        # Verify signature
        assert sig.verify(payload, payload["signature"], public_key_pem=sig.VENDOR_PUBLIC_KEY_PEM.encode())
        # Required fields
        assert payload["email"] == email
        assert payload["machine_id"] == mid
        assert payload["plan"] == "ENTERPRISE"
        assert "signature" in payload
        assert "nonce" in payload


async def test_download_license_machine_id_verification():
    """Downloaded license must be loadable by client LicenseManager."""
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        payload = await service.generate_download_payload(result["id"], mid)

    # Client-side validation
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        lic_file = f.name

    lm = LicenseManager()
    lm.license_file = lic_file
    lm.owner_dev_mode = False
    ok, reason = lm.is_valid()
    os.unlink(lic_file)
    assert ok and reason == "OK", f"Client rejected valid download: {reason}"


async def test_download_license_wrong_machine():
    """If license issued without machine_id, download uses placeholder → client must reject."""
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(cid, "ENTERPRISE", 12, actor="admin")
        # No machine_id → placeholder 0*64
        payload = await service.generate_download_payload(result["id"], "0" * 64)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        lic_file = f.name

    lm = LicenseManager()
    lm.license_file = lic_file
    lm.owner_dev_mode = False
    ok, reason = lm.is_valid()
    os.unlink(lic_file)
    assert not ok
    assert reason == "WRONG MACHINE"


# ─────────────────────────────────────────────────────────────────────────────
# 7. ENTITLEMENT CORRECTNESS
# ─────────────────────────────────────────────────────────────────────────────

async def test_enterprise_entitlements():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        payload = await service.generate_download_payload(result["id"], mid)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        lic_file = f.name

    lm = LicenseManager()
    lm.license_file = lic_file
    lm.owner_dev_mode = False
    plan = lm.get_plan()
    os.unlink(lic_file)

    assert plan["licensed"] is True
    assert plan["plan"] == "ENTERPRISE"
    ent = plan["entitlements"]
    assert ent["updates_active"] is True
    assert ent["server_ai"] is True
    assert ent["dj_archive_downloads"] is True
    assert ent["archive_repair"] is True
    assert ent["max_tracks"] == EntitlementManager.PLAN_FEATURES["ENTERPRISE"]["max_tracks"]


# ─────────────────────────────────────────────────────────────────────────────
# 8. RENEW LICENSE
# ─────────────────────────────────────────────────────────────────────────────

async def test_renew_license_updates_expiry_and_nonce():
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(cid, "PRO", 6, actor="admin")
        old = await service.get_license_detail(result["id"])
        renewed = await service.renew_license(result["id"], 12, actor="admin")
        new = await service.get_license_detail(result["id"])

        assert renewed is not None
        # Expiry extended
        assert new["expires_at"] > old["expires_at"]
        # Nonce rotated
        assert new["signature_nonce"] != old["signature_nonce"]
        # updates_until refreshed
        assert new["updates_until"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# 9. CHANGE LICENSE PLAN
# ─────────────────────────────────────────────────────────────────────────────

async def test_change_plan_updates_max_tracks_and_nonce():
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(cid, "PRO", 12, actor="admin")
        old = await service.get_license_detail(result["id"])

        changed = await service.change_license_plan(result["id"], "STUDIO", actor="admin")
        new = await service.get_license_detail(result["id"])

        assert changed["plan"] == "STUDIO"
        assert new["plan"] == "STUDIO"
        assert new["max_tracks"] == EntitlementManager.PLAN_FEATURES["STUDIO"]["max_tracks"]
        assert new["max_tracks"] != old["max_tracks"]
        assert new["signature_nonce"] != old["signature_nonce"]


async def test_change_plan_invalid_plan_rejected():
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(cid, "PRO", 12, actor="admin")
        with pytest.raises(ValueError):
            await service.change_license_plan(result["id"], "INVALID_PLAN", actor="admin")


# ─────────────────────────────────────────────────────────────────────────────
# 10. DEACTIVATE MACHINE
# ─────────────────────────────────────────────────────────────────────────────

async def test_deactivate_machine_sets_deactivated_at():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        license_id = result["id"]

        ok = await service.deactivate_machine(license_id, mid, actor="admin")
        assert ok

        detail = await service.get_license_detail(license_id)
        m = detail["machine_activations"][0]
        assert m["is_active"] is False
        assert m["deactivated_at"] is not None

        # License itself MUST remain active (deactivate ≠ revoke)
        assert detail["is_active"] is True
        assert detail["revoked_at"] is None


async def test_deactivate_machine_only_target():
    """Deactivating one machine must not affect other machines or the license.
    This test issues two licenses (same customer) with different machine_ids,
    then deactivates the machine on the first license only.
    """
    mid1 = _machine_id()
    mid2 = "a" * 64  # Different machine ID
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)

        # Issue first license with mid1
        result1 = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid1, actor="admin"
        )
        license_id = result1["id"]

        # Issue second license with mid2 (same customer, different license)
        result2 = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid2, actor="admin"
        )
        license_id2 = result2["id"]

        # Check machines before deactivate
        detail_before = await service.get_license_detail(license_id)
        print(f"License 1 - Before: {len(detail_before['machine_activations'])} machines")
        for m in detail_before['machine_activations']:
            print(f"  {m['machine_id'][:16]}... active={m['is_active']}")

        await service.deactivate_machine(license_id, mid1, actor="admin")
        detail = await service.get_license_detail(license_id)

        print(f"License 1 - After: {len(detail['machine_activations'])} machines")
        for m in detail['machine_activations']:
            print(f"  {m['machine_id'][:16]}... active={m['is_active']}")

        machines = {m["machine_id"]: m for m in detail["machine_activations"]}
        assert machines[mid1]["is_active"] is False
        assert detail["is_active"] is True  # license intact

        # Verify license 2 is unaffected
        detail2 = await service.get_license_detail(license_id2)
        machines2 = {m["machine_id"]: m for m in detail2["machine_activations"]}
        assert machines2[mid2]["is_active"] is True
        assert detail2["is_active"] is True


async def test_deactivate_machine_no_license_no_fail():
    async with get_db_session() as session:
        service = AdminService(session)
        ok = await service.deactivate_machine("nope", "0" * 64, actor="admin")
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# 11. REVOKE LICENSE
# ─────────────────────────────────────────────────────────────────────────────

async def test_revoke_license_sets_revoked_at():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        license_id = result["id"]

        ok = await service.revoke_license(license_id, actor="admin")
        assert ok

        detail = await service.get_license_detail(license_id)
        assert detail["is_active"] is False
        assert detail["revoked_at"] is not None

        # All machine activations deactivated
        for m in detail["machine_activations"]:
            assert m["is_active"] is False
            assert m["deactivated_at"] is not None


async def test_revoke_nonexistent_license():
    async with get_db_session() as session:
        service = AdminService(session)
        ok = await service.revoke_license("nonexistent", actor="admin")
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# 12. UNAUTHORIZED ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

async def test_unauthorized_admin_endpoint_returns_401():
    from fastapi.testclient import TestClient
    from app.server.run import app
    from app.server.deps import get_session

    # Override session dependency to use isolated in-memory DB
    async def _override_session():
        async with get_db_session() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    try:
        client = TestClient(app)
        resp = client.get("/admin/api/stats")  # no token
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 13. PRIVATE KEY NEVER LEAKS
# ─────────────────────────────────────────────────────────────────────────────

async def test_private_key_not_in_download_payload():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        payload = await service.generate_download_payload(result["id"], mid)

    payload_str = json.dumps(payload)
    assert "BEGIN PRIVATE KEY" not in payload_str
    assert "BEGIN EC PRIVATE KEY" not in payload_str
    assert "vendor_private_key" not in payload_str
    assert "DJ_AI_OS_LICENSE_PRIVATE_KEY" not in payload_str.upper()
    # Private key PEM is not a field
    assert "private_key" not in payload
    assert "privateKey" not in payload


async def test_private_key_not_in_customer_detail():
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        detail = await service.get_customer_detail(cid)
    detail_str = json.dumps(detail)
    assert "BEGIN PRIVATE KEY" not in detail_str
    assert "vendor_private_key" not in detail_str


async def test_private_key_not_in_audit_log():
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        await service.revoke_license(result["id"], actor="admin")

        logs = await service.list_audit_logs(limit=50)
        for log in logs:
            log_str = json.dumps(log)
            assert "BEGIN PRIVATE KEY" not in log_str
            assert "vendor_private_key" not in log_str


# ─────────────────────────────────────────────────────────────────────────────
# 14. AUDIT EVENTS
# ─────────────────────────────────────────────────────────────────────────────

async def test_audit_logs_capture_all_operations():
    mid = _machine_id()
    async with get_db_session() as session:
        service = AdminService(session)
        cid = await _create_customer(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        await service.renew_license(result["id"], 12, actor="admin")
        await service.change_license_plan(result["id"], "STUDIO", actor="admin")
        await service.deactivate_machine(result["id"], mid, actor="admin")
        await service.revoke_license(result["id"], actor="admin")

        logs = await service.list_audit_logs(limit=50)
        actions = [l["action"] for l in logs]
        assert "customer.created" in actions
        assert "license.issued" in actions
        assert "license.renewed" in actions
        assert "license.plan_changed" in actions
        assert "machine.deactivated" in actions
        assert "license.revoked" in actions


# ─────────────────────────────────────────────────────────────────────────────
# 15. FULL E2E LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

async def test_full_e2e_lifecycle():
    """
    CREATE CUSTOMER
    → ISSUE LICENSE
    → DOWNLOAD LICENSE
    → VERIFY SIGNATURE
    → VERIFY MACHINE ID
    → VERIFY ENTERPRISE ENTITLEMENTS
    → DEACTIVATE MACHINE
    → VERIFY MACHINE inactive
    → REVOKE LICENSE
    → VERIFY LICENSE inactive
    """
    mid = _machine_id()
    async with get_db_session() as session:
        service = AdminService(session)

        # CREATE CUSTOMER
        cid = await _create_customer(session)
        assert cid is not None

        # ISSUE LICENSE
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        license_id = result["id"]
        assert result["plan"] == "ENTERPRISE"

        # DOWNLOAD LICENSE
        payload = await service.generate_download_payload(license_id, mid)

        # VERIFY SIGNATURE
        assert sig.verify(payload, payload["signature"], public_key_pem=sig.VENDOR_PUBLIC_KEY_PEM.encode())

        # VERIFY MACHINE ID
        assert payload["machine_id"] == mid

        # VERIFY ENTERPRISE ENTITLEMENTS (client-side)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            lic_file = f.name
        try:
            lm = LicenseManager()
            lm.license_file = lic_file
            lm.owner_dev_mode = False
            ok, reason = lm.is_valid()
            assert ok and reason == "OK"
            plan = lm.get_plan()
            assert plan["licensed"] is True
            assert plan["plan"] == "ENTERPRISE"
            assert plan["entitlements"]["updates_active"] is True
        finally:
            os.unlink(lic_file)

        # DEACTIVATE MACHINE
        ok = await service.deactivate_machine(license_id, mid, actor="admin")
        assert ok

        # VERIFY MACHINE inactive
        detail = await service.get_license_detail(license_id)
        m = detail["machine_activations"][0]
        assert m["is_active"] is False
        assert m["deactivated_at"] is not None
        # License still active
        assert detail["is_active"] is True

        # REVOKE LICENSE
        ok = await service.revoke_license(license_id, actor="admin")
        assert ok

        # VERIFY LICENSE inactive
        detail = await service.get_license_detail(license_id)
        assert detail["is_active"] is False
        assert detail["revoked_at"] is not None
        for mach in detail["machine_activations"]:
            assert mach["is_active"] is False


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY TESTS — negative paths
# ─────────────────────────────────────────────────────────────────────────────

async def test_security_expired_license_rejected():
    """A downloaded license past expiry must fail client validation."""
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        payload = await service.generate_download_payload(result["id"], mid)
        # Force expiry in past
        payload["expiry"] = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        # Re-sign with valid key (simulating tamper of date only — signature still valid)
        payload["signature"] = sig.sign(payload)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        lic_file = f.name
    try:
        lm = LicenseManager()
        lm.license_file = lic_file
        lm.owner_dev_mode = False
        ok, reason = lm.is_valid()
        assert not ok
        assert reason == "EXPIRED"
    finally:
        os.unlink(lic_file)


async def test_security_tampered_signature_rejected():
    """Modified payload without re-signing → INVALID SIGNATURE."""
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "PRO", 12, machine_id=mid, actor="admin"
        )
        payload = await service.generate_download_payload(result["id"], mid)
        # Tamper: bump plan, keep old signature
        payload["plan"] = "ENTERPRISE"
        payload["max_tracks"] = 0

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        lic_file = f.name
    try:
        lm = LicenseManager()
        lm.license_file = lic_file
        lm.owner_dev_mode = False
        ok, reason = lm.is_valid()
        assert not ok
        assert reason == "INVALID SIGNATURE"
    finally:
        os.unlink(lic_file)


async def test_security_malformed_license_rejected():
    """Missing required fields → INVALID STRUCTURE."""
    async with get_db_session() as session:
        pass  # no DB needed

    bad = {"email": "x@y.z", "plan": "PRO"}  # missing machine_id, signature, etc.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(bad, f)
        lic_file = f.name
    try:
        lm = LicenseManager()
        lm.license_file = lic_file
        lm.owner_dev_mode = False
        ok, reason = lm.is_valid()
        assert not ok
        assert reason in ("INVALID STRUCTURE", "INVALID SIGNATURE")
    finally:
        os.unlink(lic_file)


async def test_security_revoked_license_server_side():
    """After revoke, server-side detail shows inactive (client file unchanged)."""
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        result = await service.issue_license(
            cid, "ENTERPRISE", 12, machine_id=mid, actor="admin"
        )
        license_id = result["id"]
        await service.revoke_license(license_id, actor="admin")
        detail = await service.get_license_detail(license_id)
        assert detail["is_active"] is False
        # Server-side enforcement: if we checked activation, it would be denied
        active_machines = [m for m in detail["machine_activations"] if m["is_active"]]
        assert len(active_machines) == 0


async def test_security_duplicate_machine_activation_rejected():
    """Issuing license with same machine_id twice → second activation not duplicated."""
    mid = _machine_id()
    async with get_db_session() as session:
        cid = await _create_customer(session)
        service = AdminService(session)
        r1 = await service.issue_license(
            cid, "PRO", 12, machine_id=mid, actor="admin"
        )
        # Second license same machine — should not create duplicate activation row
        r2 = await service.issue_license(
            cid, "PRO", 12, machine_id=mid, actor="admin"
        )
        d1 = await service.get_license_detail(r1["id"])
        d2 = await service.get_license_detail(r2["id"])
        # Each license has exactly one activation for this machine
        assert len(d1["machine_activations"]) == 1
        assert len(d2["machine_activations"]) == 1
        assert d1["machine_activations"][0]["machine_id"] == mid
        assert d2["machine_activations"][0]["machine_id"] == mid
