"""
DJ AI OS — CustomTkinter reentrancy guard

CustomTkinter's CTkScrollbar._draw() ends with `self._canvas.update_idletasks()`
(ctk_scrollbar.py:161). That call drains every pending idle callback while the
widget is mid-draw — including the *same* scrollbar's <Configure>/set handlers
and any canvas scrollregion changes the draw itself triggers. Under a forced
layout pass (widget construction, an explicit update()/update_idletasks())
this re-enters _draw → update_idletasks → _draw … an infinite event storm that
hangs boot with no traceback (CPU pegged, window frozen).

A simple reentrancy *guard* is not enough: skipping the nested _draw leaves the
scrollbar dirty, so Tk keeps scheduling a new idle redraw, which is guarded
again → livelock. The correct fix is to remove the forced `update_idletasks()`
from _draw altogether. Drawing still happens — super()._draw() paints the
canvas immediately — the window just doesn't synchronously drain the whole idle
queue in the middle of painting. Renders settle on the next mainloop tick.

Safe to import anywhere; idempotent.
"""

import sys

import tkinter

_patched = False


def apply_ctk_patch():
    """Replace CTkScrollbar._draw with a version that skips the
    self._canvas.update_idletasks() call (the infinite-storm source)."""
    global _patched
    if _patched:
        return
    try:
        from customtkinter.windows.widgets.ctk_scrollbar import CTkScrollbar
    except Exception:
        return

    # Save the original for reference only; we re-implement _draw below with
    # the final update_idletasks() stripped.
    def _safe_draw(self, no_color_updates=False):
        # Same body as upstream CTkScrollbar._draw (ctk_scrollbar.py:128),
        # minus the final self._canvas.update_idletasks() — the infinite-storm
        # source. Keep the body byte-for-byte in sync with the installed
        # customtkinter version: draw_rounded_scrollbar takes 7 args and there
        # is NO self._border_color attribute.
        super(type(self), self)._draw(no_color_updates)  # CTkBaseClass._draw

        corrected_start_value, corrected_end_value = \
            self._get_scrollbar_values_for_minimum_pixel_size()
        requires_recoloring = self._draw_engine.draw_rounded_scrollbar(
            self._apply_widget_scaling(self._current_width),
            self._apply_widget_scaling(self._current_height),
            self._apply_widget_scaling(self._corner_radius),
            self._apply_widget_scaling(self._border_spacing),
            corrected_start_value,
            corrected_end_value,
            self._orientation,
        )

        if no_color_updates is False or requires_recoloring:
            if self._hover_state is True:
                self._canvas.itemconfig("scrollbar_parts",
                                        fill=self._apply_appearance_mode(self._button_hover_color),
                                        outline=self._apply_appearance_mode(self._button_hover_color))
            else:
                self._canvas.itemconfig("scrollbar_parts",
                                        fill=self._apply_appearance_mode(self._button_color),
                                        outline=self._apply_appearance_mode(self._button_color))

            if self._fg_color == "transparent":
                self._canvas.configure(bg=self._apply_appearance_mode(self._bg_color))
                self._canvas.itemconfig("border_parts",
                                        fill=self._apply_appearance_mode(self._bg_color),
                                        outline=self._apply_appearance_mode(self._bg_color))
            else:
                self._canvas.configure(bg=self._apply_appearance_mode(self._fg_color))
                self._canvas.itemconfig("border_parts",
                                        fill=self._apply_appearance_mode(self._fg_color),
                                        outline=self._apply_appearance_mode(self._fg_color))

    CTkScrollbar._draw = _safe_draw

    # ================================================================
    # 2) CTkTk._windows_set_titlebar_color — drop the synchronous
    #    super().update() drain (ctk_tk.py:283).
    #
    # On Windows, the FIRST call to mainloop() runs
    # _windows_set_titlebar_color() before the window exists; its
    # "window doesn't exist yet" branch calls super().update(), which
    # drains the ENTIRE event queue synchronously. Any self-rearming
    # after() chains (HUD animation, ui_consumer) re-arm faster than a
    # thrashing box can process them, so that update() never returns and
    # boot hangs before the main window appears. The later deiconify()
    # (ctk_tk.py:310, guarded by `or True`) shows the window anyway, so
    # the drain is pure overhead. Replacing it with a no-op keeps the
    # DWM titlebar recoloring and skips the infinite drain.
    # ================================================================
    try:
        from customtkinter.windows.ctk_tk import CTk
    except Exception:
        CTk = None

    if CTk is not None:
        _orig_titlebar = CTk._windows_set_titlebar_color

        def _safe_titlebar_color(self, color_mode):
            # Same intent as upstream, but the pre-window update() drain is
            # skipped entirely (no update/update_idletasks). The DWM recolor
            # still runs, and mainloop()'s deiconify() shows the window.
            if sys.platform.startswith("win") and not self._deactivate_windows_window_header_manipulation:
                if self._window_exists:
                    self._state_before_windows_set_titlebar_color = self.state()
                    if self._state_before_windows_set_titlebar_color != "iconic" and \
                            self._state_before_windows_set_titlebar_color != "withdrawn":
                        self.focused_widget_before_widthdraw = self.focus_get()
                        tkinter.Tk.withdraw(self)
                else:
                    # Window doesn't exist yet — nothing to hide or refresh.
                    # Upstream calls super().withdraw() (tkinter.Tk.withdraw,
                    # which does NOT set _withdraw_called_before_window_exists)
                    # then super().update(). That update() drains the entire
                    # event queue, and on this box the first layout pass keeps
                    # refilling it (endless storm) — so skip the drain. Using
                    # tkinter.Tk.withdraw (not CTk.withdraw) keeps the
                    # "before_window_exists" flag clear so mainloop()'s
                    # deiconify() runs and the window actually shows.
                    self.focused_widget_before_widthdraw = self.focus_get()
                    tkinter.Tk.withdraw(self)

                if color_mode.lower() == "dark":
                    value = 1
                elif color_mode.lower() == "light":
                    value = 0
                else:
                    return

                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
                    if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                            ctypes.byref(ctypes.c_int(value)),
                            ctypes.sizeof(ctypes.c_int(value))) != 0:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                            ctypes.byref(ctypes.c_int(value)),
                            ctypes.sizeof(ctypes.c_int(value)))
                except Exception as err:
                    print(err)

                if self._window_exists or True:
                    if self._state_before_windows_set_titlebar_color == "normal":
                        self.deiconify()
                    elif self._state_before_windows_set_titlebar_color == "iconic":
                        self.iconify()
                    elif self._state_before_windows_set_titlebar_color == "zoomed":
                        self.state("zoomed")
                    else:
                        self.state(self._state_before_windows_set_titlebar_color)

                if self.focused_widget_before_widthdraw is not None:
                    self.after(1, self.focused_widget_before_widthdraw.focus)

        CTk._windows_set_titlebar_color = _safe_titlebar_color

    _patched = True
