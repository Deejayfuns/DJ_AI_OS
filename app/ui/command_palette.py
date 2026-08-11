import customtkinter as ctk
from tkinter import StringVar

from app.ui.theme import ACCENT, BACKGROUND, F_H2, F_BODY_BOLD, F_META, MUTED, PANEL, SURFACE_RAISED, TEXT, SELECTED
from app.core.i18n import t


class CommandPalette(ctk.CTkToplevel):

    def __init__(self, parent, commands):
        super().__init__(parent)

        self.title("DJ AI OS Command Palette")
        self.geometry("620x520")
        self.resizable(False, False)
        self.parent = parent
        self.commands = commands
        self.filtered_commands = list(commands)
        self.selected_index = 0

        self.search_var = StringVar(value="")

        self.build()
        self.bind_shortcuts()
        self.refresh()

        self.after(80, self.search.focus_set)

    def build(self):

        self.configure(fg_color=BACKGROUND)

        ctk.CTkLabel(
            self,
            text=t("palette.title"),
            font=F_H2,
            text_color=ACCENT
        ).pack(anchor="w", padx=18, pady=(18, 6))

        self.search = ctk.CTkEntry(
            self,
            textvariable=self.search_var,
            placeholder_text=t("palette.search_placeholder"),
            height=38
        )
        self.search.pack(fill="x", padx=18, pady=(0, 12))
        self.search_var.trace_add("write", lambda *_args: self.refresh())

        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=PANEL,
            corner_radius=8
        )
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text=t("palette.footer_hint"),
            text_color=MUTED
        ).pack(anchor="w", padx=18, pady=(0, 14))

    def bind_shortcuts(self):

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self.run_selected())
        self.bind("<Down>", lambda _e: self.move_selection(1))
        self.bind("<Up>", lambda _e: self.move_selection(-1))
        self.bind("<KP_Down>", lambda _e: self.move_selection(1))
        self.bind("<KP_Up>", lambda _e: self.move_selection(-1))

    def refresh(self):

        query = self.search_var.get().strip().lower()

        self.filtered_commands = [
            command
            for command in self.commands
            if self.matches(command, query)
        ]
        if self.selected_index >= len(self.filtered_commands):
            self.selected_index = 0

        for child in self.list_frame.winfo_children():
            child.destroy()

        if not self.filtered_commands:
            ctk.CTkLabel(
                self.list_frame,
                text=t("palette.not_found"),
                text_color="#8A8F98"
            ).pack(anchor="w", padx=12, pady=12)
            return

        for idx, command in enumerate(self.filtered_commands):
            self.add_command_row(command, idx)

    def matches(self, command, query):

        if not query:
            return True

        haystack = " ".join([
            command.get("title", ""),
            command.get("shortcut", ""),
            command.get("keywords", ""),
        ]).lower()

        return query in haystack

    def add_command_row(self, command, index):

        selected = index == self.selected_index

        row = ctk.CTkFrame(
            self.list_frame,
            fg_color=SURFACE_RAISED if not selected else SELECTED,
            corner_radius=8,
            border_width=1 if selected else 0,
            border_color=ACCENT if selected else SURFACE_RAISED,
        )
        row.pack(fill="x", padx=8, pady=5)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            left,
            text=command.get("title", "Untitled"),
            font=F_BODY_BOLD,
            text_color=TEXT,
            anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=command.get("subtitle", ""),
            text_color=MUTED,
            anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        shortcut = command.get("shortcut", "")

        if shortcut:
            ctk.CTkLabel(
                row,
                text=shortcut,
                text_color=ACCENT,
                width=90
            ).pack(side="left", padx=8)

        ctk.CTkButton(
            row,
            text=t("palette.run"),
            width=72,
            command=lambda c=command: self.run_command(c)
        ).pack(side="right", padx=10, pady=10)

        # click row to select + run
        row.bind("<Button-1>", lambda _e, c=command: self.run_command(c))
        left.bind("<Button-1>", lambda _e, c=command: self.run_command(c))

    def move_selection(self, delta):

        if not self.filtered_commands:
            return "break"

        n = len(self.filtered_commands)
        self.selected_index = (self.selected_index + delta) % n
        self.refresh()

        # keep the highlighted row visible
        try:
            child = self.list_frame.winfo_children()[self.selected_index]
            self.list_frame._parent_canvas.yview_moveto(
                self.selected_index / max(1, len(self.filtered_commands))
            )
        except Exception:
            pass

        return "break"

    def run_selected(self):

        if self.filtered_commands:
            self.run_command(self.filtered_commands[self.selected_index])

    def run_command(self, command):

        action = command.get("action")

        if action:
            action()

        self.destroy()
