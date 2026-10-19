"""Entry point: ``python -m desktop_pet`` or ``python run.py``."""

from __future__ import annotations

import os
import sys
import traceback


def _enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _show_error(message: str) -> None:
    print(message, file=sys.stderr)
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "Desktop Pet", 0x10)
    except Exception:
        pass


def main() -> int:
    if os.name != "nt":
        _show_error("桌面宠物目前只支持 Windows。")
        return 1

    _enable_dpi_awareness()
    try:
        from .app import DesktopPetApp

        DesktopPetApp().run()
        return 0
    except Exception as exc:
        traceback.print_exc()
        _show_error(
            "桌面宠物启动失败：\n\n"
            + str(exc)
            + "\n\n请查看终端输出，或到 GitHub Issues 反馈。"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
