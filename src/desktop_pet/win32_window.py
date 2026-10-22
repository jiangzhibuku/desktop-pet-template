"""Windows helpers that turn the Kivy window into a transparent desktop pet."""

from __future__ import annotations

import os
import threading

HOTKEY_ID = 0xB001
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_Q = 0x51


def register_emergency_exit(callback) -> None:
    """Register Ctrl+Alt+Shift+Q as a global escape hatch.

    The hotkey works even when the layered full-screen window is incorrectly
    rendered as an opaque black surface and blocks normal mouse input.
    """
    if os.name != "nt":
        return

    def run() -> None:
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            mods = MOD_CONTROL | MOD_ALT | MOD_SHIFT | MOD_NOREPEAT
            if not user32.RegisterHotKey(None, HOTKEY_ID, mods, VK_Q):
                return
            try:
                msg = wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                    if msg.message == 0x0312 and msg.wParam == HOTKEY_ID:
                        callback()
                        break
            finally:
                user32.UnregisterHotKey(None, HOTKEY_ID)
        except Exception:
            pass

    threading.Thread(target=run, name="pet-hotkey", daemon=True).start()


def position_window(width: int, height: int, margin: int = 30) -> None:
    """Place the normal window near the bottom-right corner (safe mode)."""
    if os.name != "nt":
        return
    try:
        import win32api
        import win32gui

        hwnd = win32gui.FindWindow(None, "Desktop Pet") or win32gui.GetForegroundWindow()
        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        x = max(0, screen_w - width - margin)
        y = max(0, screen_h - height - margin)
        win32gui.MoveWindow(hwnd, x, y, width, height, True)
    except Exception:
        pass


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
