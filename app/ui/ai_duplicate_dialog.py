import customtkinter as ctk


class AIDuplicateDialog(ctk.CTkToplevel):

    def __init__(self, parent, group, callback):
        super().__init__(parent)

        self.title("Muzik Doktoru - Duplicate Kontrol")
        self.geometry("680x420")
        self.resizable(False, False)

        self.group = group
        self.callback = callback
        self.bind_shortcuts()

        best = group.get("best", {})
        dup = group.get("duplicate", {})
        recommendation = group.get("recommendation", "ASK_DJ")

        text = f"""
MEVCUT KAYIT:
{best.get('name', best.get('path', 'UNKNOWN'))}
Bitrate: {best.get('bitrate', 0)} kbps
Boyut: {best.get('file_size', 0)} bytes

YENI BULUNAN:
{dup.get('name', 'UNKNOWN')}
Bitrate: {dup.get('bitrate', 0)} kbps
Boyut: {dup.get('file_size', 0)} bytes

AI ONERISI:
{recommendation}

Ne yapmak istersin?
"""

        ctk.CTkLabel(
            self,
            text="MUZIK DOKTORU - DUPLICATE KONTROL",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        ctk.CTkLabel(
            self,
            text=text,
            justify="left"
        ).pack(padx=20, pady=10, anchor="w")

        btns = ctk.CTkFrame(self)
        btns.pack(pady=20)

        ctk.CTkButton(
            btns,
            text="ESKIYI SIL [1]",
            fg_color="red",
            command=lambda: self.action("delete_old")
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btns,
            text="DUPLICATE KLASORU [2]",
            fg_color="orange",
            command=lambda: self.action("move_duplicate")
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btns,
            text="IKISINI TUT [3]",
            fg_color="green",
            command=lambda: self.action("keep_both")
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btns,
            text="AI ONERISINI SEC [Enter]",
            fg_color="gray",
            command=lambda: self.action("use_ai_recommendation")
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            self,
            text="Kisayollar: 1 eskiyi sil | 2 duplicate klasoru | 3 ikisini tut | Enter AI onerisi | Esc kapat",
            text_color="#888888"
        ).pack(pady=(0, 10))

    def bind_shortcuts(self):

        self.bind("1", lambda _e: self.action("delete_old"))
        self.bind("2", lambda _e: self.action("move_duplicate"))
        self.bind("3", lambda _e: self.action("keep_both"))
        self.bind("<Return>", lambda _e: self.action("use_ai_recommendation"))
        self.bind("<Escape>", lambda _e: self.destroy())

    def action(self, choice):

        self.callback(choice, self.group)
        self.destroy()
