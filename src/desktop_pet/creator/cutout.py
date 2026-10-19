"""Pluggable foreground extraction for character images.

Backends
--------
``auto``
    Transparent PNG -> alpha crop.  Opaque image -> corner flood fill.  If the
    flood fill removed almost nothing and ``rembg`` is installed, retry with the
    local model.
``rembg``
    Force the local `rembg <https://github.com/danielgatis/rembg>`_ model
    (default ``isnet-anime``, which is trained on anime/character art).
``none``
    Keep the original background.  The pet becomes a rectangular card, which
    is only useful for images that are already transparent or intentionally
    framed.

Nothing here imports Kivy, so it can be tested without a display.  ``rembg`` is
an optional dependency and is imported lazily.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

CUTOUT_MODES = {"auto", "rembg", "none"}
DEFAULT_MODEL = "isnet-anime"

_SESSIONS: dict[str, object] = {}


@dataclass
class CutoutResult:
    image: Image.Image
    method: str
    notices: list[str] = field(default_factory=list)


def rembg_available() -> bool:
    try:
        import rembg  # noqa: F401
    except Exception:
        return False
    return True


def _has_alpha(image: Image.Image) -> bool:
    return image.getchannel("A").getextrema()[0] < 250


def _trim_alpha(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


def _corner_color(image: Image.Image) -> tuple[int, int, int, int]:
    width, height = image.size
    points = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    pixels = [image.getpixel(point) for point in points]
    return max(set(pixels), key=pixels.count)


def _flood(image: Image.Image, tolerance: int) -> tuple[Image.Image, float]:
    """Remove a connected flat background.  Returns (cropped image, kept ratio)."""
    work = image.copy()
    width, height = work.size
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        try:
            ImageDraw.floodfill(work, corner, (0, 0, 0, 0), thresh=tolerance)
        except Exception:
            pass
    bbox = work.getchannel("A").getbbox()
    if not bbox:
        return image, 1.0
    kept_ratio = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / float(width * height)
    return work.crop(bbox), kept_ratio


def _remove_with_rembg(image: Image.Image, model: str) -> Image.Image:
    from rembg import new_session, remove

    session = _SESSIONS.get(model)
    if session is None:
        session = new_session(model)
        _SESSIONS[model] = session
    result = remove(image, session=session)
    if isinstance(result, bytes):
        result = Image.open(io.BytesIO(result))
    elif not isinstance(result, Image.Image):
        result = Image.open(result)
    return _trim_alpha(result.convert("RGBA"))


def prepare(
    path: str | Path,
    *,
    mode: str = "auto",
    tolerance: int = 32,
    model: str = DEFAULT_MODEL,
) -> CutoutResult:
    """Load an image and return a foreground cutout plus a short explanation."""
    mode = mode if mode in CUTOUT_MODES else "auto"
    image = Image.open(path).convert("RGBA")
    notices: list[str] = []

    if mode == "none":
        return CutoutResult(
            _trim_alpha(image),
            "none",
            ["保留原图背景（JPG 会带矩形底）"],
        )

    if _has_alpha(image):
        return CutoutResult(_trim_alpha(image), "alpha", ["检测到透明通道，直接按 alpha 裁切"])

    if mode == "rembg":
        if not rembg_available():
            work, _ratio = _flood(image, tolerance)
            return CutoutResult(
                work,
                "flood",
                ["未安装 rembg，已回退到纯色背景泛洪"],
            )
        try:
            return CutoutResult(
                _remove_with_rembg(image, model),
                "rembg",
                [f"使用本地 rembg（{model}）抠图"],
            )
        except Exception as exc:
            work, _ratio = _flood(image, tolerance)
            return CutoutResult(
                work,
                "flood",
                [f"rembg 失败（{str(exc)[:80]}），已回退到泛洪"],
            )

    # auto: fast flood first; only try rembg when flood barely removed anything.
    work, kept_ratio = _flood(image, tolerance)
    if kept_ratio > 0.92 and rembg_available():
        try:
            return CutoutResult(
                _remove_with_rembg(image, model),
                "rembg",
                [f"泛洪未有效去除背景，已用本地 rembg（{model}）"],
            )
        except Exception:
            pass
    if kept_ratio > 0.98:
        notices.append("背景几乎是整张图；如需智能抠图请安装 rembg，或上传透明 PNG")
    return CutoutResult(work, "flood", notices)
