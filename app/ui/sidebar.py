"""
DJ AI OS — Pro DJ Sidebar (Rekordbox/Serato style)

Compact sidebar with icon-based navigation.
Active state: RED left indicator bar.
Collapsed: 56px with icons. Expanded: 220px with labels.
"""

import customtkinter as ctk
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, RED_DIM,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, BLUE_BRIGHT,
    F_H3, F_META,
)
from app.core.i18n import t


# Nav items: (label_key, view_key, icon_unicode)
NAV_ITEMS = [
    ("sidebar.performance",   "performance_dash",   "⚡"),
    ("sidebar.dashboard",     "dashboard",          "📊"),
    ("sidebar.music_doctor",  "analyze",            "🏥"),
    ("sidebar.library",       "library",            "📁"),
    ("sidebar.archive",       "archive_guardian",   "🛡"),
    ("sidebar.set_builder",   "set_show",           "🎛"),
    ("sidebar.deck_studio",   "deck_studio",        "🎚"),
    ("sidebar.dj_booth",      "dj_booth",           "🎧"),
    ("sidebar.beat_studio",   "beat_studio",        "🎵"),
    ("sidebar.neural_synth",  "neural_synth",       "🧠"),
    ("sidebar.neural_bridge", "neural_bridge",      "🌉"),
    ("sidebar.pioneer_link",  "pioneer_link",       "🎛"),
    ("sidebar.dj_coach",      "dj_coach",           "📝"),
    ("sidebar.library_map",   "library_map",        "🗺"),
    ("sidebar.smart_set",     "smart_set",          "⚡"),
    ("sidebar.dj_profile",    "dj_profile",         "👤"),
    ("sidebar.remix_lab",     "remix_lab",          "🔀"),
    ("sidebar.astra_chat",    "astra_chat",         "🤖"),
    ("sidebar.export_cloud",  "cloud_export",       "☁"),
    ("sidebar.account",       "account",            "⚙"),
    ("sidebar.settings",      "settings",           "🔧"),
]


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
        self.nav = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=SURFACE_RAISED,
            scrollbar_button_hover_color=BORDER,
        )
        self.nav.pack(fill="both", expand=True)

        # =================================================
        # NAV BUTTONS
        # =================================================
        for label_key, view, icon in NAV_ITEMS:
            label_text = t(label_key)
            btn_frame = ctk.CTkFrame(self.nav, fg_color="transparent", height=32)
            btn_frame.pack(fill="x", padx=6, pady=1)
            btn_frame.pack_propagate(False)

            btn = ctk.CTkButton(
                btn_frame,
                text=f" {icon}  {label_text}",
                height=32,
                corner_radius=4,
                fg_color="transparent",
                hover_color=SURFACE_RAISED,
                text_color=TEXT_SECONDARY,
                anchor="w",
                font=("Segoe UI", 11),
                command=lambda v=view, k=label_key: self._on_click(v, k),
            )
            btn.pack(fill="x", side="left", expand=True)

            # left indicator bar (hidden until active)
            ind = ctk.CTkFrame(btn_frame, width=3, height=22, fg_color="transparent",
                               corner_radius=0)
            ind.pack(side="left", padx=(0, 0))
            ind.pack_propagate(False)

            self.buttons[label_key] = btn
            self.labels[label_key] = label_key
            self.indicators[label_key] = ind

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

    def _on_click(self, view, label_key):
        if hasattr(self.master, "set_view"):
            self.master.set_view(view)
        self.set_active(label_key)

    def set_active(self, label_key):
        icon = lambda name: NAV_ITEMS[[i[0] for i in NAV_ITEMS].index(name)][2]
        for name, btn in self.buttons.items():
            label_text = t(name)
            ind = self.indicators.get(name)
            if name == label_key:
                btn.configure(
                    fg_color=RED_DIM,
                    text_color=TEXT_PRIMARY,
                    font=("Segoe UI", 11, "bold"),
                    text=f" {icon(name)}  {label_text}",
                )
                if ind is not None:
                    ind.configure(fg_color=RED)
                self.active_button = btn
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_SECONDARY,
                    font=("Segoe UI", 11),
                    text=f" {icon(name)}  {label_text}",
                )
                if ind is not None:
                    ind.configure(fg_color="transparent")
