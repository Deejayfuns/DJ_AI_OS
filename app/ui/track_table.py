import customtkinter as ctk
from tkinter import ttk

from app.ui.theme import *

try:
    import windnd
except Exception:
    windnd = None


class TrackTable(ctk.CTkFrame):

    def __init__(self, parent, on_select=None):

        super().__init__(
            parent,
            fg_color=PANEL,
            corner_radius=12
        )

        self.configure(
            border_width=1,
            border_color=GLASS_BORDER
        )

        self.on_select = on_select
        self.tracks_by_item = {}
        self.tracks = []
        self.sort_column = None
        self.sort_reverse = False

        # =================================================
        # STYLE
        # =================================================
        style = ttk.Style()

        style.theme_use("default")

        # =================================================
        # TREE STYLE
        # =================================================
        style.configure(
            "Treeview",
            background=GLASS_BG,
            foreground=TEXT,
            fieldbackground=GLASS_BG,
            borderwidth=0,
            rowheight=34,
            font=F_BODY,
        )

        # =================================================
        # HEADER STYLE
        # =================================================
        style.configure(
            "Treeview.Heading",
            background=SURFACE_RAISED,
            foreground=ACCENT,
            borderwidth=0,
            font=F_BODY_BOLD,
            padding=(10, 10)
        )

        style.map(
            "Treeview",
            background=[
                ("selected", SELECTED)
            ],
            foreground=[
                ("selected", "white")
            ]
        )

        # =================================================
        # TABLE
        # =================================================
        self.tree = ttk.Treeview(
            self,
            columns=(

                "name",

                "genre",

                "parent",

                "mood",

                "role",

                "bpm",

                "tempo",

                "key",

                "quality",

                "suggested",

                "research",

                "bitrate",

                "energy",

                "ear",

                "heart",

                "match",

                "mix"
            ),
            show="headings",
            selectmode="browse"
        )

        # =================================================
        # HEADERS
        # =================================================
        self.header_labels = {
            "name": "TRACK",
            "genre": "GENRE",
            "parent": "FAMILY",
            "mood": "MOOD",
            "role": "ROLE",
            "bpm": "BPM",
            "tempo": "TEMPO AI",
            "key": "KEY",
            "quality": "QUALITY",
            "suggested": "SUGGESTED FILE",
            "research": "RESEARCH",
            "bitrate": "BITRATE",
            "energy": "ENERGY",
            "ear": "AI EAR",
            "heart": "HEART",
            "match": "MATCH",
            "mix": "MIX",
        }

        for column, label in self.header_labels.items():
            self.tree.heading(
                column,
                text=label,
                command=lambda c=column: self.sort_by(c)
            )

        # =================================================
        # COLUMNS
        # =================================================
        self.tree.column(
            "name",
            width=520,
            minwidth=350,
            stretch=True,
            anchor="w"
        )

        self.tree.column(
            "genre",
            width=190,
            minwidth=170,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "parent",
            width=120,
            minwidth=110,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "mood",
            width=120,
            minwidth=100,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "role",
            width=120,
            minwidth=110,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "bpm",
            width=90,
            minwidth=90,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "tempo",
            width=130,
            minwidth=120,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "key",
            width=90,
            minwidth=90,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "quality",
            width=150,
            minwidth=130,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "suggested",
            width=260,
            minwidth=180,
            stretch=False,
            anchor="w"
        )

        self.tree.column(
            "research",
            width=120,
            minwidth=110,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "bitrate",
            width=110,
            minwidth=110,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "energy",
            width=110,
            minwidth=110,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "ear",
            width=100,
            minwidth=90,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "heart",
            width=100,
            minwidth=90,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "match",
            width=90,
            minwidth=80,
            stretch=False,
            anchor="center"
        )

        self.tree.column(
            "mix",
            width=150,
            minwidth=120,
            stretch=False,
            anchor="center"
        )

        # =================================================
        # ROW COLORS
        # =================================================
        self.tree.tag_configure(
            "oddrow",
            background=GLASS_BG_HOVER
        )

        self.tree.tag_configure(
            "evenrow",
            background=GLASS_BG
        )

        # =================================================
        # SCROLLBAR
        # =================================================
        self.scrollbar = ctk.CTkScrollbar(
            self,
            command=self.tree.yview
        )

        self.x_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=self.scrollbar.set,
            xscrollcommand=self.x_scrollbar.set
        )

        # =================================================
        # PACK
        # =================================================
        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(6, 0),
            pady=(6, 0)
        )

        self.scrollbar.pack(
            side="right",
            fill="y",
            padx=(0, 6),
            pady=(6, 0)
        )

        self.x_scrollbar.pack(
            side="bottom",
            fill="x",
            padx=6,
            pady=(0, 6)
        )

        # =================================================
        # INTERNAL
        # =================================================
        self.row_count = 0
        self.tree.bind("<<TreeviewSelect>>", self.handle_select)
        self.tree.bind("<Shift-MouseWheel>", self.handle_horizontal_scroll)

    def enable_drag_drop(self, callback):

        if windnd is None:
            return

        for widget in (self, self.tree):
            try:
                windnd.hook_dropfiles(widget, func=callback)
            except Exception:
                pass

    # =====================================================
    # CLEAN TRACK NAME
    # =====================================================
    def clean_name(self, name):

        if not name:
            return "UNKNOWN"

        name = name.replace("_", " ")

        if len(name) > 58:
            name = name[:58] + "..."

        return name

    # =====================================================
    # ADD TRACK
    # =====================================================
    def add_track(self, track):

        self.tracks.append(track)

        if self.sort_column:
            self.tracks.sort(
                key=lambda item: self.sort_value(item, self.sort_column),
                reverse=self.sort_reverse
            )
            self.redraw()
            return

        self.insert_track(track)

    def set_tracks(self, tracks):

        self.clear()

        self.tracks = list(tracks)

        if self.sort_column:
            self.tracks.sort(
                key=lambda item: self.sort_value(item, self.sort_column),
                reverse=self.sort_reverse
            )

        self.redraw()

    def insert_track(self, track):

        name = self.clean_name(
            track.get("name", "UNKNOWN")
        )

        genre = track.get(
            "genre",
            "-"
        )

        parent = track.get(
            "parent_genre",
            "-"
        )

        mood = track.get(
            "mood",
            "-"
        )

        role = track.get(
            "role",
            "-"
        )

        bpm = track.get(
            "bpm",
            "-"
        )

        key = track.get(
            "key",
            track.get("camelot", "-")
        )

        tempo = track.get("bpm_correction") or "UNCHANGED"
        try:
            tempo_confidence = float(track.get("tempo_confidence", 0) or 0)
        except (TypeError, ValueError):
            tempo_confidence = 0

        if tempo != "UNCHANGED":
            tempo_text = f"{tempo_confidence:.2f} FIX"
        else:
            tempo_text = f"{tempo_confidence:.2f} OK" if tempo_confidence else "OK"

        quality = track.get(
            "quality",
            "-"
        )

        suggested = self.clean_name(
            track.get("suggested_filename", "-")
        )

        research = track.get(
            "research_status",
            "-"
        )

        bitrate = track.get(
            "bitrate",
            0
        )

        bitrate_text = f"{bitrate} kbps"

        energy = round(
            track.get("energy", 0),
            2
        )

        mix = track.get(
            "mix_strategy",
            "-"
        )

        ear = round(
            float(track.get("ai_ear_score", 0) or 0),
            2
        )

        heart = round(
            float(track.get("heart_score", 0) or 0),
            2
        )

        match = track.get(
            "compatibility_grade",
            track.get("transition_score", "-")
        )

        # =================================================
        # ZEBRA ROWS
        # =================================================
        tag = (
            "evenrow"
            if self.row_count % 2 == 0
            else "oddrow"
        )

        item = self.tree.insert(
            "",
            "end",
            values=(

                name,

                genre,

                parent,

                mood,

                role,

                bpm,

                tempo_text,

                key,

                quality,

                suggested,

                research,

                bitrate_text,

                energy,

                ear,

                heart,

                match,

                mix
            ),
            tags=(tag,)
        )

        self.tracks_by_item[item] = track
        self.row_count += 1

    # =====================================================
    # CLEAR
    # =====================================================
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

        self.tracks.sort(
            key=lambda track: self.sort_value(track, column),
            reverse=self.sort_reverse
        )

        self.update_headings()
        self.redraw()

    def sort_value(self, track, column):

        numeric_columns = {
            "bpm",
            "bitrate",
            "energy",
            "match",
            "ear",
            "heart",
            "tempo"
        }

        if column in numeric_columns:
            try:
                if column == "match":
                    return float(track.get("transition_score", 0) or 0)

                if column == "ear":
                    return float(track.get("ai_ear_score", 0) or 0)

                if column == "heart":
                    return float(track.get("heart_score", 0) or 0)

                if column == "tempo":
                    return float(track.get("tempo_confidence", 0) or 0)

                return float(track.get(column, 0) or 0)
            except (TypeError, ValueError):
                return 0

        value_map = {
            "name": track.get("name", ""),
            "genre": track.get("genre", ""),
            "parent": track.get("parent_genre", ""),
            "mood": track.get("mood", ""),
            "role": track.get("role", ""),
            "key": track.get("key", track.get("camelot", "")),
            "tempo": track.get("bpm_correction", ""),
            "quality": track.get("quality", ""),
            "suggested": track.get("suggested_filename", ""),
            "research": track.get("research_status", ""),
            "mix": track.get("mix_strategy", ""),
            "match": track.get("compatibility_grade", ""),
            "ear": track.get("ai_ear_score", ""),
            "heart": track.get("heart_score", ""),
        }

        return str(value_map.get(column, "") or "").lower()

    def update_headings(self):

        for column, label in self.header_labels.items():
            suffix = ""

            if column == self.sort_column:
                suffix = " DESC" if self.sort_reverse else " ASC"

            self.tree.heading(
                column,
                text=f"{label}{suffix}",
                command=lambda c=column: self.sort_by(c)
            )

    def handle_select(self, _event):

        if not self.on_select:
            return

        selected = self.tree.selection()

        if not selected:
            return

        track = self.tracks_by_item.get(selected[0])

        if track:
            self.on_select(track)

    def handle_horizontal_scroll(self, event):

        direction = -1 if event.delta > 0 else 1
        self.tree.xview_scroll(direction, "units")

        return "break"
