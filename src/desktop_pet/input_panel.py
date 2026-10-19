"""A tiny always-on-top Tk input box and whitelist manager.

Kivy owns the main loop, so Tk runs in its own daemon thread.  Cross-thread
communication is limited to thread-safe Events and plain tuples; Tk widgets are
only touched from the Tk thread.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

PLACEHOLDER = "对她说点什么…"


class InputPanel:
    def __init__(
        self,
        *,
        on_submit: Callable[[str], None],
        get_apps: Callable[[], dict[str, str]],
        add_app: Callable[[str, str], str],
        remove_app: Callable[[str], str],
        on_hide: Callable[[], None] | None = None,
    ) -> None:
        self._on_submit = on_submit
        self._get_apps = get_apps
        self._add_app = add_app
        self._remove_app = remove_app
        self._on_hide = on_hide

        self._show_input = threading.Event()
        self._show_manage = threading.Event()
        self._hide_input = threading.Event()
        self._closing = threading.Event()
        self._lock = threading.Lock()
        self._anchor = (0.0, 0.0, 240.0, 300.0)
        self._started = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._run, name="pet-input", daemon=True)
        self._thread.start()

    def show_input(self) -> None:
        self.start()
        self._show_input.set()

    def hide_input(self) -> None:
        self._hide_input.set()

    def show_manager(self) -> None:
        self.start()
        self._show_manage.set()

    def set_anchor(self, x: float, y: float, width: float, height: float) -> None:
        with self._lock:
            self._anchor = (float(x), float(y), float(width), float(height))

    def close(self) -> None:
        self._closing.set()

    # ------------------------------------------------------------ tk thread
    def _run(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.withdraw()
        root.configure(bg="#ffa5c3")

        win_w, win_h = 330, 54
        frame = tk.Frame(root, bg="#ffa5c3")
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        entry = tk.Entry(
            frame,
            font=("Microsoft YaHei UI", 11),
            relief="flat",
            bd=0,
            fg="#4a4a55",
            insertbackground="#ff5c8a",
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#ffd3e2",
            highlightcolor="#ff8fb3",
        )
        entry.pack(fill="both", expand=True, padx=8, pady=7)

        def set_placeholder() -> None:
            entry.delete(0, tk.END)
            entry.insert(0, PLACEHOLDER)
            entry.config(fg="#b8b8c0")

        def clear_placeholder(_event=None) -> None:
            if entry.get() == PLACEHOLDER:
                entry.delete(0, tk.END)
                entry.config(fg="#4a4a55")

        entry.bind("<Button-1>", clear_placeholder)
        entry.bind("<KeyPress>", clear_placeholder)

        manage = tk.Toplevel(root)
        manage.title("白名单管理")
        manage.attributes("-topmost", True)
        manage.configure(bg="#f7f7f9")
        screen_w = manage.winfo_screenwidth()
        screen_h = manage.winfo_screenheight()
        manage.geometry(
            "360x340+{}+{}".format(
                max(0, (screen_w - 360) // 2),
                max(0, (screen_h - 340) // 2),
            )
        )
        manage.withdraw()

        tk.Label(
            manage,
            text="允许桌宠打开的软件（名称 → 启动命令）",
            bg="#f7f7f9",
            fg="#555555",
            font=("Microsoft YaHei UI", 9),
        ).pack(pady=(8, 2))

        listbox = tk.Listbox(manage, width=42, height=10, font=("Microsoft YaHei UI", 10))
        listbox.pack(padx=10, pady=4, fill="both", expand=True)

        status = tk.Label(
            manage, text="", bg="#f7f7f9", fg="#666666", font=("Microsoft YaHei UI", 9)
        )
        status.pack()

        def refresh_apps() -> None:
            listbox.delete(0, tk.END)
            for name, command in sorted(self._get_apps().items()):
                listbox.insert(tk.END, f"{name}  →  {command}")

        bar = tk.Frame(manage, bg="#f7f7f9")
        bar.pack(padx=10, pady=4)
        name_entry = tk.Entry(bar, width=12, font=("Microsoft YaHei UI", 10))
        name_entry.grid(row=0, column=0, padx=(0, 4))
        cmd_entry = tk.Entry(bar, width=22, font=("Microsoft YaHei UI", 10))
        cmd_entry.grid(row=0, column=1)

        def do_add() -> None:
            name = name_entry.get().strip()
            command = cmd_entry.get().strip()
            if not name or not command:
                status.config(text="应用名和启动命令都要填")
                return
            status.config(text=self._add_app(name, command))
            name_entry.delete(0, tk.END)
            cmd_entry.delete(0, tk.END)
            refresh_apps()

        def do_delete() -> None:
            selection = listbox.curselection()
            if not selection:
                status.config(text="先选中要移除的应用")
                return
            label = listbox.get(selection[0])
            name = label.split("  →  ", 1)[0]
            status.config(text=self._remove_app(name))
            refresh_apps()

        buttons = tk.Frame(manage, bg="#f7f7f9")
        buttons.pack(pady=(0, 10))
        tk.Button(buttons, text="添加", command=do_add, width=8, bg="#ffa5c3").grid(
            row=0, column=0, padx=4
        )
        tk.Button(buttons, text="移除选中", command=do_delete, width=10, bg="#c9d8e8").grid(
            row=0, column=1, padx=4
        )
        tk.Button(buttons, text="关闭", command=manage.withdraw, width=8).grid(
            row=0, column=2, padx=4
        )

        def place_input() -> None:
            with self._lock:
                px, py, pw, ph = self._anchor
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            x = int(px + pw / 2 - win_w / 2)
            y = int(screen_h - (py + ph + 10 + win_h))
            if y < 0:
                y = int(screen_h - py + 10)
            x = max(0, min(x, screen_w - win_w))
            y = max(0, min(y, screen_h - win_h))
            root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        def hide_input() -> None:
            root.withdraw()
            if self._on_hide is not None:
                try:
                    self._on_hide()
                except Exception:
                    pass

        def submit(_event=None) -> None:
            text = entry.get().strip()
            if text == PLACEHOLDER:
                text = ""
            hide_input()
            if text:
                self._on_submit(text)

        def on_escape(_event=None) -> None:
            hide_input()

        entry.bind("<Return>", submit)
        root.bind("<Escape>", on_escape)

        refresh_apps()

        def poll() -> None:
            if self._closing.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            try:
                if self._show_input.is_set():
                    self._show_input.clear()
                    manage.withdraw()
                    set_placeholder()
                    root.deiconify()
                    place_input()
                    root.lift()
                    entry.focus_set()
                    root.after(30, lambda: entry.focus_force())
                if self._show_manage.is_set():
                    self._show_manage.clear()
                    root.withdraw()
                    refresh_apps()
                    manage.deiconify()
                    manage.lift()
                if self._hide_input.is_set():
                    self._hide_input.clear()
                    hide_input()
                if root.winfo_viewable():
                    place_input()
            except tk.TclError:
                return
            except Exception:
                pass
            root.after(50, poll)

        poll()
        try:
            root.mainloop()
        except Exception:
            pass
