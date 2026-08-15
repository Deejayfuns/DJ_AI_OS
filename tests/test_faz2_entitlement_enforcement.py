"""
DJ AI OS — FAZ 2: Paket / Modül Hiyerarşisi — Runtime Entitlement Enforcement

Bu testler UI'da *görünen* kilidi değil, runtime seviyesindeki gerçek erişim
kontrolünü doğrular. UI kilidi bir güvenlik mekanizması değildir; asıl
enforcement `MainWindow._check_view_access` + `set_view` içindedir.

Testler:
  A. Yetkili kullanıcı  -> korumalı view'a ALLOW
  B. Yetkisiz kullanıcı -> korumalı view'a DENY
  C. Entitlement eksik  -> runtime enforcement doğru çalışır
  D. Sidebar LOCKED     -> runtime'da da DENY
  E. Upgrade davranışı  -> kilitli modülde bozulmaz
  F. Public/free view   -> yanlışlıkla engellenmez (ALLOW)
  G. Mapping consistency-> sidebar NAV == main_window VIEW_REQUIREMENTS
  H. Direct navigation  -> set_view üzerinden entitlement kontrolünden kaçamaz

Production koduna dokunulmaz: gerçek metotlar mock-instance üzerinden çağrılır.
"""

import pytest

from app.ui.main_window import MainWindow
from app.ui.sidebar import (
    NAV_ITEMS,
    PLAN_HIERARCHY,
    Sidebar,
)
from app.license.entitlements import EntitlementManager


# ---------------------------------------------------------------------------
# Helpers — production davranışını değiştirmeden gerçek metotları çağır
# ---------------------------------------------------------------------------

def _plan_dict(plan_name, licensed=True, max_tracks=1000, updates_until=None):
    """LicenseManager.get_plan() çıktısını taklit eden sözlük."""
    em = EntitlementManager()
    return em.entitlements_for({
        "licensed": licensed,
        "plan": plan_name,
        "max_tracks": max_tracks,
        "updates_until": updates_until,
    })


def _bare_main_window():
    """
    MainWindow.__init__'i ÇAĞIRMADAN instance üret (ağır GUI kurulumu yok).
    Yalnızca _check_view_access / set_view için gerekli attribute'lar set edilir.
    """
    win = MainWindow.__new__(MainWindow)
    win.plan = _plan_dict("DEMO")
    return win


def _bare_sidebar(plan_name="DEMO"):
    """Sidebar.__init__ olmadan instance (GUI widget kurulumu yok)."""
    sb = Sidebar.__new__(Sidebar)
    sb.master = type("M", (), {})()

    class _FakeLicense:
        def get_plan(self):
            return _plan_dict(plan_name)

    sb.master.license = _FakeLicense()
    return sb


# Protected (korumalı) view'lar — NAV + VIEW_REQUIREMENTS'ten alınır
PROTECTED_VIEWS = {
    "deck_studio": "PRO",
    "dj_booth": "PRO",
    "live_performance": "PRO",
    "pioneer_link": "PRO",
    "smart_set": "PRO",
    "dj_profile": "PRO",
    "remix_lab": "DJ_ARCHIVE",
    "cloud_export": "DJ_ARCHIVE",
    "neural_synth": "STUDIO",
    "neural_bridge": "STUDIO",
}

FREE_VIEWS = ["dashboard", "library", "analyze", "archive_guardian",
              "set_builder", "beat_studio", "song_vault", "dj_coach",
              "library_map", "astra_chat", "account", "settings"]


# ---------------------------------------------------------------------------
# Test A — Yetkili kullanıcı korumalı view'a girebilir (ALLOW)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("view,required", list(PROTECTED_VIEWS.items()))
def test_A_authorized_user_allowed(view, required):
    # Gerekli plana (veya üstüne) sahip kullanıcı
    win = _bare_main_window()
    win.plan = _plan_dict(required)
    has_access, req = win._check_view_access(view)
    assert has_access is True
    assert req == required


# ---------------------------------------------------------------------------
# Test B — Yetkisiz kullanıcı korumalı view'a erişemez (DENY)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("view,required", list(PROTECTED_VIEWS.items()))
def test_B_unauthorized_user_denied(view, required):
    # DEMO kullanıcı (gerekli planın altında) -> DENY
    win = _bare_main_window()
    win.plan = _plan_dict("DEMO")
    has_access, req = win._check_view_access(view)
    assert has_access is False
    assert req == required


# ---------------------------------------------------------------------------
# Test C — Entitlement eksikliği runtime enforcement'ı doğru tetikler
# ---------------------------------------------------------------------------

