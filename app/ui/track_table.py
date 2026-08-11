"""
DJ AI OS — Track Table (Pro DJ style)

Clean zebra-stripe table, RED selected row, energy bars.
Rekordbox/Serato inspired — high contrast, club-proof.
"""

import customtkinter as ctk
from tkinter import ttk

from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, GREEN, AMBER, BLUE_BRIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM, F_BODY, F_BODY_BOLD, F_META,
    R_SM,
)

try:
    import windnd
except Exception:
    windnd = None


class TrackTable(ctk.CTkFrame):

    def __init__(self, parent, on_select=None, on_double_click=None, on_right_click_action=None):
        super().__init__(parent, fg_color=SURFACE, corner_radius=R_SM)
        self.configure(border_width=1, border_color=BORDER)

        self.on_select = on_select
        self.on_double_click = on_double_click
        self.on_right_click_action = on_right_click_action
        self.tracks_by_item = {}
        self.tracks = []
        self.sort_column = None
        self.sort_reverse = False

        # =================================================
        # STYLE — Pro DJ
        # =================================================
        style = ttk.Style()
        style.theme_use("default")

        style.configure(
            "Treeview",
            background=BG,
            foreground=TEXT_PRIMARY,
            fieldbackground=BG,
            borderwidth=0,
            rowheight=32,
            font=F_BODY,
        )

        style.configure(
            "Treeview.Heading",
            background=SURFACE_RAISED,
            foreground=TEXT_SECONDARY,
            borderwidth=0,
            font=F_META,
            padding=(8, 6),
        )

        style.map(
            "Treeview",
            background=[("selected", "#2A1520")],
            foreground=[("selected", RED)],
        )

        # =================================================
        # TABLE
        # =================================================
        self.tree = ttk.Treeview(
            self,
            columns=(
                "name", "genre", "role", "bpm", "key",
                "quality", "energy", "ear", "heart", "mix", "archive",
            ),
            show="headings",
            selectmode="browse",
        )

        # =================================================
        # HEADERS
        # =================================================
        self.header_labels = {
            "name": "TRACK",
            "genre": "GENRE",
            "role": "ROLE",
            "bpm": "BPM",
            "key": "KEY",
            "quality": "QUALITY",
            "energy": "ENERGY",
            "ear": "AI EAR",
            "heart": "HEART",
            "mix": "MIX",
            "archive": "ARCHIVE",
        }

        for column, label in self.header_labels.items():
            self.tree.heading(
                column, text=label,
                command=lambda c=column: self.sort_by(c),
            )

        # =================================================
        # COLUMNS
        # =================================================
        self.tree.column("name",   width=420, minwidth=280, stretch=True, anchor="w")
        self.tree.column("genre",  width=140, minwidth=120, stretch=False, anchor="w")
        self.tree.column("role",   width=100, minwidth=90,  stretch=False, anchor="center")
        self.tree.column("bpm",    width=70,  minwidth=70,  stretch=False, anchor="center")
        self.tree.column("key",    width=60,  minwidth=60,  stretch=False, anchor="center")
        self.tree.column("quality",width=120, minwidth=100, stretch=False, anchor="center")
        self.tree.column("energy", width=90,  minwidth=80,  stretch=False, anchor="center")
        self.tree.column("ear",    width=70,  minwidth=70,  stretch=False, anchor="center")
        self.tree.column("heart",  width=70,  minwidth=70,  stretch=False, anchor="center")
        self.tree.column("mix",    width=120, minwidth=100, stretch=False, anchor="center")
        self.tree.column("archive",width=90,  minwidth=80,  stretch=False, anchor="center")

        # =================================================
        # ROW COLORS
        # =================================================
        self.tree.tag_configure("evenrow", background=BG)
        self.tree.tag_configure("oddrow", background=SURFACE)

        # =================================================
        # SCROLLBAR
        # =================================================
        self.scrollbar = ctk.CTkScrollbar(self, command=self.tree.yview, width=8,
                                          button_color=SURFACE_RAISED, button_hover_color=BORDER)
        self.x_scrollbar = ctk.CTkScrollbar(self, orientation="horizontal", command=self.tree.xview,
                                            width=8, button_color=SURFACE_RAISED, button_hover_color=BORDER)

        self.tree.configure(yscrollcommand=self.scrollbar.set, xscrollcommand=self.x_scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=(4, 0))
        self.scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=(4, 0))
        self.x_scrollbar.pack(side="bottom", fill="x", padx=4, pady=(0, 4))

        # =================================================
        # INTERNAL
        # =================================================
        self.row_count = 0
        self.tree.bind("<<TreeviewSelect>>", self.handle_select)
        self.tree.bind("<Double-1>", self.handle_double_click)
        self.tree.bind("<Button-3>", self.handle_right_click)
        self.tree.bind("<Shift-MouseWheel>", self.handle_horizontal_scroll)

    def enable_drag_drop(self, callback):
        if windnd is None:
            return
        for widget in (self, self.tree):
            try:
                windnd.hook_dropfiles(widget, func=callback)
            except Exception:
                pass

    def clean_name(self, name):
        if not name:
            return "UNKNOWN"
        name = name.replace("_", " ")
        if len(name) > 55:
            name = name[:55] + "..."
        return name

    def add_track(self, track):
        self.tracks.append(track)
        if self.sort_column:
            self.tracks.sort(key=lambda t: self.sort_value(t, self.sort_column), reverse=self.sort_reverse)
            self.redraw()
            return
        self.insert_track(track)

    def set_tracks(self, tracks):
        self.clear()
        self.tracks = list(tracks)
        if self.sort_column:
            self.tracks.sort(key=lambda t: self.sort_value(t, self.sort_column), reverse=self.sort_reverse)
        self.redraw()

    def insert_track(self, track):
        name = self.clean_name(track.get("name", "UNKNOWN"))
        genre = track.get("genre", "-")
        role = track.get("role", "-")
        bpm = track.get("bpm", "-")
        key = track.get("key", track.get("camelot", "-"))
        quality = track.get("quality", "-")

        energy = track.get("energy", 0)
        energy_text = f"{'█' * int(energy * 5)}{'░' * (5 - int(energy * 5))} {energy:.0%}"

        ear = round(float(track.get("ai_ear_score", 0) or 0), 2)
        heart = round(float(track.get("heart_score", 0) or 0), 2)
        mix = track.get("mix_strategy", "-")
        archive = track.get("archive_status", "-")

        tag = "evenrow" if self.row_count % 2 == 0 else "oddrow"

        item = self.tree.insert(
            "", "end",
            values=(name, genre, role, bpm, key, quality, energy_text, ear, heart, mix, archive),
            tags=(tag,),
        )
        self.tracks_by_item[item] = track
        self.row_count += 1

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tracks_by_item = {}
        self.tracks = []
        self.row_count = 0

    def redraw(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tracks_by_item = {}
        self.row_count = 0
        for track in self.tracks:
            self.insert_track(track)

    def sort_by(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self.tracks.sort(key=lambda t: self.sort_value(t, column), reverse=self.sort_reverse)
        self.update_headings()
        self.redraw()

    def sort_value(self, track, column):
        numeric_columns = {"bpm", "energy", "ear", "heart"}
        if column in numeric_columns:
            try:
                if column == "ear":
                    return float(track.get("ai_ear_score", 0) or 0)
                if column == "heart":
                    return float(track.get("heart_score", 0) or 0)
                return float(track.get(column, 0) or 0)
            except (TypeError, ValueError):
                return 0

        value_map = {
            "name": track.get("name", ""),
            "genre": track.get("genre", ""),
            "role": track.get("role", ""),
            "key": track.get("key", track.get("camelot", "")),
            "quality": track.get("quality", ""),
            "mix": track.get("mix_strategy", ""),
            "archive": track.get("archive_status", ""),
        }
        return str(value_map.get(column, "")).lower()

    def update_headings(self):
        for column, label in self.header_labels.items():
            suffix = ""
            if column == self.sort_column:
                suffix = " ▼" if self.sort_reverse else " ▲"
            self.tree.heading(column, text=f"{label}{suffix}", command=lambda c=column: self.sort_by(c))

    def handle_select(self, _event):
        if not self.on_select:
            return
        selected = self.tree.selection()
        if not selected:
            return
        track = self.tracks_by_item.get(selected[0])
        if track:
            self.on_select(track)

    def handle_double_click(self, _event):
        selected = self.tree.selection()
        if not selected:
            return
        track = self.tracks_by_item.get(selected[0])
        if not track:
            return
        if self.on_double_click:
            self.on_double_click(track)
        elif self.on_select:
            self.on_select(track)

    def handle_right_click(self, _event):
        selected = self.tree.selection()
        if not selected:
            return
        track = self.tracks_by_item.get(selected[0])
        if not track:
            return

        import tkinter as tk
        menu = tk.Menu(self.tree, tearoff=0,
                       bg="#14141E", fg="#F0F0F5",
                       activebackground="#E63946", activeforeground="#FFFFFF",
                       font=("Segoe UI", 11))

        menu.add_command(label="CAL (Play)", command=lambda: self._do_action("play", track))
        menu.add_command(label="DECK A'YA YUKLE", command=lambda: self._do_action("load_a", track))
        menu.add_command(label="DECK B'YE YUKLE", command=lambda: self._do_action("load_b", track))
        menu.add_separator()
        menu.add_command(label="SET'E EKLE", command=lambda: self._do_action("add_set", track))
        menu.add_command(label="BILGI GOSTER", command=lambda: self._do_action("info", track))

        try:
            menu.tk_popup(self.tree.winfo_pointerx(), self.tree.winfo_pointery())
        finally:
            menu.grab_release()

    def _do_action(self, action, track):
        if self.on_right_click_action:
            self.on_right_click_action(action, track)
        elif action == "play" and self.on_select:
            self.on_select(track)

    def handle_horizontal_scroll(self, event):
        direction = -1 if event.delta > 0 else 1
        self.tree.xview_scroll(direction, "units")
        return "break"
