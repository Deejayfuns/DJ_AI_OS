import customtkinter as ctk
from tkinter import StringVar

from app.ui.theme import ACCENT, CARD, PANEL
from app.ui.track_table import TrackTable
from app.ui.views.base import ViewBase


class GenreReviewView(ViewBase):

    def build(self, parent):

        win = self.win

        win.make_section_title(
            parent,
            "Genre Review",
            "AI'nin emin olmadigi parcalari DJ onayi ile ogret."
        )

        controls = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=8)
        controls.pack(fill="x", pady=(0, 10))

        win.review_genre = StringVar(value="AFRO HOUSE")
        win.review_parent = StringVar(value="HOUSE")
        win.review_role = StringVar(value="WARMUP")

        ctk.CTkEntry(
            controls,
            textvariable=win.review_genre,
            placeholder_text="Genre",
            width=160
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkEntry(
            controls,
            textvariable=win.review_parent,
            placeholder_text="Parent",
            width=140
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkEntry(
            controls,
            textvariable=win.review_role,
            placeholder_text="Role",
            width=140
        ).pack(side="left", padx=8, pady=10)

        ctk.CTkButton(
            controls,
            text="APPROVE SELECTED",
            command=win.approve_selected_genre
        ).pack(side="left", padx=8, pady=10)

        tracks = win.genre_review.needs_review(win.library or win.saved_tracks)
        win.build_filter_bar(parent, tracks)

        table_frame = ctk.CTkFrame(parent, fg_color=PANEL)
        table_frame.pack(fill="both", expand=True)
        win.table = TrackTable(table_frame, on_select=win.on_track_selected)
        win.table.pack(fill="both", expand=True, padx=6, pady=6)
        win.populate_table(tracks)
