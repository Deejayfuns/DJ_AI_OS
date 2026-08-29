"""
DJ AI OS — Pro DJ Sidebar (Rekordbox/Serato style)

Compact sidebar with icon-based navigation.
Active state: RED left indicator bar.
Collapsed: 56px with icons. Expanded: 220px with labels.
Module gating with lock icons and upgrade cards.
"""

import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, RED_DIM,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BLUE_BRIGHT, AMBER, GREEN,
    F_H3, F_META, F_BODY,
)
from app.core.i18n import t


# Nav items: (label_key, view_key, icon_unicode, required_plan)
# required_plan: minimum plan needed to access (DEMO, PRO, DJ_ARCHIVE, STUDIO, ENTERPRISE)
# None = always accessible (DEMO and above)
NAV_ITEMS = [
    ("sidebar.performance",   "performance_dash",   "⚡", None),          # DEMO
    ("sidebar.dashboard",     "dashboard",          "📊", None),          # DEMO
    ("sidebar.music_doctor",  "analyze",            "🏥", None),          # DEMO
    ("sidebar.library",       "library",            "📁", None),          # DEMO
    ("sidebar.archive",       "archive_guardian",   "🛡", None),          # DEMO
    ("sidebar.set_builder",   "set_show",           "🎛", None),          # DEMO
    ("sidebar.deck_studio",   "deck_studio",        "🎚", "PRO"),         # PRO
    ("sidebar.dj_booth",      "dj_booth",           "🎧", "PRO"),         # PRO
    ("sidebar.beat_studio",   "beat_studio",        "🎵", None),          # DEMO (limited)
    ("sidebar.live_performance", "live_performance", "🎹", "PRO"),        # PRO
    ("sidebar.song_vault",    "song_vault",         "💾", None),          # DEMO
    ("sidebar.neural_synth",  "neural_synth",       "🧠", "STUDIO"),      # STUDIO
    ("sidebar.neural_bridge", "neural_bridge",      "🌉", "STUDIO"),      # STUDIO
    ("sidebar.pioneer_link",  "pioneer_link",       "🎛", "PRO"),         # PRO
    ("sidebar.dj_coach",      "dj_coach",           "📝", None),          # DEMO
    ("sidebar.library_map",   "library_map",        "🗺", None),          # DEMO
    ("sidebar.smart_set",     "smart_set",          "⚡", "PRO"),         # PRO
    ("sidebar.dj_profile",    "dj_profile",         "👤", "PRO"),         # PRO
    ("sidebar.remix_lab",     "remix_lab",          "🔀", "DJ_ARCHIVE"),  # DJ_ARCHIVE
    ("sidebar.astra_chat",    "astra_chat",         "🤖", None),          # DEMO
    ("sidebar.export_cloud",  "cloud_export",       "☁", "DJ_ARCHIVE"),   # DJ_ARCHIVE
    ("sidebar.account",       "account",            "⚙", None),           # DEMO
    ("sidebar.settings",      "settings",           "🔧", None),          # DEMO
]


# Plan hierarchy for comparison
PLAN_HIERARCHY = {
    "DEMO": 0,
    "PRO": 1,
    "DJ_ARCHIVE": 2,
    "STUDIO": 3,
    "ENTERPRISE": 4,
    "OWNER_DEV": 5,
}

PLAN_DISPLAY = {
    "DEMO": "DEMO",
    "PRO": "PRO ($9.99/ay)",
    "DJ_ARCHIVE": "DJ ARCHIVE ($19.99/ay)",
    "STUDIO": "STUDIO ($39.99/ay)",
    "ENTERPRISE": "ENTERPRISE (özel)",
    "OWNER_DEV": "OWNER DEV",
}


