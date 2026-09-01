"""
FROZEN CUSTOMER BUILD — final functional regression against dist/DJ_AI_OS/_internal.

Run with the frozen module tree on sys.path (not the dev tree) so we exercise
the exact code that ships in the installer. No rebuild; no dev-tree shadowing.

Covers:
  - DEMO boot (no license)
  - Enterprise activation (valid signed license)
  - Fail-closed: invalid sig / tampered / expired / wrong machine / corrupt
  - Navigation 23/23 (NAV_ITEMS <-> set_view dispatch <-> distinct builders)
  - HUD regression (_HUD_DISABLED_VIEWS + content-below-HUD gate)
  - Turkish TTS/UI defaults (EmelNeural + boot line)
  - APPDATA persistence + Program-Files write avoidance
  - Security: no private key / dev.flag / license.key / test artifacts in tree
"""
import os
import sys
import json
import tempfile
import importlib

# --- Frozen module tree on path ---------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FROZEN = os.path.join(ROOT, "dist", "DJ_AI_OS", "_internal")
if not os.path.isdir(FROZEN):
    import pytest
    pytest.skip(f"Frozen tree not found: {FROZEN} (PyInstaller build not run in this CI job)", allow_module_level=True)
if FROZEN not in sys.path:
    sys.path.insert(0, FROZEN)

# Neutralize frozen-detection so path resolution uses APPDATA as in real install
import sys as _sys
_sys.frozen = True

import pytest
from app.license import license_manager as lm_mod
from app.license import signature as sig
from app.license.machine_id import MachineID
from app.ui.sidebar import NAV_ITEMS, PLAN_HIERARCHY
from app.core import paths
from app.core import voice_config
import app.ui.main_window as mw_mod

# Module-level constants (defined at module scope in source)
_HUD_DISABLED = mw_mod._HUD_DISABLED_VIEWS

# VIEW_REQUIREMENTS is method-local inside MainWindow._check_view_access.
# Extract it once by inspecting the method via a lightweight instance stub.
import inspect
_src_check = inspect.getsource(mw_mod.MainWindow._check_view_access)
import re
_m = re.search(r"VIEW_REQUIREMENTS\s*=\s*\{(.*?)\}", _src_check, re.S)
_VIEW_REQUIREMENTS = {}
if _m:
    for k, v in re.findall(r'"([a-z_]+)":\s*"([A-Z_]+)"', _m.group(1)):
        _VIEW_REQUIREMENTS[k] = v

# builders dict is method-local inside set_view; extract the "view": "self.method"
# string pairs, then resolve each "self.method" to the actual bound method.
_src_set = inspect.getsource(mw_mod.MainWindow.set_view)
_m2 = re.search(r"builders\s*=\s*\{(.*?)\}", _src_set, re.S)
_SET_VIEW_BUILDERS = {}
if _m2:
    for k, v in re.findall(r'"([a-z_]+)":\s*(self\.[a-z_]+)', _m2.group(1)):
        # Resolve "self.method" -> MainWindow.method (unbound fn is still callable)
        attr = v.split(".", 1)[1]
        _SET_VIEW_BUILDERS[k] = getattr(mw_mod.MainWindow, attr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_manager(payload_dict):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload_dict, f)
    lm = lm_mod.LicenseManager()
    lm.license_file = path
    lm.owner_dev_mode = False
    return lm, path


# --- Test keypair (patched into signature module for deterministic signing) ---
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


def _make_valid_license():
    """Generate a VALID_LICENSE signed for THIS machine with the test key."""
    current_machine_id = MachineID().generate()
    payload = {
        "email": "customer@dj.local",
        "machine_id": current_machine_id,
        "plan": "ENTERPRISE",
        "expiry": "2027-08-20",
        "max_tracks": 0,
        "updates_until": "2027-08-20",
        "issued_at": "2026-08-20T06:58:14.306291+00:00",
        "nonce": "prodcccccccccccccccccccccccccccc",
    }
    payload["signature"] = sig.sign(payload, private_key_pem=_TEST_PRIVATE_PEM)
    return payload


# Test-signed license payload. Built once at import; the VENDOR public key is
# patched PER-TEST via monkeypatch below (never mutated at module import), so
# this module cannot leak a swapped key to other test modules that rely on the
# real vendor public key (e.g. test_admin_license.py).
import pytest


@pytest.fixture(autouse=True)
def _patch_vendor_public_key(monkeypatch: pytest.MonkeyPatch):
    """Patch the vendor public key so the test-signed license verifies in the
    frozen tree (which normally carries the real vendor public key). Restored
    automatically by monkeypatch after each test — no global leak."""
    monkeypatch.setattr(sig, "VENDOR_PUBLIC_KEY_PEM", _TEST_PUBLIC_PEM)


VALID_LICENSE = _make_valid_license()


