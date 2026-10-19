"""Filesystem layout used by the application.

Keeping every mutable file (config, memories, logs, screenshots) in the user's
data directory means a fresh clone of the repository never contains personal
data and can be published safely.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "DesktopPet"


def project_root() -> Path:
    """Return the repository root (or the PyInstaller extraction directory)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # src/desktop_pet/paths.py -> <repo>
    return Path(__file__).resolve().parents[2]


def user_data_dir() -> Path:
    """Return the per-user data directory.

    Override with ``DESKTOP_PET_HOME`` (useful for portable installs and tests).
    """
    override = os.environ.get("DESKTOP_PET_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "desktop-pet"


@dataclass(frozen=True)
class AppPaths:
    root: Path
    assets: Path
    characters: Path
    data: Path
    config: Path
    memory: Path
    todos: Path
    stats: Path
    whitelist: Path
    logs: Path
    screenshots: Path

    def ensure(self) -> "AppPaths":
        for path in (
            self.data,
            self.characters,
            self.logs,
            self.screenshots,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self


def build_paths(root: Path | None = None, data: Path | None = None) -> AppPaths:
    root = (root or project_root()).resolve()
    data = (data or user_data_dir()).resolve()
    assets = root / "assets"
    return AppPaths(
        root=root,
        assets=assets,
        characters=assets / "characters",
        data=data,
        config=data / "config.json",
        memory=data / "memory.json",
        todos=data / "todos.json",
        stats=data / "stats.json",
        whitelist=data / "whitelist.json",
        logs=data / "logs",
        screenshots=data / "screenshots",
    ).ensure()
