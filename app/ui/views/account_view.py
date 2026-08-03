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
        ).pack(anchor="w", padx=14, pady=(2, 12))

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

        right = ctk.CTkScrollableFrame(body, fg_color=PANEL, corner_radius=8)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            right,
            text="COMMERCIAL PLANS",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT
        ).pack(anchor="w", padx=12, pady=(12, 6))

        for plan_name, info in win.license.entitlements.pricing_table().items():
            card = ctk.CTkFrame(right, fg_color=CARD, corner_radius=8)
            card.pack(fill="x", padx=8, pady=6)

            price = info.get("monthly_usd")
            price_text = "Custom" if price is None else f"${price}/mo"

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
