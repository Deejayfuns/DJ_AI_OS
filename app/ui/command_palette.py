import customtkinter as ctk
from tkinter import StringVar


class CommandPalette(ctk.CTkToplevel):

    def __init__(self, parent, commands):
        super().__init__(parent)

        self.title("DJ AI OS Command Palette")
        self.geometry("620x520")
        self.resizable(False, False)
        self.parent = parent
        self.commands = commands
        self.filtered_commands = list(commands)

        self.search_var = StringVar(value="")

        self.build()
        self.bind_shortcuts()
        self.refresh()

        self.after(80, self.search.focus_set)

    def build(self):

        self.configure(fg_color="#0B0D10")

        ctk.CTkLabel(
            self,
            text="COMMAND PALETTE",
            font=("Segoe UI", 18, "bold"),
            text_color="#00FFA3"
        ).pack(anchor="w", padx=18, pady=(18, 6))

        self.search = ctk.CTkEntry(
            self,
            textvariable=self.search_var,
            placeholder_text="Komut ara: set, deck, doktor, export...",
            height=38
        )
        self.search.pack(fill="x", padx=18, pady=(0, 12))
        self.search_var.trace_add("write", lambda *_args: self.refresh())

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#111315",
            corner_radius=8
        )
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text="Enter ilk komutu calistirir | Esc kapatir",
            text_color="#8A8F98"
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def bind_shortcuts(self):

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.run_first())

    def refresh(self):

        query = self.search_var.get().strip().lower()

        self.filtered_commands = [
            command
            for command in self.commands
            if self.matches(command, query)
        ]

        for child in self.list_frame.winfo_children():
            child.destroy()

        if not self.filtered_commands:
            ctk.CTkLabel(
                self.list_frame,
                text="Komut bulunamadi.",
                text_color="#8A8F98"
            ).pack(anchor="w", padx=12, pady=12)
            return

        for command in self.filtered_commands:
            self.add_command_row(command)

    def matches(self, command, query):

        if not query:
            return True

        haystack = " ".join([
            command.get("title", ""),
            command.get("shortcut", ""),
            command.get("keywords", ""),
        ]).lower()

        return query in haystack

    def add_command_row(self, command):

        row = ctk.CTkFrame(self.list_frame, fg_color="#161A1F", corner_radius=8)
        row.pack(fill="x", padx=8, pady=5)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            left,
            text=command.get("title", "Untitled"),
            font=("Segoe UI", 13, "bold"),
            text_color="#F1F4F8",
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=command.get("subtitle", ""),
            text_color="#8A8F98",
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        shortcut = command.get("shortcut", "")

        if shortcut:
            ctk.CTkLabel(
                row,
                text=shortcut,
                text_color="#00FFA3",
                width=90
            ).pack(side="left", padx=8)

        ctk.CTkButton(
            row,
            text="RUN",
            width=72,
            command=lambda c=command: self.run_command(c)
        ).pack(side="right", padx=10, pady=10)

    def run_first(self):

        if self.filtered_commands:
            self.run_command(self.filtered_commands[0])

    def run_command(self, command):

        action = command.get("action")

        if action:
            action()

        self.destroy()