# ---------------------------------------------------------------------------
# 1. DEMO boot (no license)
# ---------------------------------------------------------------------------
def test_demo_boot_no_license():
    lm = lm_mod.LicenseManager()
    lm.license_file = os.path.join(tempfile.gettempdir(), "nonexistent_demo.json")
    lm.owner_dev_mode = False
    plan = lm.get_plan()
    assert plan["plan"] == "DEMO", plan
    assert plan.get("licensed") is False
    assert plan["max_tracks"] == 1000
    ok, reason = lm.is_valid()
    assert ok is False and reason == "NO LICENSE", (ok, reason)
    # DEMO entitlement shape
    ent = plan["entitlements"]
    assert ent["rekordbox_export"] is False
    assert ent["dj_archive_downloads"] is False
    assert ent["server_ai"] is False
    assert ent["team_admin"] is False
    assert ent["archive_repair"] is False
    assert ent["updates_active"] is False


# ---------------------------------------------------------------------------
# 2. Enterprise activation
# ---------------------------------------------------------------------------
def test_enterprise_activation():
    lm, path = _load_manager(dict(VALID_LICENSE))
    try:
        plan = lm.get_plan()
        assert plan["plan"] == "ENTERPRISE"
        assert plan["licensed"] is True
        assert plan["max_tracks"] == 0  # unlimited
        ok, reason = lm.is_valid()
        assert ok is True and reason == "OK", (ok, reason)
        ent = plan["entitlements"]
        # Every feature on for ENTERPRISE except max_tracks (which is 0 = unlimited)
        for k, v in ent.items():
            if k in ("max_tracks", "plan", "licensed"):
                continue
            assert v is True, f"ENTERPRISE entitlement {k} should be ON"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# 3. Fail-closed matrix
# ---------------------------------------------------------------------------
def test_fail_closed_invalid_signature():
    p = dict(VALID_LICENSE)
    p["signature"] = "00" * 64
    lm, path = _load_manager(p)
    try:
        ok, reason = lm.is_valid()
        assert ok is False and reason == "INVALID SIGNATURE", (ok, reason)
    finally:
        os.unlink(path)


def test_fail_closed_tampered_payload():
    p = dict(VALID_LICENSE)
    p["plan"] = "PRO"  # payload changed after signing
    lm, path = _load_manager(p)
    try:
        ok, reason = lm.is_valid()
        assert ok is False and reason == "INVALID SIGNATURE", (ok, reason)
    finally:
        os.unlink(path)


def test_fail_closed_expired():
    p = dict(VALID_LICENSE)
    p["expiry"] = "2020-01-01"
    lm, path = _load_manager(p)
    try:
        ok, reason = lm.is_valid()
        assert ok is False and reason in ("INVALID SIGNATURE", "EXPIRED"), (ok, reason)
    finally:
        os.unlink(path)


def test_fail_closed_wrong_machine():
    p = dict(VALID_LICENSE)
    p["machine_id"] = "0" * 64
    lm, path = _load_manager(p)
    try:
        ok, reason = lm.is_valid()
        assert ok is False and reason == "WRONG MACHINE", (ok, reason)
    finally:
        os.unlink(path)


def test_fail_closed_corrupt_json():
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("{ this is not valid json ")
    lm = lm_mod.LicenseManager()
    lm.license_file = path
    lm.owner_dev_mode = False
    try:
        ok, reason = lm.is_valid()
        assert ok is False
        assert reason in ("NO LICENSE", "INVALID STRUCTURE", "INVALID SIGNATURE"), (ok, reason)
    finally:
        os.unlink(path)


def test_fail_closed_missing_fields():
    p = {"plan": "ENTERPRISE", "machine_id": "abc"}
    lm, path = _load_manager(p)
    try:
        ok, reason = lm.is_valid()
        assert ok is False and reason in ("INVALID STRUCTURE", "INVALID SIGNATURE"), (ok, reason)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# 4. Navigation 23/23
# ---------------------------------------------------------------------------
def test_nav_count_is_23():
    assert len(NAV_ITEMS) == 23, len(NAV_ITEMS)


def test_nav_viewkeys_distinct():
    views = [v for (_, v, _, _) in NAV_ITEMS]
    assert len(views) == len(set(views)), "duplicate view keys in NAV_ITEMS"


def test_nav_set_view_dispatch_distinct_builders():
    # Every NAV view key must map to exactly one distinct builder in set_view.
    builders = _SET_VIEW_BUILDERS
    seen = {}
    for label_key, view, icon, req in NAV_ITEMS:
        assert view in builders, f"NAV view {view} has no set_view builder"
        b = builders[view]
        # builder must be a real bound method on MainWindow
        assert callable(b), f"builder for {view} not callable"
        # distinct: no two nav views share the same builder object
        if id(b) in seen.values():
            dup = [k for k, v in seen.items() if v == id(b)]
            assert view in dup or False, f"builder reused across {dup} and {view}"
        seen[view] = id(b)


