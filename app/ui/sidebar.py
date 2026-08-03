import customtkinter as ctk

from app.ui.theme import *


class Sidebar(ctk.CTkFrame):

    def __init__(self, master):

        super().__init__(
            master,
            width=280,
            fg_color=PANEL,
            corner_radius=0,
            border_width=1,
            border_color=NEON_PURPLE_DARK
        )

        self.master = master

        self.active_button = None

        self.buttons = {}

        self.pack_propagate(False)

        self.build()

    # =====================================================
    # BUILD
    # =====================================================
    def build(self):

        # =================================================
        # TOP
        # =================================================
        self.top = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.top.pack(
            fill="x",
            pady=(30, 10)
        )

        # =================================================
        # LOGO
        # =================================================
        ctk.CTkLabel(
            self.top,
            text="DJ AI OS",
            font=("Segoe UI", 30, "bold"),
            text_color=ACCENT
        ).pack(
            anchor="w",
            padx=24
        )

        # =================================================
        # SUBTITLE
        # =================================================
        ctk.CTkLabel(
            self.top,
            text="NEON PERFORMANCE SYSTEM",
            font=("Segoe UI", 11),
            text_color=NEON_BLUE
        ).pack(
            anchor="w",
            padx=26,
            pady=(2, 18)
        )

        # =================================================
        # DIVIDER
        # =================================================
        divider = ctk.CTkFrame(
            self,
            height=1,
            fg_color=NEON_PURPLE_DARK
        )

        divider.pack(
            fill="x",
            padx=18,
            pady=(0, 20)
        )

        # =================================================
        # NAVIGATION
        # =================================================
        self.nav = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )

        self.nav.pack(
            fill="both",
            expand=True
        )

        # =================================================
        # NAV ITEMS
        # =================================================
        nav_items = [

            ("Dashboard", "dashboard"),

            ("Music Doctor", "analyze"),

            ("Library", "library"),

            ("Archive Guardian", "archive_guardian"),

            ("Set & Show", "set_show"),

            ("Deck Studio", "deck_studio"),

            ("DJ Booth", "dj_booth"),

            ("DJ Coach", "dj_coach"),

            ("Library Map", "library_map"),

            ("Smart Set", "smart_set"),

            ("Remix Lab", "remix_lab"),

            ("Astra Chat", "astra_chat"),

            ("Export & Cloud", "cloud_export"),

            ("Account", "account"),

            ("Settings", "settings")

        ]


        for label, view in nav_items:

            btn = ctk.CTkButton(

                self.nav,

                text=label,

                height=48,

                corner_radius=12,

                fg_color=CARD,

                hover_color=HOVER,

                border_width=1,

                border_color=BORDER,

                text_color=TEXT,

                anchor="w",

                font=("Segoe UI", 14, "bold"),

                command=lambda v=view, l=label:
                self.on_click(v, l)

            )

            btn.pack(
                fill="x",
                padx=18,
                pady=5
            )

            self.buttons[label] = btn

        # =================================================
        # FOOTER
        # =================================================
        self.footer = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )

        self.footer.pack(
            fill="x",
            pady=20
        )

        footer_line = ctk.CTkFrame(
            self.footer,
            height=1,
            fg_color=NEON_PURPLE_DARK
        )

        footer_line.pack(
            fill="x",
            padx=18,
            pady=(0, 15)
        )

        ctk.CTkLabel(
            self.footer,
            text="AI PERFORMANCE ENGINE",
            font=("Segoe UI", 10),
            text_color=NEON_BLUE
        ).pack(
            anchor="w",
            padx=24
        )

        ctk.CTkLabel(
            self.footer,
            text="v24 ULTRA PRODUCER",
            font=("Segoe UI", 10, "bold"),
            text_color=ACCENT
        ).pack(
            anchor="w",
            padx=24,
            pady=(2, 0)
        )

        # default active
        self.set_active("Dashboard")

    # =====================================================
    # CLICK
    # =====================================================
    def on_click(self, view, label):

        if hasattr(self.master, "set_view"):

            self.master.set_view(view)

        self.set_active(label)

    # =====================================================
    # ACTIVE STYLE
    # =====================================================
    def set_active(self, label):

        for name, btn in self.buttons.items():

            if name == label:

                btn.configure(
                    fg_color=NEON_PURPLE,
                    hover_color=NEON_MAGENTA,
                    text_color="#FFFFFF",
                    border_color=ACCENT,
                    border_width=2
                )

                self.active_button = btn

            else:

                btn.configure(
                    fg_color=GLASS_BG,
                    hover_color=GLASS_BG_HOVER,
                    text_color=TEXT,
                    border_color=GLASS_BORDER,
                    border_width=1
                )