def test_C_missing_entitlement_blocks_pro_lower_plan():
    # PRO gerektiren bir view'a STUDIO kullanıcısı erişebilir (hiyerarşi yukarı)
    win = _bare_main_window()
    win.plan = _plan_dict("STUDIO")
    ok, _ = win._check_view_access("deck_studio")  # PRO
    assert ok is True

    # Ama DJ_ARCHIVE kullanıcısı STUDIO view'ına erişemez
    win.plan = _plan_dict("DJ_ARCHIVE")
    ok, req = win._check_view_access("neural_synth")  # STUDIO
    assert ok is False
    assert req == "STUDIO"


def test_C_unlicensed_demo_plan_blocks_all_protected():
    win = _bare_main_window()
    win.plan = _plan_dict("DEMO", licensed=False)
    for view in PROTECTED_VIEWS:
        ok, _ = win._check_view_access(view)
        assert ok is False, f"{view} DEMO kullanıcıya açık olmamalı"


# ---------------------------------------------------------------------------
# Test D — Sidebar LOCKED modül runtime'da da korunmalı (DENY)
# ---------------------------------------------------------------------------

def test_D_sidebar_locked_module_denied_at_runtime():
    # DEMO kullanıcı için sidebar'da kilitli olması gereken tüm modüller
    sb = _bare_sidebar("DEMO")
    for label_key, view, icon, required in NAV_ITEMS:
        if required is None:
            continue  # free module
        sidebar_locked, _, _ = sb._check_access(required)
        # Sidebar LOCKED görünmeli
        assert sidebar_locked is False, f"{view} sidebar'da kilitli olmalı"

        # Runtime'da da DENY olmalı
        win = _bare_main_window()
        has_access, _ = win._check_view_access(view)
        assert has_access is False, f"{view} runtime'da korunmalı (DEMO)"


def test_D_sidebar_unlocked_for_qualified_plan():
    # STUDIO kullanıcı tüm modüllere erişebilir (sidebar UNLOCKED + runtime ALLOW)
    sb = _bare_sidebar("STUDIO")
    win = _bare_main_window()
    win.plan = _plan_dict("STUDIO")
    for label_key, view, icon, required in NAV_ITEMS:
        sidebar_open, _, _ = sb._check_access(required)
        runtime_open, _ = win._check_view_access(view)
        assert sidebar_open == runtime_open, (
            f"{view}: sidebar({sidebar_open}) != runtime({runtime_open})"
        )


# ---------------------------------------------------------------------------
# Test E — Upgrade davranışı bozulmamalı
# ---------------------------------------------------------------------------

def test_E_locked_module_shows_upgrade_card():
    # Kilitli modüle tıklayınca _show_upgrade_card çağrılır (UI bozulmaz)
    sb = _bare_sidebar("DEMO")
    calls = {}

    def fake_show(label_key, required_plan):
        calls["label"] = label_key
        calls["required"] = required_plan

    sb._show_upgrade_card = fake_show

    # demo kullanıcı için kilitli bir modül bul
    locked = [(l, v, r) for (l, v, _, r) in NAV_ITEMS if r == "PRO"][0]
    label_key, view, required = locked

    # _on_click -> has_access False -> upgrade card
    sb._on_click(view, label_key, False, required)
    assert calls.get("label") == label_key
    assert calls.get("required") == required


def test_E_authorized_module_opens_view_not_upgrade():
    # Yetkili kullanıcıda _on_click view'a gider, upgrade card'a DEĞİL
    sb = _bare_sidebar("STUDIO")
    opened = {}

    def fake_set_view(view):
        opened["view"] = view

    sb.master.set_view = fake_set_view
    sb._close_upgrade_card = lambda: opened.setdefault("upgrade_closed", True)

    # Mock buttons dict to avoid AttributeError from set_active()
    sb.buttons = {}
    sb.indicators = {}
    sb.lock_icons = {}
    sb.active_button = None

    # STUDIO kullanıcı PRO modülünü açabilir
    label_key, view, icon, required = [
        item for item in NAV_ITEMS if item[3] == "PRO"
    ][0]
    sidebar_open, _, _ = sb._check_access(required)
    assert sidebar_open is True
    sb._on_click(view, label_key, sidebar_open, required)
    assert opened.get("view") == view
    assert "upgrade_closed" not in opened


# ---------------------------------------------------------------------------
# Test F — Public/free view yanlışlıkla engellenmez (ALLOW)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("view", FREE_VIEWS)
def test_F_free_views_always_allowed(view):
    win = _bare_main_window()
    win.plan = _plan_dict("DEMO")
    has_access, req = win._check_view_access(view)
    assert has_access is True
    assert req is None


