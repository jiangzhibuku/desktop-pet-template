"""High-level creation flows used by both the CLI and the in-app wizard."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from ..config import Config, load_config
from ..paths import AppPaths
from . import ai
from .draw import build_frames
from .image_pack import frames_from_image
from .pack import (
    PackResult,
    save_linked_pack,
    save_pack,
    slugify,
)
from .spec import CharacterSpec

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

FRAME_CANDIDATES = {
    "idle": ("idle", "idle1", "daiji/daiji1", "daiji1", "stand", "wait"),
    "idle2": ("idle2", "idle_2", "daiji/daiji2", "daiji2"),
    "idle3": ("idle3", "idle_3", "daiji/daiji3", "daiji3"),
    "walk": ("walk", "khqn", "run", "move"),
    "jump": ("jump", "tiaoyue", "hop"),
    "ultra": ("ultra", "dazhao", "skill", "special"),
}


def _natural(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.lower())
    return [(0, int(part)) if part.isdigit() else (1, part) for part in parts]


def _images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ],
        key=_natural,
    )


def find_frame_dirs(source: Path) -> dict[str, Path]:
    """Map animation names to frame folders in an existing pack."""
    meta: dict = {}
    meta_path = source / "character.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}

    result: dict[str, Path] = {}
    configured = meta.get("animations")
    if isinstance(configured, dict):
        for name, value in configured.items():
            if not isinstance(value, str):
                continue
            folder = source / value
            if _images(folder):
                result[name] = folder
    if result.get("idle"):
        return result

    for name, candidates in FRAME_CANDIDATES.items():
        for candidate in candidates:
            folder = source / candidate
            if _images(folder):
                result[name] = folder
                break

    # A folder that directly contains frames is treated as the idle animation.
    if "idle" not in result and _images(source):
        result["idle"] = source
    return result


def _meta(source: Path) -> dict:
    path = source / "character.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def create_from_image(
    image_path: str | Path,
    name: str,
    paths: AppPaths,
    *,
    author: str = "unknown",
    license: str = "unverified",
    tolerance: int = 32,
    overwrite: bool = False,
    make_default: bool = True,
) -> PackResult:
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"找不到图片：{path}")
    spec = CharacterSpec(
        name=name or path.stem,
        description=f"image: {path.name}",
        author=author,
        license=license,
    ).normalized()
    frames = frames_from_image(path, tolerance=tolerance)
    return save_pack(
        spec,
        frames,
        paths,
        source={"type": "image", "image": str(path.resolve())},
        overwrite=overwrite,
        make_default=make_default,
    )


def create_from_prompt(
    prompt: str,
    name: str | None,
    paths: AppPaths,
    *,
    config: Config | None = None,
    use_ai_spec: bool = False,
    use_ai_image: bool = False,
    author: str = "unknown",
    license: str = "unverified",
    overwrite: bool = False,
    make_default: bool = True,
) -> tuple[PackResult, list[str]]:
    config = config or load_config(paths)
    notices: list[str] = []
    spec, spec_source = ai.spec_for_prompt(prompt, config, use_ai=use_ai_spec)
    if use_ai_spec:
        notices.append("规格解析：" + ("AI" if spec_source == "ai" else "AI 不可用，已用离线规则"))
    if name:
        spec.name = name
    spec.author = author
    spec.license = license

    frames = None
    source: dict
    if use_ai_image:
        generated = paths.data / "generated" / (slugify(spec.name) + ".png")
        image_path = ai.generate_image(ai.image_prompt(spec), config, generated)
        if image_path is not None:
            try:
                frames = frames_from_image(image_path)
                source = {
                    "type": "ai-image",
                    "prompt": prompt,
                    "image": str(image_path),
                }
                notices.append("角色图：AI 生成成功")
            except Exception:
                frames = None
        if frames is None:
            notices.append("AI 出图不可用，已回退到离线绘制")

    if frames is None:
        frames = build_frames(spec)
        source = {"type": "prompt", "prompt": prompt}
        notices.append("角色图：离线程序化绘制")

    result = save_pack(
        spec,
        frames,
        paths,
        source=source,
        overwrite=overwrite,
        make_default=make_default,
    )
    return result, notices


def import_frames(
    source: str | Path,
    name: str | None,
    paths: AppPaths,
    *,
    link: bool = False,
    author: str = "unknown",
    license: str = "unverified",
    overwrite: bool = False,
    make_default: bool = True,
) -> PackResult:
    source = Path(source).expanduser()
    if not source.is_dir():
        raise NotADirectoryError(f"找不到文件夹：{source}")
    frame_dirs = find_frame_dirs(source)
    if "idle" not in frame_dirs:
        raise ValueError("没有找到待机帧。请提供 idle/ 文件夹，或包含 idle/daiji1/khqn 等子目录的角色包。")

    meta = _meta(source)
    spec_data = meta.get("spec")
    if isinstance(spec_data, dict):
        spec = CharacterSpec.from_dict(spec_data)
    else:
        spec = CharacterSpec(
            name=name or str(meta.get("name") or source.name),
            description=f"frames: {source}",
            author=author,
            license=license,
            fps=float(meta.get("fps") or 12),
            ultra_scale=float(meta.get("ultra_scale") or 1.35),
        )
    if name:
        spec.name = name
    spec.author = author
    spec.license = license

    if link:
        return save_linked_pack(
            spec,
            frame_dirs,
            paths,
            source={"type": "frames", "path": str(source.resolve())},
            overwrite=overwrite,
            make_default=make_default,
            fps=float(meta.get("fps") or spec.fps),
            ultra_scale=float(meta.get("ultra_scale") or spec.ultra_scale),
        )

    frames: dict[str, list[Image.Image]] = {}
    first_idle = _images(frame_dirs["idle"])[0]
    try:
        with Image.open(first_idle) as image:
            frame_size = image.size
    except OSError:
        frame_size = (256, 320)
    for key, folder in frame_dirs.items():
        images: list[Image.Image] = []
        for path in _images(folder):
            try:
                with Image.open(path) as image:
                    images.append(image.convert("RGBA").copy())
            except OSError:
                continue
        if images:
            frames[key] = images

    return save_pack(
        spec,
        frames,
        paths,
        source={"type": "frames", "path": str(source.resolve())},
        overwrite=overwrite,
        make_default=make_default,
        frame_size=frame_size,
    )


def list_packs(paths: AppPaths) -> list[dict]:
    from .pack import list_packs as _list

    return _list(paths)
