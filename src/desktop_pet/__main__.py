"""Entry point: ``python -m desktop_pet`` or ``python run.py``."""

from __future__ import annotations

import os
import site
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


def _prepare_frozen_dlls() -> None:
    if not getattr(sys, "frozen", False):
        return
    base = getattr(sys, "_MEIPASS", "")
    if not base:
        return
    os.environ["PATH"] = base + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(base)
        except OSError:
            pass


def main() -> int:
    if os.name != "nt":
        _show_error("桌面宠物目前只支持 Windows。")
        return 1

    if "--safe" in sys.argv:
        os.environ["DESKTOP_PET_SAFE"] = "1"
        sys.argv.remove("--safe")

    _enable_dpi_awareness()
    _prepare_frozen_dlls()
    if site.USER_BASE is None:
        site.USER_BASE = os.environ.get("APPDATA", os.path.expanduser("~"))
    if not os.environ.get("KIVY_GL_BACKEND"):
        try:
            import kivy_deps.angle  # noqa: F401

            os.environ["KIVY_GL_BACKEND"] = "angle_sdl2"
        except Exception:
            pass
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