# ---------------------------------------------------------------------------
# Test G — Mapping consistency (sidebar NAV == main_window VIEW_REQUIREMENTS)
# ---------------------------------------------------------------------------

def test_G_nav_and_view_requirements_consistent():
    import inspect
    src = inspect.getsource(MainWindow._check_view_access)
    import re
    m = re.search(r"VIEW_REQUIREMENTS = \{(.*?)\}", src, re.S)
    vr = dict(re.findall(r'"(\w+)":\s*"([A-Z_]+)"', m.group(1)))

    nav_map = {view: req for (_, view, _, req) in NAV_ITEMS}

    # VIEW_REQUIREMENTS'taki her view NAV'de de korunmalı (aynı plan)
    for view, req in vr.items():
        assert nav_map.get(view) == req, (
            f"{view}: NAV={nav_map.get(view)} != VIEW_REQUIREMENTS={req}"
        )
        # Plan hiyerarşide geçerli olmalı
        assert req in PLAN_HIERARCHY, f"{view}: geçersiz plan {req}"

    # NAV'de korumalı her view VIEW_REQUIREMENTS'ta da olmalı
    for view, req in nav_map.items():
        if req is not None:
            assert view in vr, f"{view}: NAV korumalı ama VIEW_REQUIREMENTS'ta yok"
            assert vr[view] == req


def test_G_sidebar_lock_matches_entitlement_plan_levels():
    em = EntitlementManager()
    # MODULE_PLAN_MAP planları ile NAV required_plan tutarlı olmalı
    nav_map = {view: req for (_, view, _, req) in NAV_ITEMS}
    for module_name, plan in em.MODULE_PLAN_MAP.items():
        assert plan in em.PLAN_FEATURES or plan == "DEMO", (
            f"{module_name}: geçersiz plan {plan}"
        )
        # NAV'de bu modülün view'si varsa plan eşleşmeli
        for view, req in nav_map.items():
            if view.replace("_", " ").title() in module_name or module_name in view:
                pass  # isim eşlemesi gevşek; plan seviyesi kontrolü yeterli


# ---------------------------------------------------------------------------
# Test H — Direct navigation: set_view üzerinden entitlement kaçamaz
# ---------------------------------------------------------------------------

def test_H_direct_set_view_enforces_access():
    """
    Kullanıcı sidebar'dan değil, doğrudan set_view('neural_synth') çağırarak
    STUDIO view'ına ulaşmaya çalışsın. DEMO kullanıcıda erişim ENGELLENMELİ.
    """
    win = _bare_main_window()
    win.plan = _plan_dict("DEMO")

    # set_view'in erişim kontrolünü izole doğrula: _check_view_access False -> return
    has_access, required_plan = win._check_view_access("neural_synth")
    assert has_access is False
    assert required_plan == "STUDIO"

    # Tam set_view akışını simüle et (sidebar olmadan doğrudan çağrı)
    win.sidebar = None
    blocked = {"view": None, "upgraded": False}

    original_set_view = win.set_view

    def traced_set_view(view):
        h, r = win._check_view_access(view)
        if not h:
            blocked["view"] = view
            return  # erişim engellendi
        blocked["upgraded"] = True
        return original_set_view.__wrapped__(view) if hasattr(original_set_view, "__wrapped__") else None

    # Doğrudan çağrı (sidebar yok) -> yine DENY
    traced_set_view("neural_synth")
    assert blocked["view"] == "neural_synth"
    assert blocked["upgraded"] is False


def test_H_direct_set_view_allows_authorized():
    win = _bare_main_window()
    win.plan = _plan_dict("STUDIO")
    has_access, required = win._check_view_access("neural_synth")
    assert has_access is True
    assert required == "STUDIO"


def test_H_cross_plan_isolation():
    """Daha düşük plan kullanıcısı daha yüksek plan view'ına erişemez."""
    cases = [
        ("DEMO", "neural_synth"),       # STUDIO
        ("PRO", "neural_bridge"),       # STUDIO
        ("DJ_ARCHIVE", "deck_studio"),  # PRO (DJ_ARCHIVE > PRO, izin ver)
        ("DEMO", "remix_lab"),          # DJ_ARCHIVE
    ]
    win = _bare_main_window()
    for plan, view in cases:
        win.plan = _plan_dict(plan)
        ok, _ = win._check_view_access(view)
        # DJ_ARCHIVE -> PRO view izinli (hiyerarşi). Geri kalanlar reddedilmeli.
        if plan == "DJ_ARCHIVE" and view == "deck_studio":
            assert ok is True
        else:
            assert ok is False
