"""Character (sprite pack) discovery.

A character is a folder of PNG frame sequences plus an optional
``character.json``.  The placeholder character shipped with the project lives
in ``assets/characters/mochi``; users can drop their own pack in
``%APPDATA%/DesktopPet/characters/`` without touching the repository.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .paths import AppPaths

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Animation names understood by the UI.  "idle2" and "idle3" are the extra
# idle poses exposed by the radial menu.
ANIMATION_NAMES = ("idle", "idle2", "idle3", "walk", "jump", "ultra")

# Common alternative folder spellings, so third-party packs can be adopted
# without renaming every folder.
FOLDER_ALIASES = {
    "idle": ("idle", "daiji", "stand", "wait"),
    "idle2": ("idle2", "idle_2", "daiji2", "idle-2"),
    "idle3": ("idle3", "idle_3", "daiji3", "idle-3"),
    "walk": ("walk", "khqn", "run", "move"),
    "jump": ("jump", "tiaoyue", "hop"),
    "ultra": ("ultra", "dazhao", "skill", "special"),
}

DEFAULT_FRAME_SIZE = (256, 320)


class CharacterError(RuntimeError):
    """Raised when no usable character pack can be found."""


def _natural_key(path: Path) -> list[tuple[int, object]]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
    ]


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _list_frames(folder: Path) -> tuple[Path, ...]:
    if not folder.is_dir():
        return ()
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return tuple(sorted(files, key=_natural_key))


def available_characters(paths: AppPaths) -> list[str]:
    names: set[str] = set()
    for root in (paths.data / "characters", paths.characters):
        if root.is_dir():
            names.update(p.name for p in root.iterdir() if p.is_dir())
    return sorted(names)


@dataclass
class Character:
    key: str
    directory: Path
    name: str
    author: str
    license: str
    fps: float
    ultra_scale: float
    frame_size: tuple[int, int]
    animations: dict[str, tuple[Path, ...]] = field(default_factory=dict)

    @property
    def aspect_ratio(self) -> float:
        width, height = self.frame_size
        return width / height if height else DEFAULT_FRAME_SIZE[0] / DEFAULT_FRAME_SIZE[1]

    def frames(self, name: str) -> tuple[Path, ...]:
        """Return frames for *name*, falling back to the idle animation."""
        frames = self.animations.get(name)
        if frames:
            return frames
        return self.animations.get("idle", ())

    def size_for(self, height: float, name: str = "idle") -> tuple[float, float]:
        ratio = self.ultra_scale if name == "ultra" else 1.0
        h = height * ratio
        return h * self.aspect_ratio, h

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "directory": str(self.directory),
            "fps": self.fps,
            "frame_size": list(self.frame_size),
            "animations": {key: len(value) for key, value in self.animations.items()},
        }


def _find_directory(key: str, paths: AppPaths) -> Path | None:
    for root in (paths.data / "characters", paths.characters):
        candidate = root / key
        if candidate.is_dir():
            return candidate
    return None


def load_character(key: str, paths: AppPaths) -> Character:
    directory = _find_directory(key, paths)
    if directory is None:
        directory = _find_directory("mochi", paths)
        if directory is None:
            available = available_characters(paths) or ["(none)"]
            raise CharacterError(
                f"找不到角色「{key}」，也没有内置的 mochi。可用角色：{', '.join(available)}"
            )
        key = "mochi"

    meta = _read_json(directory / "character.json")
    mapping = meta.get("animations")
    mapping = mapping if isinstance(mapping, dict) else {}

    animations: dict[str, tuple[Path, ...]] = {}
    for name in ANIMATION_NAMES:
        configured = mapping.get(name)
        candidates: list[str] = []
        if isinstance(configured, str):
            candidates.append(configured)
        elif isinstance(configured, list):
            candidates.extend(str(item) for item in configured)
        candidates.extend(FOLDER_ALIASES[name])

        frames: tuple[Path, ...] = ()
        for folder_name in candidates:
            frames = _list_frames(directory / folder_name)
            if frames:
                break
        if frames:
            animations[name] = frames

    idle = animations.get("idle")
    if not idle:
        raise CharacterError(
            f"角色目录 {directory} 里没有可用的待机帧。"
            "请把 PNG 序列放到 idle/ 子目录，或参考 docs/ASSETS.md。"
        )

    for name in ("idle2", "idle3"):
        animations.setdefault(name, idle)

    frame_size = DEFAULT_FRAME_SIZE
    declared = meta.get("frame_width"), meta.get("frame_height")
    if all(isinstance(value, (int, float)) and value > 0 for value in declared):
        frame_size = (int(declared[0]), int(declared[1]))

    fps = meta.get("fps", 12)
    try:
        fps = float(fps)
    except (TypeError, ValueError):
        fps = 12.0
    fps = min(60.0, max(1.0, fps))

    ultra_scale = meta.get("ultra_scale", 1.35)
    try:
        ultra_scale = float(ultra_scale)
    except (TypeError, ValueError):
        ultra_scale = 1.35
    ultra_scale = min(3.0, max(1.0, ultra_scale))

    return Character(
        key=key,
        directory=directory,
        name=str(meta.get("name") or key),
        author=str(meta.get("author") or "unknown"),
        license=str(meta.get("license") or "unknown"),
        fps=fps,
        ultra_scale=ultra_scale,
        frame_size=frame_size,
        animations=animations,
    )
