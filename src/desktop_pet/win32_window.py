"""Windows helpers that turn the Kivy window into a transparent desktop pet."""

from __future__ import annotations

import os


def setup_desktop_window() -> bool:
    """Stretch the window over the desktop, hide it from the taskbar and make
    black pixels click-through via a layered colour key.

    Returns ``True`` when the native calls succeeded.  Failures are ignored so
    the app still runs (just without the desktop-integration tricks).
    """
    if os.name != "nt":
        return False
    try:
        import win32api
        import win32con
        import win32gui

        # Prefer our own window over whatever happens to be focused (which
        # could be the terminal that launched the app).
        hwnd = win32gui.FindWindow(None, "Desktop Pet") or win32gui.GetForegroundWindow()
        desktop = win32gui.GetDesktopWindow()
        left, top, right, bottom = win32gui.GetWindowRect(desktop)
        win32gui.MoveWindow(hwnd, left, top, right - left, bottom - top, True)

        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            style | win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW,
        )
        win32gui.SetLayeredWindowAttributes(
            hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY
        )
        return True
    except Exception:
        return False