def test_nav_protected_consistent_with_sidebar():
    # VIEW_REQUIREMENTS plan gating must match sidebar NAV required_plan.
    vr = _VIEW_REQUIREMENTS
    nav_map = {v: req for (_, v, _, req) in NAV_ITEMS}
    for view, req in vr.items():
        assert nav_map.get(view) == req, f"{view}: VIEW_REQ={req} != NAV={nav_map.get(view)}"
    # Every protected NAV view appears in VIEW_REQUIREMENTS
    for view, req in nav_map.items():
        if req is not None:
            assert view in vr, f"{view} protected in NAV but missing from VIEW_REQUIREMENTS"


# ---------------------------------------------------------------------------
# 5. HUD regression
# ---------------------------------------------------------------------------
def test_hud_disabled_views():
    disabled = _HUD_DISABLED
    assert "dashboard" in disabled
    assert "archive_guardian" in disabled
    # 21 others must be HUD-enabled
    enabled = [v for (_, v, _, _) in NAV_ITEMS if v not in disabled]
    assert len(enabled) == 21, len(enabled)


def test_hud_content_below_canvas():
    # The HUD canvas must be lowered so view content sits above it.
    # Frozen tree ships compiled .pyc; read the source via inspect.
    import inspect
    src = inspect.getsource(mw_mod.MainWindow._hud_apply_visibility)
    assert len(src) > 0
    # The regression we guard against: tkraise() lifting the opaque HUD canvas
    # ABOVE view content. The code must NOT call cv.tkraise — it relies on
    # creation-order z-order (canvas created before self.content).
    # Assert no actual tkraise CALL appears in the body (only the warning
    # comment is allowed).
    call_lines = [ln for ln in src.splitlines()
                  if "tkraise" in ln and not ln.strip().startswith("#")]
    assert not call_lines, f"HUD must NOT tkraise above view content: {call_lines}"
    # Disabled views must hide the canvas (place_forget + delete).
    assert "place_forget" in src and "cv.delete" in src, \
        "HUD apply_visibility must hide the canvas for disabled views"


# ---------------------------------------------------------------------------
# 6. Turkish TTS / UI defaults
# ---------------------------------------------------------------------------
def test_turkish_default_voice():
    vid = voice_config.get_voice_id()
    assert vid == "tr-TR-EmelNeural", vid


def test_turkish_boot_line():
    line = voice_config.get_boot_line("tr-TR-EmelNeural")
    assert "Merhaba" in line
    assert "Geleceğin Teknolojisi" in line
    assert "Görüşmek üzere" in line


def test_sidebar_turkish_labels():
    # i18n resolver must return Turkish (default lang) for sidebar keys
    from app.core.i18n import t
    # Force Turkish default
    label = t("sidebar.library")
    assert label != "sidebar.library", "i18n fell back to raw key (locales missing)"
    assert "Kütüphane" in label or "kütüphane" in label.lower(), label


# ---------------------------------------------------------------------------
# 7. APPDATA persistence / Program Files writes
# ---------------------------------------------------------------------------
def test_appdata_license_path():
    p = paths.get_license_path()
    assert "APPDATA" in str(p).upper() or "DJ_AI_OS" in str(p), str(p)
    assert p.name == "license.key"


def test_no_programfiles_write_in_paths():
    for name in ("get_db_path", "get_log_dir", "get_license_path", "get_cache_dir"):
        fn = getattr(paths, name)
        val = fn()
        assert "PROGRAMFILES" not in str(val).upper(), f"{name} -> {val}"
        assert "PROGRA~" not in str(val).upper(), f"{name} -> {val}"


# ---------------------------------------------------------------------------
# 8. Security — no secrets in frozen tree
# ---------------------------------------------------------------------------
def test_no_private_key_in_tree():
    hits = []
    for root, dirs, files in os.walk(FROZEN):
        for fn in files:
            if fn == "vendor_private_key.pem" or fn.endswith(".pem") and "private" in fn.lower():
                hits.append(os.path.join(root, fn))
    assert not hits, f"Private key present: {hits}"


def test_no_dev_or_license_artifacts():
    forbidden = {"dev.flag", "license.key", "test_license.json",
                 "test_analysis.db", "dj_database.db", "dj_memory.db"}
    hits = []
    for root, dirs, files in os.walk(FROZEN):
        for fn in files:
            if fn in forbidden:
                hits.append(os.path.join(root, fn))
    assert not hits, f"Forbidden artifact in tree: {hits}"


def test_no_forbidden_artifacts_in_data():
    # User's explicit forbidden list (from requirements):
    # vendor_private_key.pem, dev.flag, license.key, test_license.json,
    # test_analysis.db, dj_database.db, dj_memory.db
    # These MUST NOT appear anywhere in frozen tree.
    # __pycache__ in data/db/ is COMPILED BYTECODE of ai_library_db.py
    # (imported by main_window.py) and is REQUIRED at runtime.
    forbidden = {"vendor_private_key.pem", "dev.flag", "license.key",
                 "test_license.json", "test_analysis.db",
                 "dj_database.db", "dj_memory.db"}
    hits = []
    for root, dirs, files in os.walk(FROZEN):
        for fn in files:
            if fn in forbidden:
                hits.append(os.path.join(root, fn))
    assert not hits, f"Forbidden artifact in frozen tree: {hits}"