class Sidebar(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            width=180,
            fg_color=SURFACE,
            corner_radius=0,
        )

        self.master = master
        self.active_button = None
        self.active_label = None
        self.buttons = {}
        self.labels = {}
        self.indicators = {}   # label_key -> left indicator bar widget
        self.lock_icons = {}   # label_key -> lock icon label
        self.nav_items = NAV_ITEMS  # Store for access checking
        self._upgrade_card = None  # Currently shown upgrade card

        self.pack_propagate(False)
        self._build()

    def _build(self):
        # =================================================
        # LOGO
        # =================================================
        self.logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.logo_frame.pack(fill="x", pady=(12, 4))

        ctk.CTkLabel(
            self.logo_frame, text="DJ AI OS", font=F_H3, text_color=RED,
        ).pack(anchor="w", padx=14)

        ctk.CTkLabel(
            self.logo_frame, text="PRO DJ", font=F_META, text_color=TEXT_DIM,
        ).pack(anchor="w", padx=14)

        # =================================================
        # SEPARATOR
        # =================================================
        sep = ctk.CTkFrame(self, height=1, fg_color=BORDER)
        sep.pack(fill="x", padx=12, pady=(8, 8))

        # =================================================
        # NAV SCROLLABLE
        # =================================================
        # Clear existing nav if rebuilding (e.g. after language change)
        if hasattr(self, "nav") and self.nav.winfo_exists():
            for widget in self.nav.winfo_children():
                widget.destroy()

        self.nav = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=SURFACE_RAISED,
            scrollbar_button_hover_color=BORDER,
        )
        self.nav.pack(fill="both", expand=True)

        # Clear state dicts before rebuilding
        self.buttons.clear()
        self.labels.clear()
        self.indicators.clear()
        self.lock_icons.clear()

        # =================================================
        # NAV BUTTONS (with lock icons)
        # =================================================
        for item in NAV_ITEMS:
            label_key, view, icon, required_plan = item
            label_text = t(label_key)
            btn_frame = ctk.CTkFrame(self.nav, fg_color="transparent", height=32)
            btn_frame.pack(fill="x", padx=6, pady=1)
            btn_frame.pack_propagate(False)

            # Check access
            has_access, user_plan, required = self._check_access(required_plan)

            # Button text with lock if needed
            btn_text = f" {icon}  {label_text}"
            text_color = TEXT_SECONDARY if has_access else TEXT_DIM

            btn = ctk.CTkButton(
                btn_frame,
                text=btn_text,
                height=32,
                corner_radius=4,
                fg_color=SURFACE,
                hover_color=SURFACE_RAISED if has_access else SURFACE,
                text_color=text_color,
                anchor="w",
                font=("Segoe UI", 11),
                command=lambda v=view, k=label_key, a=has_access, r=required_plan: self._on_click(v, k, a, r),
            )
            btn.pack(fill="x", side="left", expand=True)

            # left indicator bar (hidden until active)
            ind = ctk.CTkFrame(btn_frame, width=3, height=22, fg_color="transparent",
                               corner_radius=0)
            ind.pack(side="left", padx=(0, 0))
            ind.pack_propagate(False)

            # Lock icon (right side)
            lock_label = ctk.CTkLabel(
                btn_frame,
                text="🔒" if not has_access else "",
                text_color=AMBER if not has_access else TEXT_DIM,
                font=("Segoe UI", 10),
            )
            lock_label.pack(side="right", padx=(0, 8))

            self.buttons[label_key] = btn
            self.labels[label_key] = label_key
            self.indicators[label_key] = ind
            self.lock_icons[label_key] = lock_label

        # =================================================
        # FOOTER
        # =================================================
        footer_sep = ctk.CTkFrame(self, height=1, fg_color=BORDER)
        footer_sep.pack(fill="x", padx=12, pady=(8, 4))

        self.version = ctk.CTkLabel(
            self, text="v24 ULTRA PRODUCER",
            font=("Consolas", 9), text_color=TEXT_DIM,
        )
        self.version.pack(pady=(0, 10))

        # Default active
        self.set_active("sidebar.dashboard")

    def _check_access(self, required_plan):
        """Check if current user plan meets required_plan."""
        if required_plan is None:
            return True, None, None

        user_plan = "DEMO"
        if hasattr(self.master, "license") and self.master.license:
            plan_data = self.master.license.get_plan()
            user_plan = plan_data.get("plan", "DEMO")

        user_level = PLAN_HIERARCHY.get(user_plan, 0)
        required_level = PLAN_HIERARCHY.get(required_plan, 0)

        has_access = user_level >= required_level
        return has_access, user_plan, required_plan

    def _on_click(self, view, label_key, has_access, required_plan):
        if not has_access:
            self._show_upgrade_card(label_key, required_plan)
            return

        if hasattr(self.master, "set_view"):
            self.master.set_view(view)
        self.set_active(label_key)

    def _show_upgrade_card(self, label_key, required_plan):
        """Show upgrade card when user clicks locked module."""
        # Destroy existing card
        if self._upgrade_card:
            try:
                self._upgrade_card.destroy()
            except Exception:
                pass

        # Find the nav item
        nav_item = next((item for item in NAV_ITEMS if item[0] == label_key), None)
        if not nav_item:
            return

        _, view, icon, _ = nav_item
        module_name = t(label_key)
        required_display = PLAN_DISPLAY.get(required_plan, required_plan)

        # Get user's current plan
        user_plan = "DEMO"
        if hasattr(self.master, "license") and self.master.license:
            plan_data = self.master.license.get_plan()
            user_plan = plan_data.get("plan", "DEMO")

        # Create upgrade card
        card = ctk.CTkFrame(self.nav, fg_color=SURFACE_RAISED, corner_radius=8, border_width=1, border_color=AMBER)
        card.pack(fill="x", padx=6, pady=(4, 8))

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            header,
            text=f"🔒 {module_name}",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text=f"{required_display} gerekli",
            font=("Segoe UI", 10),
            text_color=AMBER,
        ).pack(side="right")

        # Description
        desc_map = {
            "PRO": "Profesyonel kütüphane AI, Rekordbox hazırlığı, Deck Studio, Live Performance, 50k track.",
            "DJ_ARCHIVE": "PRO özellikleri + aylık DJ arşiv indirmeleri, Remix Lab, Cloud Export.",
            "STUDIO": "DJ ARCHIVE özellikleri + çoklu DJ studio, admin kontrolleri, cloud AI, team yönetimi.",
            "ENTERPRISE": "Özel lisanslama, kurumsal destek, SLA, on-premise AI.",
        }
        desc = desc_map.get(required_plan, f"{required_display} planı bu modülü açar.")

        ctk.CTkLabel(
            card,
            text=desc,
            font=("Segoe UI", 10),
            text_color=TEXT_SECONDARY,
            wraplength=200,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Upgrade buttons
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        # Monthly button
        monthly_price = self._get_price(required_plan, "monthly")
        yearly_price = self._get_price(required_plan, "yearly")

        if monthly_price:
            monthly_btn = ctk.CTkButton(
                btn_frame,
                text=f"Aylık ${monthly_price:.2f}/ay",
                height=28,
                font=("Segoe UI", 10),
                command=lambda: self._open_checkout(required_plan, "monthly"),
            )
            monthly_btn.pack(side="left", padx=(0, 6))

        if yearly_price:
            yearly_btn = ctk.CTkButton(
                btn_frame,
                text=f"Yıllık ${yearly_price:.2f}/yıl (%{int((1 - yearly_price/(monthly_price*12))*100)} indirim)" if monthly_price else f"Yıllık ${yearly_price:.2f}",
                height=28,
                font=("Segoe UI", 10),
                fg_color=GREEN,
                hover_color="#1e8a49",
                command=lambda: self._open_checkout(required_plan, "yearly"),
            )
            yearly_btn.pack(side="left", padx=6)

        # Close button
        close_btn = ctk.CTkButton(
            btn_frame,
            text="KAPAT",
            height=28,
            width=60,
            fg_color="transparent",
            border_width=1,
            border_color=BORDER,
            command=self._close_upgrade_card,
        )
        close_btn.pack(side="right")

        self._upgrade_card = card

    def _get_price(self, plan, period):
        """Get price for plan and period."""
        if not hasattr(self.master, "license") or not self.master.license:
            return None
        pricing = self.master.license.entitlements.pricing_table().get(plan, {})
        return pricing.get(f"{period}_usd")

    def _open_checkout(self, plan, period):
        """Open checkout for upgrade."""
        if hasattr(self.master, "create_checkout_intent"):
            self.master.create_checkout_intent(plan)
        self._close_upgrade_card()

    def _close_upgrade_card(self):
        """Close the upgrade card."""
        if self._upgrade_card:
            try:
                self._upgrade_card.destroy()
            except Exception:
                pass
            self._upgrade_card = None

    def set_active(self, label_key):
        icon = lambda name: NAV_ITEMS[[i[0] for i in NAV_ITEMS].index(name)][2]
        for name, btn in self.buttons.items():
            label_text = t(name)
            ind = self.indicators.get(name)
            lock = self.lock_icons.get(name)
            has_access, _, _ = self._check_access(
                next((item[3] for item in NAV_ITEMS if item[0] == name), None)
            )

            if name == label_key and has_access:
                btn.configure(
                    fg_color=RED_DIM,
                    text_color=TEXT_PRIMARY,
                    font=("Segoe UI", 11, "bold"),
                    text=f" {icon(name)}  {label_text}",
                )
                if ind is not None:
                    ind.configure(fg_color=RED)
                if lock is not None:
                    lock.configure(text="", text_color=TEXT_DIM)
                self.active_button = btn
            else:
                btn.configure(
                    fg_color=SURFACE,
                    text_color=TEXT_SECONDARY if has_access else TEXT_DIM,
                    font=("Segoe UI", 11),
                    text=f" {icon(name)}  {label_text}",
                )
                if ind is not None:
                    ind.configure(fg_color="transparent")
                if lock is not None:
                    lock.configure(text="🔒" if not has_access else "", text_color=AMBER if not has_access else TEXT_DIM)

    def refresh_access(self):
        """Refresh all button states based on current plan (call after license change)."""
        for name, btn in self.buttons.items():
            required_plan = next((item[3] for item in NAV_ITEMS if item[0] == name), None)
            has_access, _, _ = self._check_access(required_plan)
            lock = self.lock_icons.get(name)
            ind = self.indicators.get(name)

            # Update button state
            if has_access:
                btn.configure(
                    hover_color=SURFACE_RAISED,
                    text_color=TEXT_SECONDARY,
                )
                if lock:
                    lock.configure(text="", text_color=TEXT_DIM)
            else:
                btn.configure(
                    hover_color=SURFACE,
                    text_color=TEXT_DIM,
                )
                if lock:
                    lock.configure(text="🔒", text_color=AMBER)
