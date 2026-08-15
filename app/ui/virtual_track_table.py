"""
Virtualized Track Table — Canvas-based list for 100k+ tracks.

Features:
- Virtualized rendering (only visible rows drawn)
- Smooth scrolling with mouse wheel
- Column sorting
- Double-click to play, right-click context menu
- Selection support (single/multi)
- Custom row rendering with waveform preview
- Theme-aware (neon/glassmorphism)
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Optional, Callable, List, Dict, Any
import math

from app.ui.theme import *
from app.ui.glass import safe_alpha


class VirtualizedTrackTable(ctk.CTkFrame):
    """
    High-performance virtualized track table.

    Usage:
        table = VirtualizedTrackTable(
            parent,
            columns=["#", "Title", "Artist", "BPM", "Key", "Duration", "Genre"],
            on_select=callback,
            on_double_click=play_callback,
            on_right_click=context_menu_callback
        )
        table.pack(fill="both", expand=True)
        table.set_tracks(track_list)
    """

    def __init__(
        self,
        parent,
        columns: Optional[List[str]] = None,
        on_select: Optional[Callable[[Dict], None]] = None,
        on_double_click: Optional[Callable[[Dict], None]] = None,
        on_right_click: Optional[Callable[[Dict, int, int], None]] = None,
        row_height: int = 36,
        **kwargs
    ):
        # Default columns
        if columns is None:
            columns = ["#", "Title", "Artist", "BPM", "Key", "Duration", "Genre", "Energy"]

        self.columns = columns
        self.column_widths = self._default_column_widths()
        self.on_select = on_select
        self.on_double_click = on_double_click
        self.on_right_click = on_right_click
        self.row_height = row_height

        # Data
        self._all_tracks: List[Dict] = []
        self._filtered_tracks: List[Dict] = []
        self._visible_indices: List[int] = []
        self._selected_idx: Optional[int] = None
        self._hover_idx: Optional[int] = None

        # Sorting
        self._sort_column: Optional[int] = None
        self._sort_reverse = False

        # Scroll
        self._scroll_y = 0
        self._scroll_x = 0
        self._scroll_target = 0
        self._animating = False

        # Column resizing
        self._resizing_col: Optional[int] = None
        self._resize_start_x = 0
        self._resize_start_width = 0

        # Initialize UI
        super().__init__(parent, fg_color=PANEL, corner_radius=8, **kwargs)
        self.configure(border_width=1, border_color=GLASS_BORDER)

        self._build_ui()
        self._bind_events()

    def _default_column_widths(self) -> List[int]:
        """Default column widths in pixels."""
        defaults = {
            "#": 50,
            "Title": 280,
            "Artist": 180,
            "BPM": 70,
            "Key": 60,
            "Camelot": 80,
            "Duration": 80,
            "Genre": 120,
            "Energy": 70,
            "Rating": 60,
            "Role": 110,
            "Quality": 110,
            "Ear": 70,
            "Heart": 70,
            "Mix": 120,
            "Archive": 100,
        }
        return [defaults.get(col, 120) for col in self.columns]

    def _total_width(self) -> int:
        """Sum of all column widths (the canvas content width)."""
        return sum(self.column_widths)

    @staticmethod
    def _cell_text(track: Dict, col: str) -> str:
        """Render one cell's text for a given column name."""
        col_l = col.lower()
        if col == "#":
            return ""
        if col == "Title":
            return str(track.get("name", track.get("title", "Unknown")))
        if col == "Artist":
            return str(track.get("artist", "Unknown"))
        if col == "BPM":
            return f"{track.get('bpm', 0):.0f}" if track.get("bpm") else "—"
        if col in ("Key", "Camelot"):
            return str(track.get("camelot", track.get("key", "—")))
        if col == "Duration":
            secs = track.get("duration", 0)
            if not secs:
                return "—"
            return f"{int(secs // 60)}:{int(secs % 60):02d}"
        if col == "Genre":
            return str(track.get("genre", track.get("parent_genre", "—")))
        if col == "Energy":
            energy = track.get("energy", 0)
            if not energy:
                return "—"
            bars = int(energy * 5)
            return f"{'█' * bars}{'░' * (5 - bars)} {energy:.0%}"
        if col == "Ear":
            v = track.get("ai_ear_score", 0)
            return f"{float(v or 0):.2f}"
        if col == "Heart":
            v = track.get("heart_score", 0)
            return f"{float(v or 0):.2f}"
        # Role / Quality / Mix / Archive / custom columns fall through here
        return str(track.get(col_l, track.get(col, "—")))

    @staticmethod
    def _sort_value(track: Dict, col: str):
        """Return a sortable value for a column name."""
        col_l = col.lower()
        if col == "Title":
            return str(track.get("name", track.get("title", ""))).lower()
        if col == "Artist":
            return str(track.get("artist", "")).lower()
        if col == "Key" or col == "Camelot":
            return str(track.get("camelot", track.get("key", ""))).lower()
        if col == "Ear":
            return float(track.get("ai_ear_score", 0) or 0)
        if col == "Heart":
            return float(track.get("heart_score", 0) or 0)
        if col == "Energy":
            return float(track.get("energy", 0) or 0)
        if col == "Duration":
            return float(track.get("duration", 0) or 0)
        if col == "BPM":
            return float(track.get("bpm", 0) or 0)
        val = track.get(col_l, track.get(col, ""))
        if isinstance(val, (int, float)):
            return val
        return str(val).lower()

    def _build_ui(self):
        """Build the canvas-based UI."""
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color=SURFACE_RAISED, height=40, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        self.header_canvas = tk.Canvas(
            self.header_frame,
            height=40,
            bg=SURFACE_RAISED,
            highlightthickness=0,
        )
        self.header_canvas.pack(fill="x")

        # Main canvas with scrollbar
        canvas_frame = ctk.CTkFrame(self, fg_color="transparent")
        canvas_frame.pack(fill="both", expand=True)

        # Scrollbars (native tk — CTkScrollbar._draw calls update_idletasks
        # reentrantly and can hang boot with an infinite event storm)
        self.v_scrollbar = tk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=self._on_scrollbar,
            width=12,
            bg=GLASS_BG,
            troughcolor=BG,
            activebackground=SURFACE_RAISED,
            highlightthickness=0,
            relief="flat",
        )
        self.v_scrollbar.pack(side="right", fill="y")

        self.h_scrollbar = tk.Scrollbar(
            canvas_frame,
            orient="horizontal",
            command=self._on_h_scrollbar,
            width=12,
            bg=GLASS_BG,
            troughcolor=BG,
            activebackground=SURFACE_RAISED,
            highlightthickness=0,
            relief="flat",
        )
        self.h_scrollbar.pack(side="bottom", fill="x")

        # Canvas
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=GLASS_BG,
            highlightthickness=0,
            yscrollcommand=self._on_canvas_scroll,
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        # Draw initial
        self._draw_header()
        self._draw_rows()

    def _bind_events(self):
        """Bind mouse/keyboard events."""
        # Canvas events
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Leave>", self._on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # Linux
        self.canvas.bind("<Button-5>", self._on_mousewheel)  # Linux

        # Header events
        self.header_canvas.bind("<Button-1>", self._on_header_click)
        self.header_canvas.bind("<B1-Motion>", self._on_header_drag)
        self.header_canvas.bind("<ButtonRelease-1>", self._on_header_release)
        self.header_canvas.bind("<Motion>", self._on_header_motion)

        # Keyboard
        self.canvas.bind("<Up>", self._on_key_up)
        self.canvas.bind("<Down>", self._on_key_down)
        self.canvas.bind("<Return>", self._on_key_enter)
        self.canvas.focus_set()

    # ============================================================
    # PUBLIC API
    # ============================================================

    def set_tracks(self, tracks: List[Dict]):
        """Set all tracks and rebuild."""
        self._all_tracks = tracks
        self._apply_filter_and_sort()
        self._update_scrollbar()
        self._draw_rows()

    def add_track(self, track: Dict):
        """Add a single track."""
        self._all_tracks.append(track)
        self._apply_filter_and_sort()
        self._update_scrollbar()
        self._draw_rows()

    def remove_track(self, track_id: str) -> bool:
        """Remove track by ID/path."""
        for i, t in enumerate(self._all_tracks):
            if t.get("id") == track_id or t.get("path") == track_id:
                self._all_tracks.pop(i)
                self._apply_filter_and_sort()
                self._update_scrollbar()
                self._draw_rows()
                return True
        return False

    def clear(self):
        """Clear all tracks."""
        self._all_tracks = []
        self._filtered_tracks = []
        self._selected_idx = None
        self._update_scrollbar()
        self._draw_rows()

    def set_filter(self, filter_fn: Callable[[Dict], bool]):
        """Set filter function and re-apply."""
        self._filter_fn = filter_fn
        self._apply_filter_and_sort()
        self._update_scrollbar()
        self._draw_rows()

    def sort_by_column(self, col_idx: int):
        """Sort by column index."""
        if self._sort_column == col_idx:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col_idx
            self._sort_reverse = False
        self._apply_filter_and_sort()
        self._draw_header()
        self._draw_rows()

    def get_selected_track(self) -> Optional[Dict]:
        """Get currently selected track."""
        if self._selected_idx is not None and 0 <= self._selected_idx < len(self._filtered_tracks):
            return self._filtered_tracks[self._selected_idx]
        return None

    def get_selected_tracks(self) -> List[Dict]:
        """Get all selected tracks (for multi-select)."""
        # Currently single select only
        track = self.get_selected_track()
        return [track] if track else []

    def select_index(self, idx: int):
        """Programmatically select row by index."""
        if 0 <= idx < len(self._filtered_tracks):
            self._selected_idx = idx
            self._ensure_visible(idx)
            self._draw_rows()
            if self.on_select:
                self.on_select(self._filtered_tracks[idx])

    def scroll_to_index(self, idx: int):
        """Scroll to make index visible."""
        self._ensure_visible(idx)

    # ============================================================
    # INTERNAL: Filtering & Sorting
    # ============================================================

    def _apply_filter_and_sort(self):
        """Apply filter and sort to get visible tracks."""
        # Filter
        if hasattr(self, "_filter_fn") and self._filter_fn:
            self._filtered_tracks = [t for t in self._all_tracks if self._filter_fn(t)]
        else:
            self._filtered_tracks = list(self._all_tracks)

        # Sort
        if self._sort_column is not None:
            col_name = self.columns[self._sort_column]
            reverse = self._sort_reverse
            self._filtered_tracks.sort(
                key=lambda track: self._sort_value(track, col_name),
                reverse=reverse,
            )

    # ============================================================
    # DRAWING
    # ============================================================

    def _draw_header(self):
        """Draw column headers."""
        c = self.header_canvas
        c.delete("all")

        width = c.winfo_width()
        if width <= 1:
            return

        x = -self._scroll_x
        for i, (col, col_width) in enumerate(zip(self.columns, self.column_widths)):
            # Clamp to canvas width
            if x >= width:
                break

            actual_width = min(col_width, width - x)

            # Column background
            c.create_rectangle(
                x, 0, x + actual_width, 40,
                fill=SURFACE_RAISED,
                outline=GLASS_BORDER if i > 0 else "",
            )

            # Sort indicator
            sort_indicator = ""
            if self._sort_column == i:
                sort_indicator = " ▼" if self._sort_reverse else " ▲"

            # Column text
            c.create_text(
                x + 12, 20,
                text=col + sort_indicator,
                fill=ACCENT,
                font=F_BODY_BOLD,
                anchor="w",
            )

            # Resize handle (right edge)
            if i < len(self.columns) - 1:
                handle_x = x + actual_width
                c.create_line(
                    handle_x, 8, handle_x, 32,
                    fill=GLASS_BORDER,
                    width=1,
                    tags=(f"resize_{i}",)
                )

            x += actual_width

        self._update_h_scrollbar()

    def _draw_rows(self):
        """Draw visible rows only (virtualized)."""
        c = self.canvas
        c.delete("all")

        canvas_height = c.winfo_height()
        if canvas_height <= 1:
            canvas_height = 400

        canvas_width = c.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800

        # Calculate visible range
        first_visible = max(0, self._scroll_y // self.row_height)
        last_visible = min(
            len(self._filtered_tracks),
            first_visible + (canvas_height // self.row_height) + 2
        )

        self._visible_indices = list(range(first_visible, last_visible))

        # Draw each visible row
        y = first_visible * self.row_height - self._scroll_y

        for idx in self._visible_indices:
            track = self._filtered_tracks[idx]
            self._draw_row(c, track, idx, y, canvas_width)
            y += self.row_height

        # Update scroll region — ONLY when the region actually changed.
        # Tk re-evaluates the canvas view on every `-scrollregion` configure and
        # fires yscrollcommand (→ _on_canvas_scroll → _on_scrollbar → _draw_rows),
        # so setting an identical region every draw starts an infinite
        # yscrollcommand ↔ _draw_rows ping-pong that wedges update()/mainloop.
        total_height = len(self._filtered_tracks) * self.row_height
        if c.cget("scrollregion") != f"0 0 {canvas_width} {total_height}":
            c.configure(scrollregion=(0, 0, canvas_width, total_height))

    def _draw_row(self, canvas: tk.Canvas, track: Dict, idx: int, y: float, width: float):
        """Draw a single row."""
        # Row background
        is_selected = (idx == self._selected_idx)
        is_hover = (idx == self._hover_idx)

        if is_selected:
            bg_color = SELECTED
            text_color = "white"
        elif is_hover:
            bg_color = HOVER
            text_color = TEXT
        elif idx % 2 == 0:
            bg_color = GLASS_BG
            text_color = TEXT
        else:
            bg_color = safe_alpha(GLASS_BG, 0.5)
            text_color = MUTED

        canvas.create_rectangle(
            0, y, width, y + self.row_height,
            fill=bg_color,
            outline="",
        )

        # Selection highlight
        if is_selected:
            canvas.create_rectangle(
                2, y + 2, 4, y + self.row_height - 2,
                fill=ACCENT,
                outline="",
            )

        # Row number
        x = -self._scroll_x
        canvas.create_text(
            x + 12, y + self.row_height // 2,
            text=str(idx + 1),
            fill=text_color,
            font=F_BODY,
            anchor="w",
        )

        # Columns — rendered per-column via _cell_text so any DJ-specific
        # column (role, quality, ear, heart, mix, archive) displays correctly.
        x = self.column_widths[0] - self._scroll_x  # Skip "#" column
        for i, col_width in enumerate(self.column_widths[1:]):
            if x >= width:
                break
            actual_width = min(col_width, width - x)
            col_name = self.columns[i + 1]
            text = self._cell_text(track, col_name)
            canvas.create_text(
                x + 10, y + self.row_height // 2,
                text=str(text)[:50],
                fill=text_color,
                font=F_BODY,
                anchor="w",
            )
            x += actual_width

    def _format_duration(self, seconds: float) -> str:
        """Format duration as MM:SS."""
        if not seconds:
            return "—"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    # ============================================================
    # EVENT HANDLERS
    # ============================================================

    def _on_canvas_configure(self, event):
        """Canvas resized - redraw."""
        self._draw_header()
        self._draw_rows()
        self._update_scrollbar()
        self._update_h_scrollbar()

    def _on_canvas_click(self, event):
        """Handle click on row."""
        idx = self._get_row_at_y(event.y)
        if idx is not None:
            self._selected_idx = idx
            self._draw_rows()
            if self.on_select:
                self.on_select(self._filtered_tracks[idx])
        else:
            # Clicked empty space - deselect
            self._selected_idx = None
            self._draw_rows()

        self.canvas.focus_set()

    def _on_canvas_double_click(self, event):
        """Handle double-click - play track."""
        idx = self._get_row_at_y(event.y)
        if idx is not None and self.on_double_click:
            self.on_double_click(self._filtered_tracks[idx])

    def _on_canvas_right_click(self, event):
        """Handle right-click - context menu."""
        idx = self._get_row_at_y(event.y)
        if idx is not None and self.on_right_click:
            track = self._filtered_tracks[idx]
            self._selected_idx = idx
            self._draw_rows()
            # Convert to screen coordinates
            x = self.canvas.winfo_pointerx()
            y = self.canvas.winfo_pointery()
            self.on_right_click(track, x, y)

    def _on_canvas_motion(self, event):
        """Handle mouse hover."""
        idx = self._get_row_at_y(event.y)
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._draw_rows()

    def _on_canvas_leave(self, event):
        """Mouse left canvas."""
        self._hover_idx = None
        self._draw_rows()

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.num == 4:  # Linux up
            delta = -1
        elif event.num == 5:  # Linux down
            delta = 1
        else:
            delta = -event.delta // 120  # Windows/Mac

        self._scroll_y = max(0, self._scroll_y + delta * self.row_height)
        max_scroll = max(0, len(self._filtered_tracks) * self.row_height - self.canvas.winfo_height())
        self._scroll_y = min(self._scroll_y, max_scroll)

        self.canvas.yview_moveto(self._scroll_y / max(1, max_scroll))
        self._draw_rows()

    def _on_scrollbar(self, *args):
        """Scrollbar command."""
        if args[0] == "moveto":
            self._scroll_y = float(args[1]) * max(1, len(self._filtered_tracks) * self.row_height - self.canvas.winfo_height())
        elif args[0] == "scroll":
            self._scroll_y += int(args[1]) * self.row_height * int(args[2])

        max_scroll = max(0, len(self._filtered_tracks) * self.row_height - self.canvas.winfo_height())
        self._scroll_y = max(0, min(self._scroll_y, max_scroll))
        self._draw_rows()

    def _on_canvas_scroll(self, *args):
        """Canvas scroll command (from scrollbar)."""
        self._on_scrollbar(*args)

    def _on_h_scrollbar(self, *args):
        """Horizontal scrollbar command."""
        max_scroll = max(0, self._total_width() - self.canvas.winfo_width())
        if args[0] == "moveto":
            self._scroll_x = float(args[1]) * max_scroll
        elif args[0] == "scroll":
            self._scroll_x += int(args[1]) * 20
        self._scroll_x = max(0, min(self._scroll_x, max_scroll))
        self._draw_header()
        self._draw_rows()

    def _update_h_scrollbar(self):
        """Update horizontal scrollbar position/visibility."""
        width = self.canvas.winfo_width()
        if width <= 1:
            return
        total = self._total_width()
        if total <= width:
            self.h_scrollbar.set(0, 1)
        else:
            self.h_scrollbar.set(
                self._scroll_x / total,
                (self._scroll_x + width) / total,
            )

    def _update_scrollbar(self):
        """Update scrollbar position/visibility."""
        canvas_height = self.canvas.winfo_height()
        if canvas_height <= 1:
            return

        total_height = len(self._filtered_tracks) * self.row_height
        if total_height <= canvas_height:
            self.v_scrollbar.set(0, 1)
        else:
            self.v_scrollbar.set(
                self._scroll_y / total_height,
                (self._scroll_y + canvas_height) / total_height
            )

    def _get_row_at_y(self, y: int) -> Optional[int]:
        """Get row index at canvas Y coordinate."""
        canvas_y = y + self._scroll_y
        idx = canvas_y // self.row_height
        if 0 <= idx < len(self._filtered_tracks):
            return int(idx)
        return None

    def _ensure_visible(self, idx: int):
        """Ensure row index is visible."""
        canvas_height = self.canvas.winfo_height()
        if canvas_height <= 1:
            return

        row_top = idx * self.row_height
        row_bottom = row_top + self.row_height

        if row_top < self._scroll_y:
            self._scroll_y = row_top
        elif row_bottom > self._scroll_y + canvas_height:
            self._scroll_y = row_bottom - canvas_height

        max_scroll = max(0, len(self._filtered_tracks) * self.row_height - canvas_height)
        self._scroll_y = max(0, min(self._scroll_y, max_scroll))
        self._draw_rows()

    # ============================================================
    # HEADER EVENTS (Column resize, sort)
    # ============================================================

    def _on_header_click(self, event):
        """Handle header click (sort or start resize)."""
        x = event.x
        col_idx = self._get_col_at_x(x)

        if col_idx is None:
            return

        # Check if clicking resize handle
        col_right = sum(self.column_widths[:col_idx + 1])
        if abs(x - col_right) < 6 and col_idx < len(self.columns) - 1:
            # Start resize
            self._resizing_col = col_idx
            self._resize_start_x = x
            self._resize_start_width = self.column_widths[col_idx]
            self.header_canvas.config(cursor="sb_h_double_arrow")
        else:
            # Sort by column
            self.sort_by_column(col_idx)

    def _on_header_drag(self, event):
        """Handle header drag (resize column)."""
        if self._resizing_col is not None:
            delta = event.x - self._resize_start_x
            new_width = max(40, self._resize_start_width + delta)
            self.column_widths[self._resizing_col] = new_width
            self._draw_header()

    def _on_header_release(self, event):
        """Handle header release."""
        self._resizing_col = None
        self.header_canvas.config(cursor="")

    def _on_header_motion(self, event):
        """Header mouse motion - show resize cursor."""
        x = event.x
        col_idx = self._get_col_at_x(x)
        if col_idx is not None:
            col_right = sum(self.column_widths[:col_idx + 1])
            if abs(x - col_right) < 6 and col_idx < len(self.columns) - 1:
                self.header_canvas.config(cursor="sb_h_double_arrow")
                return
        self.header_canvas.config(cursor="")

    def _get_col_at_x(self, x: int) -> Optional[int]:
        """Get column index at X coordinate."""
        x += self._scroll_x
        col_x = 0
        for i, width in enumerate(self.column_widths):
            if col_x <= x < col_x + width:
                return i
            col_x += width
        return None

    # ============================================================
    # KEYBOARD NAVIGATION
    # ============================================================

    def _on_key_up(self, event):
        """Up arrow - select previous."""
        if self._selected_idx is not None and self._selected_idx > 0:
            self.select_index(self._selected_idx - 1)

    def _on_key_down(self, event):
        """Down arrow - select next."""
        if self._selected_idx is not None and self._selected_idx < len(self._filtered_tracks) - 1:
            self.select_index(self._selected_idx + 1)
        elif self._selected_idx is None and self._filtered_tracks:
            self.select_index(0)

    def _on_key_enter(self, event):
        """Enter - double-click action."""
        if self._selected_idx is not None and self.on_double_click:
            self.on_double_click(self._filtered_tracks[self._selected_idx])


# ============================================================
# BACKWARD COMPATIBILITY WRAPPER
# ============================================================

class TrackTable(ctk.CTkFrame):
    """
    Backward-compatible wrapper using VirtualizedTrackTable.
    Maintains same API as old Treeview-based TrackTable.
    """

    # Default columns mirror the original Treeview TrackTable so this is a
    # true drop-in for the library/set builder/archive views.
    DEFAULT_COLUMNS = ["#", "Title", "Genre", "Role", "BPM", "Key", "Quality",
                       "Energy", "Ear", "Heart", "Mix", "Archive"]

    def __init__(self, parent, on_select=None, on_double_click=None,
                 on_right_click_action=None, columns=None):
        super().__init__(parent, fg_color=PANEL, corner_radius=12)
        self.configure(border_width=1, border_color=GLASS_BORDER)

        self.virtualized = VirtualizedTrackTable(
            self,
            columns=columns if columns is not None else self.DEFAULT_COLUMNS,
            on_select=on_select,
            on_double_click=on_double_click,
            on_right_click=lambda track, x, y: on_right_click_action and on_right_click_action(track),
        )
        self.virtualized.pack(fill="both", expand=True)

        # Expose commonly used methods
        self.tracks_by_item = {}
        self.tracks = []
        self.sort_column = None
        self.sort_reverse = False

    def set_tracks(self, tracks):
        self.tracks = tracks
        self.virtualized.set_tracks(tracks)

    def add_track(self, track):
        self.tracks.append(track)
        self.virtualized.add_track(track)

    def clear(self):
        self.tracks = []
        self.virtualized.clear()

    def get_selected_track(self):
        return self.virtualized.get_selected_track()


# ============================================================
# EXPORTS
# ============================================================

__all__ = ["VirtualizedTrackTable", "TrackTable"]