import customtkinter as ctk
from tkinter import StringVar

from app.ui.theme import ACCENT, CARD, MUTED, PANEL, SUCCESS, TEXT
from app.ui.views.base import ViewBase


class AccountView(ViewBase):

    def build(self, parent):

        win = self.win

        win.make_section_title(
            parent,
            "Account",
            "Online lisans, abonelik, cloud arşiv ve server AI yetkileri."
        )

        plan = win.license.get_plan()
        entitlements = plan.get("entitlements", {})
        account = win.commercial_api.account_status(plan, entitlements)

        top = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        top.pack(fill="x", pady=(0, 12))

        activation = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        activation.pack(fill="x", pady=(0, 12))

        win.account_email = StringVar(value="")
        win.account_license_key = StringVar(value="")

        ctk.CTkEntry(
            activation,
            textvariable=win.account_email,
            placeholder_text="Email",
            width=260
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkEntry(
            activation,
            textvariable=win.account_license_key,
            placeholder_text="License key e.g. ARCHIVE-12345678",
            width=300
        ).pack(side="left", padx=8, pady=12)

        ctk.CTkButton(
            activation,
            text="ACTIVATE LICENSE",
            command=win.activate_license_from_ui
        ).pack(side="left", padx=8, pady=12)

        # Yönet (Stripe Customer Portal)
        ctk.CTkButton(
            activation,
            text="YÖNET / BILLING",
            width=140,
            command=win.open_customer_portal
        ).pack(side="left", padx=8, pady=12)

        # --- OFFLINE LICENSE LOAD ---
        offline_frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        offline_frame.pack(fill="x", pady=(8, 12))

        ctk.CTkLabel(
            offline_frame,
            text="OFFLINE LİSANS YÜKLE",
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            offline_frame,
            text="Vendor'dan aldığınız imzalı license.key (JSON) içeriğini yapıştırın veya dosya seçin.",
            text_color=MUTED,
            wraplength=800
        ).pack(anchor="w", padx=12, pady=(0, 8))

        win.offline_license_text = ctk.CTkTextbox(offline_frame, height=80, width=700)
        win.offline_license_text.pack(anchor="w", padx=12, pady=(0, 8))

        btn_row = ctk.CTkFrame(offline_frame, fg_color="transparent")
        btn_row.pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row,
            text="DOSYA SEÇ",
            width=120,
            command=lambda: win.load_offline_license_from_file()
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="YÜKLE",
            width=100,
            command=lambda: win.load_offline_license_from_text(
                win.offline_license_text.get("1.0", "end").strip()
            )
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="TEMİZLE",
            width=80,
            command=lambda: win.offline_license_text.delete("1.0", "end")
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=f"PLAN: {plan.get('plan')} | LICENSED: {'YES' if plan.get('licensed') else 'NO'}",
            font=("Segoe UI", 18, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", padx=14, pady=(12, 0))

        ctk.CTkLabel(
            top,
            text=(
                f"Server mode: {account.get('mode')} | "
                f"Updates active: {'YES' if entitlements.get('updates_active') else 'NO'}"
            ),
            text_color=MUTED
        ).pack(anchor="w", padx=14, pady=(2, 0))

        # Çevrimdışı imzalı lisans üretimi için makine kimliği (vendor'a verilecek)
        machine_row = ctk.CTkFrame(top, fg_color="transparent")
        machine_row.pack(fill="x", padx=14, pady=(8, 0))

        machine_id = win.license.machine_id_display()
        ctk.CTkLabel(
            machine_row,
            text=f"MACHINE ID: {machine_id[:32]}…",
            text_color=MUTED
        ).pack(side="left", anchor="w")

        def copy_machine_id():
            try:
                win.clipboard_clear()
                win.clipboard_append(machine_id)
                win.set_status("MACHINE ID kopyalandı.")
            except Exception:
                pass

        ctk.CTkButton(
            machine_row,
            text="COPY",
            width=64,
            height=22,
            command=copy_machine_id
        ).pack(side="left", padx=8)

        if not entitlements.get("updates_active"):
            ctk.CTkLabel(
                top,
                text="🔒 Güncellemeler aktif değil — lisansını yenile.",
                text_color="#f87171"
            ).pack(anchor="w", padx=14, pady=(6, 12))
        else:
            ctk.CTkLabel(
                top,
                text="Güncelleme: Settings → UPDATES bölümünden kontrol edebilirsin.",
                text_color=MUTED
            ).pack(anchor="w", padx=14, pady=(6, 12))

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True)

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            left,
            text="ENTITLEMENTS",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        for feature, enabled in entitlements.items():
            if feature in {"plan", "licensed"}:
                continue

            ctk.CTkLabel(
                left,
                text=f"{feature}: {'ON' if enabled else 'OFF'}",
                text_color=SUCCESS if enabled else MUTED
            ).pack(anchor="w", padx=12, pady=2)

        # =====================================================
        # PLAN KARŞILAŞTIRMA TABLOSU
        # =====================================================
        compare = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=8)
        compare.pack(side="left", fill="both", expand=True, padx=(8, 8))

        ctk.CTkLabel(
            compare,
            text="PAKET KARŞILAŞTIRMA",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        # Table header
        plans = ["DEMO", "PRO", "DJ_ARCHIVE", "STUDIO", "ENTERPRISE"]
        pricing = win.license.entitlements.pricing_table()

        header = ctk.CTkFrame(compare, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(
            header, text="Modül", width=150, anchor="w",
            font=("Segoe UI", 10, "bold"), text_color=TEXT
        ).pack(side="left", padx=4)
        for p in plans:
            price = pricing.get(p, {}).get("monthly_usd")
            price_text = "ÖZEL" if price is None else f"${price}"
            ctk.CTkLabel(
                header, text=f"{p}\n{price_text}", width=70,
                font=("Segoe UI", 8), text_color=MUTED
            ).pack(side="left", padx=2)

        # Module rows
        module_map = win.license.entitlements.module_plan_map()
        user_plan = plan.get("plan", "DEMO")

        module_order = [
            "Performance Dashboard", "Dashboard", "Müzik Doktoru (Analiz)",
            "Kütüphane", "Arşiv Koruyucu", "Set Oluşturucu", "Beat Studio",
            "Song Vault", "DJ Coach", "Kütüphane Haritası", "Astra Chat",
            "Deck Studio", "DJ Booth", "Canlı Performans", "Pioneer Link",
            "Akıllı Set", "DJ Profili", "Remix Lab", "Cloud Export",
            "Nöral Sentez", "Nöral Köprü",
        ]

        for module_name in module_order:
            required_plan = module_map.get(module_name, "DEMO")
            row = ctk.CTkFrame(compare, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=1)

            ctk.CTkLabel(
                row, text=module_name, width=150, anchor="w",
                font=("Segoe UI", 9), text_color=TEXT
            ).pack(side="left", padx=4)

            for p in plans:
                # OWNER_DEV has everything
                if user_plan == "OWNER_DEV":
                    is_open = True
                elif p == "DEMO":
                    is_open = (required_plan == "DEMO")
                else:
                    # In plan p, module is open if p's level >= required level
                    p_level = {"DEMO": 0, "PRO": 1, "DJ_ARCHIVE": 2, "STUDIO": 3, "ENTERPRISE": 4}
                    req_level = p_level.get(required_plan, 0)
                    is_open = p_level[p] >= req_level

                ctk.CTkLabel(
                    row, text="✓" if is_open else "—",
                    width=70, anchor="center",
                    font=("Segoe UI", 11, "bold"),
                    text_color=SUCCESS if is_open else "#444"
                ).pack(side="left", padx=2)

        # Upgrade buttons
        upgrade_frame = ctk.CTkFrame(compare, fg_color="transparent")
        upgrade_frame.pack(fill="x", padx=12, pady=(12, 12))

        ctk.CTkLabel(
            upgrade_frame,
            text="MEVCUT PLANIN: " + user_plan,
            font=("Segoe UI", 11, "bold"),
            text_color=ACCENT
        ).pack(anchor="w", pady=(0, 8))

        for plan_name, info in pricing.items():
            monthly = info.get("monthly_usd")
            yearly = info.get("yearly_usd")
            price_text = "Custom" if monthly is None else f"${monthly}/mo"
            yearly_text = "" if yearly is None else f"  |  ${yearly}/yıl"

            # Skip if user already on this or higher plan
            plan_levels = {"DEMO": 0, "PRO": 1, "DJ_ARCHIVE": 2, "STUDIO": 3, "ENTERPRISE": 4}
            user_level = plan_levels.get(user_plan, 0)
            this_level = plan_levels.get(plan_name, 0)
            if plan_name == "ENTERPRISE":
                this_level = 5
            if this_level <= user_level and plan_name not in ("OWNER_DEV",):
                continue

            card = ctk.CTkFrame(upgrade_frame, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", pady=3)

            ctk.CTkLabel(
                card,
                text=f"{plan_name} — {price_text}{yearly_text}",
                font=("Segoe UI", 12, "bold"),
                text_color=ACCENT
            ).pack(side="left", padx=12, pady=8)

            ctk.CTkButton(
                card,
                text="YÜKSELT",
                width=100,
                height=28,
                command=lambda p=plan_name: win.create_checkout_intent(p)
            ).pack(side="right", padx=12, pady=6)

        right = ctk.CTkScrollableFrame(body, fg_color=PANEL, corner_radius=8)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            right,
            text="PLAN DETAYLARI",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        for plan_name, info in win.license.entitlements.pricing_table().items():
            card = ctk.CTkFrame(right, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", padx=8, pady=6)

            monthly = info.get("monthly_usd")
            yearly = info.get("yearly_usd")
            price_text = "Custom" if monthly is None else f"${monthly}/mo"
            if yearly:
                price_text += f"  •  ${yearly}/yıl"

            ctk.CTkLabel(
                card,
                text=f"{plan_name} - {price_text}",
                font=("Segoe UI", 15, "bold"),
                text_color=ACCENT
            ).pack(anchor="w", padx=12, pady=(10, 0))

            ctk.CTkLabel(
                card,
                text=info.get("headline", ""),
                text_color=MUTED
            ).pack(anchor="w", padx=12, pady=(2, 8))

            ctk.CTkButton(
                card,
                text="CREATE CHECKOUT INTENT",
                command=lambda p=plan_name: win.create_checkout_intent(p)
            ).pack(anchor="w", padx=12, pady=(0, 12))
