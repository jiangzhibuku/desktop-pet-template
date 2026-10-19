"""Open the native Windows file picker without blocking Kivy.

Tk is created inside its own short-lived thread and destroyed immediately after
the dialog closes.  The selected path is delivered back to the Kivy thread via
``Clock.schedule_once``.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from kivy.clock import Clock


def pick_image(on_selected: Callable[[str], None]) -> None:
    def work() -> None:
        path = ""
        root = None
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            initial = Path.home() / "Pictures"
            if not initial.is_dir():
                initial = Path.home() / "Desktop"
            if not initial.is_dir():
                initial = Path.home()
            path = filedialog.askopenfilename(
                parent=root,
                initialdir=str(initial),
                title="选择角色图片",
                filetypes=[
                    ("图片文件", "*.png *.jpg *.jpeg *.webp"),
                    ("PNG", "*.png"),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("WebP", "*.webp"),
                    ("所有文件", "*.*"),
                ],
            )
        except Exception:
            path = ""
        finally:
            if root is not None:
                try:
                    root.destroy()
                except Exception:
                    pass
        Clock.schedule_once(lambda _dt: on_selected(path), 0)

    threading.Thread(target=work, name="pet-image-picker", daemon=True).start()
