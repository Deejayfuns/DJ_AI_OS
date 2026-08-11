"""
DJ AI OS — Song Vault Panel (Premium Module)

Futuristic acquisition console. Feed it a track name or a txt playlist
and it researches the web, downloads the best available source and
converts it to lossless WAV or 320 kbps MP3 — all from one panel.

Designed for content you have the right to use.
"""

import os
import threading

import customtkinter as ctk
from tkinter import filedialog

from app.ai.song_vault import SongVault, FORMAT_SPECS
from app.core.i18n import t
from app.ui.theme import (
    BG, SURFACE, SURFACE_RAISED, BORDER, RED, RED_HOVER, GREEN, AMBER,
    BLUE_BRIGHT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    F_H3, F_BODY, F_BODY_BOLD, F_META, F_MONO,
)


class SongVaultPanel(ctk.CTkFrame):
    """Premium music acquisition console."""

    def __init__(self, master, win=None):
        super().__init__(master, fg_color=SURFACE, corner_radius=8,
                         border_width=1, border_color=BORDER)
        self.win = win

        self.engine = SongVault(
            out_dir=os.path.join(os.getcwd(), "DJ_SONG_VAULT"),
            fmt="mp3_320",
        )

        self._queue = []          # pending query strings
        self._processing = False
        self._cancel = False
        self._row_labels = {}     # query -> status label widget

        self._build()

    # ============================================================
    # BUILD
    # ============================================================
    def _build(self):
        # ---- Header ----
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(header, text="SONG VAULT", font=F_H3,
                     text_color=RED).pack(side="left")
        ctk.CTkLabel(header, text="◆ PREMIUM", font=F_META,
                     text_color=AMBER, fg_color=BG, corner_radius=3,
                     padx=6, pady=2).pack(side="left", padx=8)
        ctk.CTkLabel(header, text="INTERNET ARSIV UZAYI",
                     font=F_META, text_color=TEXT_DIM).pack(side="left", padx=6)

        self.status_dot = ctk.CTkLabel(header, text="●", font=F_META,
                                       text_color=TEXT_DIM)
        self.status_dot.pack(side="right")
        self.status_label = ctk.CTkLabel(header, text="BEKLEMEDE",
                                         font=F_META, text_color=TEXT_DIM)
        self.status_label.pack(side="right", padx=4)

        # ---- Config row ----
        cfg = ctk.CTkFrame(self, fg_color=BG, corner_radius=6,
                           border_width=1, border_color=BORDER)
        cfg.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(cfg, text="FORMAT:", font=F_META,
                     text_color=TEXT_DIM).pack(side="left", padx=(10, 6))
        self.fmt_var = ctk.StringVar(value="mp3_320")
        self.fmt_combo = ctk.CTkComboBox(
            cfg, values=[k for k in FORMAT_SPECS],
            variable=self.fmt_var, width=150, height=26, font=F_META,
            command=self._on_format,
        )
        self.fmt_combo.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(cfg, text="HEDEF:", font=F_META,
                     text_color=TEXT_DIM).pack(side="left")
        self.dir_label = ctk.CTkLabel(cfg, text=self.engine.out_dir,
                                      font=F_MONO, text_color=BLUE_BRIGHT,
                                      anchor="w")
        self.dir_label.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkButton(cfg, text="KONUM", width=60, height=24, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY,
                      command=self._pick_dir).pack(side="left", padx=(4, 6))
        ctk.CTkButton(cfg, text="KLASOR", width=60, height=24, font=F_META,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY,
                      command=self._open_dir).pack(side="left", padx=(0, 10))

        # ---- Single query ----
        qrow = ctk.CTkFrame(self, fg_color="transparent")
        qrow.pack(fill="x", padx=14, pady=(0, 6))
        self.query_entry = ctk.CTkEntry(
            qrow, placeholder_text="Ornek: Freddie Gibbs - Palmolive (veya tek sarki adi)",
            font=F_BODY, fg_color=BG, border_color=BORDER,
        )
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.query_entry.bind("<Return>", lambda e: self._enqueue_query())
        ctk.CTkButton(qrow, text="ARA & INDIR", width=110, height=34,
                      fg_color=RED, hover_color=RED_HOVER, text_color="#FFF",
                      font=F_BODY_BOLD, command=self._enqueue_query).pack(side="left")

        # ---- Playlist row ----
        prow = ctk.CTkFrame(self, fg_color="transparent")
        prow.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkButton(prow, text="TXT PLAYLIST YUKLE", width=150, height=28,
                      fg_color=SURFACE_RAISED, hover_color=BORDER,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._load_playlist).pack(side="left", padx=(0, 8))
        self.queue_label = ctk.CTkLabel(prow, text="Kuyruk: 0",
                                        font=F_META, text_color=TEXT_DIM)
        self.queue_label.pack(side="left")
        ctk.CTkButton(prow, text="DURDUR", width=70, height=28,
                      fg_color=SURFACE_RAISED, hover_color=RED,
                      text_color=TEXT_SECONDARY, font=F_META,
                      command=self._stop).pack(side="right")

        # ---- Progress ----
        self.progress = ctk.CTkProgressBar(self, height=6, fg_color=BG,
                                           progress_color=RED)
        self.progress.pack(fill="x", padx=14, pady=(2, 2))
        self.progress.set(0)

        # ---- Results ----
        ctk.CTkLabel(self, text="INDIRME RAPORU", font=F_META,
                     text_color=TEXT_DIM).pack(anchor="w", padx=14, pady=(6, 2))
        self.results = ctk.CTkScrollableFrame(self, fg_color=BG, corner_radius=6)
        self.results.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    # ============================================================
    # FORMAT / DIR
    # ============================================================
    def _on_format(self, value):
        self.engine.set_format(value)
        self.set_status("FORMAT: %s" % FORMAT_SPECS[value]["label"], TEXT_DIM)

    def _pick_dir(self):
        path = filedialog.askdirectory(initialdir=self.engine.out_dir)
        if path:
            self.engine.set_output_dir(path)
            self.dir_label.configure(text=self.engine.out_dir)

    def _open_dir(self):
        try:
            os.startfile(self.engine.out_dir)  # Windows
        except Exception:
            try:
                import subprocess
                subprocess.Popen(["explorer", self.engine.out_dir])
            except Exception:
                pass

    # ============================================================
    # QUEUE
    # ============================================================
    def _enqueue_query(self):
        q = self.query_entry.get().strip()
        if not q:
            return
        self.query_entry.delete(0, "end")
        self._add_to_queue([q])

    def _load_playlist(self):
        path = filedialog.askopenfilename(
            filetypes=[("Playlist", "*.txt"), ("All", "*.*")])
        if not path:
            return
        try:
            queries = self.engine.parse_playlist(path)
        except Exception as exc:
            self.set_status("Playlist hatasi: %s" % exc, RED)
            return
        if not queries:
            self.set_status("Playlist bos veya '#' yorum satirlarindan olusuyor.", AMBER)
            return
        self.set_status("%d parca yuklendi" % len(queries), GREEN)
        self._add_to_queue(queries)

    def _add_to_queue(self, queries):
        for q in queries:
            if q not in self._row_labels:
                self._queue.append(q)
                self._add_row(q)
        self.queue_label.configure(text="Kuyruk: %d" % len(self._queue))
        self._kick_worker()

    def _kick_worker(self):
        if not self._processing:
            self._processing = True
            self._cancel = False
            threading.Thread(target=self._worker, daemon=True).start()

    def _stop(self):
        self._cancel = True

    # ============================================================
    # WORKER (background thread)
    # ============================================================
    def _worker(self):
        while self._queue and not self._cancel:
            q = self._queue.pop(0)
            self._ui(lambda: self._mark(q, "ARANIYOR...", AMBER))

            def progress(d):
                st = d.get("status") or {}
                stage = st.get("stage")
                if stage == "downloading":
                    self._ui(lambda: self._mark(
                        q, "INDIRILIYOR %s  %s" % (st.get("percent", ""),
                                                   st.get("speed", "")), BLUE_BRIGHT))
                    pct = d.get("percent")
                elif stage == "converting":
                    self._ui(lambda: self._mark(q, "DONUSTURULUYOR...", AMBER))

            r = self.engine.search_and_download(q, progress=progress)

            def _done():
                if r.get("ok"):
                    size = r.get("size", 0)
                    mb = size / (1024 * 1024)
                    tag = "MEVCUT (SKIP)" if r.get("skipped") else "HAZIR"
                    self._mark(q, "%s  %.1f MB" % (tag, mb), GREEN, r.get("path"))
                else:
                    self._mark(q, "HATA: %s" % r.get("error", ""), RED)
            self._ui(_done)

        self._processing = False
        self._ui(self._finish)

    def _finish(self):
        self.progress.set(0)
        self.set_status("TAMAM (%d)" % len(self._row_labels), GREEN)
        self.status_dot.configure(text_color=GREEN)
        self.queue_label.configure(text="Kuyruk: 0")

    def _ui(self, fn):
        try:
            self.after(0, fn)
        except Exception:
            pass

    # ============================================================
    # ROWS
    # ============================================================
    def _add_row(self, query):
        row = ctk.CTkFrame(self.results, fg_color=SURFACE, corner_radius=4)
        row.pack(fill="x", padx=2, pady=2)
        ctk.CTkLabel(row, text=query, font=F_BODY, text_color=TEXT_PRIMARY,
                     wraplength=420, justify="left").pack(side="left", padx=8, pady=6)
        st = ctk.CTkLabel(row, text="SIRADA", font=F_META,
                          text_color=TEXT_DIM, anchor="e")
        st.pack(side="right", padx=8, pady=6)
        self._row_labels[query] = st

    def _mark(self, query, status_text, color, path=None):
        lbl = self._row_labels.get(query)
        if lbl and lbl.winfo_exists():
            lbl.configure(text=status_text, text_color=color)
        self.set_status(status_text, color)
        self.status_dot.configure(text_color=color)

    def set_status(self, text, color=TEXT_DIM):
        try:
            self.status_label.configure(text=text, text_color=color)
        except Exception:
            pass
