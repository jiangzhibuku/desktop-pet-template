"""Write a generated character pack and update the active configuration."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .. import __version__
from ..config import load_config, save_config
from ..paths import AppPaths
from .spec import CharacterSpec

PACK_FRAME_SIZE = (256, 320)
IMAGE_NAMES = ("idle", "idle2", "idle3", "walk", "jump", "ultra")


@dataclass
class PackResult:
    key: str
    directory: Path
    preview: Path
    spec: CharacterSpec


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKC", name or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = "".join(ch for ch in text if ch.isalnum() or ch in {"_", "-"})
    text = text.strip("_-").lower()
    return (text or "pet")[:32]


def _unique_key(paths: AppPaths, base: str, overwrite: bool) -> tuple[str, Path]:
    root = paths.data / "characters"
    root.mkdir(parents=True, exist_ok=True)
    key = base
    candidate = root / key
    if overwrite:
        if candidate.exists():
            shutil.rmtree(candidate)
        return key, candidate
    index = 2
    while candidate.exists():
        key = f"{base}_{index}"
        candidate = root / key
        index += 1
    return key, candidate


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyhbd.ttc",
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msyh.ttc",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def build_preview(spec: CharacterSpec, idle: list[Image.Image], out_dir: Path, fps: float) -> Path:
    """A 900x560 pastel card plus a looping GIF of the first idle animation."""
    scale = 2
    width, height = 900, 560
    canvas = Image.new("RGBA", (width * scale, height * scale))
    draw = ImageDraw.Draw(canvas)
    for y in range(height * scale):
        t = y / (height * scale)
        draw.line(
            [(0, y), (width * scale, y)],
            fill=(int(255 - 8 * t), int(242 + 6 * t), int(246 + 6 * t)),
        )
    for cx, cy, radius, color in [
        (110, 80, 90, (255, 220, 232, 255)),
        (790, 120, 120, (222, 240, 255, 255)),
        (770, 480, 90, (255, 236, 214, 255)),
    ]:
        draw.ellipse(
            [
                (cx - radius) * scale,
                (cy - radius) * scale,
                (cx + radius) * scale,
                (cy + radius) * scale,
            ],
            fill=color,
        )

    if idle:
        pet = idle[0].resize((int(PACK_FRAME_SIZE[0] * 1.35), int(PACK_FRAME_SIZE[1] * 1.35)), Image.LANCZOS)
        canvas.alpha_composite(pet, (110 * scale, 100 * scale))

    font = _font(46 * scale)
    small = _font(18 * scale)
    draw.text((470 * scale, 190 * scale), spec.name[:14], font=font, fill=(90, 72, 82))
    draw.text(
        (472 * scale, 250 * scale),
        f"{spec.species} · {spec.accessory} · {spec.pattern}",
        font=small,
        fill=(150, 120, 135),
    )
    draw.text(
        (472 * scale, 286 * scale),
        "made with Desktop Pet Creator",
        font=small,
        fill=(180, 150, 165),
    )
    if spec.description:
        draw.text(
            (472 * scale, 330 * scale),
            spec.description[:28],
            font=small,
            fill=(120, 100, 110),
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    preview = out_dir / "preview.png"
    canvas.resize((width, height), Image.LANCZOS).save(preview, optimize=True)

    if idle:
        gif_frames = []
        for frame in idle:
            back = Image.new("RGBA", PACK_FRAME_SIZE, (253, 243, 247, 255))
            back.alpha_composite(frame)
            gif_frames.append(back.convert("P", palette=Image.ADAPTIVE, colors=64))
        gif_frames[0].save(
            out_dir / "preview.gif",
            save_all=True,
            append_images=gif_frames[1:],
            duration=max(40, int(1000 / max(1.0, fps))),
            loop=0,
            optimize=True,
        )
    return preview


def save_pack(
    spec: CharacterSpec,
    frames: dict[str, list[Image.Image]],
    paths: AppPaths,
    *,
    source: dict,
    overwrite: bool = False,
    make_default: bool = True,
    frame_size: tuple[int, int] = PACK_FRAME_SIZE,
) -> PackResult:
    spec = spec.normalized()
    key, directory = _unique_key(paths, slugify(spec.name), overwrite)
    directory.mkdir(parents=True, exist_ok=True)

    animations: dict[str, str] = {}
    for name in IMAGE_NAMES:
        images = frames.get(name) or frames.get("idle") or []
        if not images:
            continue
        folder = directory / name
        folder.mkdir(exist_ok=True)
        for index, frame in enumerate(images):
            frame.convert("RGBA").save(folder / f"{name}_{index:02d}.png", optimize=True)
        animations[name] = name

    meta = {
        "name": spec.name,
        "species": spec.species,
        "description": spec.description,
        "author": spec.author,
        "license": spec.license,
        "frame_width": frame_size[0],
        "frame_height": frame_size[1],
        "fps": spec.fps,
        "ultra_scale": spec.ultra_scale,
        "generator": f"desktop-pet-creator/{__version__}",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "animations": animations,
        "spec": spec.to_dict(),
    }
    (directory / "character.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    source_lines = [
        f"Character: {spec.name}",
        f"Generated by: desktop-pet-creator/{__version__}",
        f"Date: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Species: {spec.species}",
        f"Source type: {source.get('type', 'unknown')}",
    ]
    if source.get("prompt"):
        source_lines.append(f"Prompt: {source['prompt']}")
    if source.get("image"):
        source_lines.append(f"Image: {source['image']}")
    source_lines.extend(
        [
            "",
            "IMPORTANT",
            "This pack was generated locally. If you publish or sell it, you must",
            "confirm that you own the source image / the generated result and that",
            "your image model's terms allow commercial use.",
        ]
    )
    (directory / "SOURCE.txt").write_text("\n".join(source_lines) + "\n", encoding="utf-8")
    (directory / "LICENSE.txt").write_text(
        "License: unverified\n"
        "The character assets in this folder were supplied or generated by the\n"
        "user. The project's MIT/CC0 licenses do not apply to them. Replace this\n"
        "file with the actual license after checking the source.\n",
        encoding="utf-8",
    )

    preview = build_preview(spec, frames.get("idle", []), directory, spec.fps)

    if make_default:
        config = load_config(paths)
        config.character = key
        save_config(config, paths)

    return PackResult(key=key, directory=directory, preview=preview, spec=spec)


def save_linked_pack(
    spec: CharacterSpec,
    frame_dirs: dict[str, Path],
    paths: AppPaths,
    *,
    source: dict,
    overwrite: bool = False,
    make_default: bool = True,
    fps: float = 12.0,
    ultra_scale: float = 1.35,
) -> PackResult:
    """Register an existing frame folder without copying the images.

    Useful for a 100+ MB legacy pack: the character folder only contains
    metadata and absolute paths, so the original assets stay where they are.
    """
    spec = spec.normalized()
    key, directory = _unique_key(paths, slugify(spec.name), overwrite)
    directory.mkdir(parents=True, exist_ok=True)

    animations = {name: str(path.resolve()) for name, path in frame_dirs.items()}
    idle_dir = frame_dirs.get("idle")
    first_idle = None
    if isinstance(idle_dir, Path) and idle_dir.is_dir():
        first_idle = next((p for p in sorted(idle_dir.iterdir()) if p.is_file()), None)
    frame_size = PACK_FRAME_SIZE
    if first_idle is not None:
        try:
            with Image.open(first_idle) as image:
                frame_size = image.size
        except OSError:
            pass

    meta = {
        "name": spec.name,
        "species": spec.species,
        "description": spec.description,
        "author": spec.author,
        "license": spec.license,
        "frame_width": frame_size[0],
        "frame_height": frame_size[1],
        "fps": fps,
        "ultra_scale": ultra_scale,
        "generator": f"desktop-pet-creator/{__version__}",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": {**source, "linked": True},
        "animations": animations,
        "spec": spec.to_dict(),
    }
    (directory / "character.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        f"Character: {spec.name}",
        f"Source type: {source.get('type', 'linked-frames')}",
        "This pack links to external frame folders; the images are NOT copied.",
    ]
    if source.get("path"):
        lines.append(f"Source path: {source['path']}")
    lines.extend(
        [
            "",
            "IMPORTANT",
            "If the source frames are third-party artwork, do not redistribute",
            "this pack or the source images without permission.",
        ]
    )
    (directory / "SOURCE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (directory / "LICENSE.txt").write_text(
        "License: unverified\n"
        "Linked third-party frames are not covered by this project's licenses.\n",
        encoding="utf-8",
    )

    preview_frames: list[Image.Image] = []
    idle_dir = frame_dirs.get("idle")
    if idle_dir and idle_dir.is_dir():
        first = sorted(idle_dir.iterdir())[:1]
        for item in first:
            try:
                with Image.open(item) as image:
                    preview_frames.append(image.convert("RGBA"))
            except OSError:
                pass
    preview = build_preview(spec, preview_frames, directory, fps)

    if make_default:
        config = load_config(paths)
        config.character = key
        save_config(config, paths)

    return PackResult(key=key, directory=directory, preview=preview, spec=spec)


def list_packs(paths: AppPaths) -> list[dict]:
    packs: list[dict] = []
    roots = [paths.data / "characters", paths.characters]
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.name in seen:
                continue
            meta_path = child / "character.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
            seen.add(child.name)
            packs.append(
                {
                    "key": child.name,
                    "name": meta.get("name") or child.name,
                    "species": meta.get("species") or "",
                    "directory": child,
                }
            )
    return packs


def use_pack(paths: AppPaths, key: str) -> None:
    config = load_config(paths)
    config.character = key
    save_config(config, paths)


def open_path(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass
