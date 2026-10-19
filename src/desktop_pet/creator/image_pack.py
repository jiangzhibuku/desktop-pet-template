"""Turn one character image into a set of animation frames.

A single cutout cannot really "walk", so the motion is intentionally stylised:
bobbing, squash/stretch, a small tilt and a soft shadow.  That keeps the
character's own art intact instead of redrawing or deforming it.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .cutout import DEFAULT_MODEL
from .cutout import prepare as prepare_cutout

W, H = 256, 320
SCALE = 3
GROUND_Y = 300          # feet line in 256x320 coordinates
MAX_W, MAX_H = 228, 286

SHADOW = (92, 72, 82, 52)
OUTLINE_GLOW = (255, 186, 214)


def prepare_image(
    path: str | Path,
    *,
    tolerance: int = 32,
    cutout: str = "auto",
    cutout_model: str = DEFAULT_MODEL,
) -> Image.Image:
    """Load an image and return its foreground (alpha-cropped)."""
    result = prepare_cutout(
        path,
        mode=cutout,
        tolerance=tolerance,
        model=cutout_model,
    )
    image = result.image
    if image.width == 0 or image.height == 0:
        raise ValueError("图片里没有可用的角色像素")
    return image


def normalize(image: Image.Image, *, max_w: int = MAX_W, max_h: int = MAX_H) -> Image.Image:
    """Scale the cutout to fit the canvas.

    The result is the tight character image (not a padded canvas); the renderer
    anchors its bottom edge to :data:`GROUND_Y`.
    """
    ratio = min(max_w / image.width, max_h / image.height)
    width = max(1, int(round(image.width * ratio)))
    height = max(1, int(round(image.height * ratio)))
    resized = image.resize((width, height), Image.LANCZOS)
    return resized.resize((width * SCALE, height * SCALE), Image.LANCZOS)


def _shadow(canvas: Image.Image, base_width: int, lift: float) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    grow = max(0.35, 1.0 - lift / 120.0)
    spread = (base_width * 0.55) * grow
    cy = GROUND_Y * SCALE + 10 * SCALE
    cx = W * SCALE // 2
    draw.ellipse(
        [
            cx - spread,
            cy - 7 * SCALE,
            cx + spread,
            cy + 8 * SCALE,
        ],
        fill=SHADOW,
    )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3 * SCALE)))


def _glow(canvas: Image.Image, strength: float) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = W * SCALE // 2, 180 * SCALE
    for i, radius in enumerate(range(40, 150, 12)):
        alpha = int((5 + 3 * i) * strength)
        draw.ellipse(
            [
                cx - radius * SCALE,
                cy - int(radius * 0.72) * SCALE,
                cx + radius * SCALE,
                cy + int(radius * 0.72) * SCALE,
            ],
            fill=(255, 190, 220, max(0, min(80, alpha))),
        )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(5 * SCALE)))


def _sparkles(canvas: Image.Image, strength: float) -> None:
    draw = ImageDraw.Draw(canvas)
    points = [(78, 96), (188, 112), (70, 190), (196, 210)]
    for index, (x, y) in enumerate(points):
        size = (5 + (index % 2) * 3) * SCALE * (0.6 + strength * 0.5)
        cx, cy = x * SCALE, y * SCALE
        draw.polygon(
            [
                (cx, cy - size),
                (cx + size * 0.28, cy - size * 0.28),
                (cx + size, cy),
                (cx + size * 0.28, cy + size * 0.28),
                (cx, cy + size),
                (cx - size * 0.28, cy + size * 0.28),
                (cx - size, cy),
                (cx - size * 0.28, cy - size * 0.28),
            ],
            fill=(255, 224, 132, int(180 * strength)),
        )


def render_frame(
    base: Image.Image,
    *,
    bob: float = 0.0,
    squash: tuple[float, float] = (1.0, 1.0),
    sway: float = 0.0,
    angle: float = 0.0,
    lift: float = 0.0,
    glow: float = 0.0,
) -> Image.Image:
    canvas = Image.new("RGBA", (W * SCALE, H * SCALE), (0, 0, 0, 0))
    base_width = base.width // SCALE
    _shadow(canvas, base_width, lift)
    if glow:
        _glow(canvas, glow)

    art = base
    if squash != (1.0, 1.0):
        new_w = max(1, int(art.width * squash[0]))
        new_h = max(1, int(art.height * squash[1]))
        art = art.resize((new_w, new_h), Image.LANCZOS)
    if angle:
        art = art.rotate(angle, resample=Image.BICUBIC, expand=True)

    x = (W * SCALE - art.width) // 2 + int(sway * SCALE)
    # PIL's origin is top-left; GROUND_Y is measured from the top edge.
    y = GROUND_Y * SCALE - art.height - int(bob * SCALE)
    canvas.alpha_composite(art, (x, y))
    if glow:
        _sparkles(canvas, glow)
    return canvas.resize((W, H), Image.LANCZOS)


def frames_from_image(
    path: str | Path,
    *,
    tolerance: int = 32,
    cutout: str = "auto",
    cutout_model: str = DEFAULT_MODEL,
    notices: list[str] | None = None,
) -> dict[str, list[Image.Image]]:
    """Create the six animation sequences from one image."""
    result = prepare_cutout(
        path,
        mode=cutout,
        tolerance=tolerance,
        model=cutout_model,
    )
    if notices is not None:
        notices.extend(result.notices)
    if result.image.width == 0 or result.image.height == 0:
        raise ValueError("图片里没有可用的角色像素")
    base = normalize(result.image)

    idle: list[Image.Image] = []
    for index, bob in enumerate([0, -1, -2, -2, -1, 0, 0, 0, -1, -2]):
        breathe = 0.008 if index in (2, 3) else 0.0
        idle.append(
            render_frame(
                base,
                bob=bob,
                squash=(1.0 - breathe * 0.4, 1.0 + breathe),
                lift=abs(bob),
                angle=(-1 if index in (2, 3) else 0),
            )
        )

    idle2: list[Image.Image] = []
    for index, bob in enumerate([0, -1, -1, 0, 0, -1, -2, -2, -1, 0]):
        idle2.append(
            render_frame(
                base,
                bob=bob,
                squash=(1.0, 1.0 + (0.006 if index in (6, 7) else 0.0)),
                sway=1.5 if index in (3, 4, 5) else -1.0,
                angle=(2 if index in (4, 5) else 0),
                lift=abs(bob),
            )
        )

    idle3: list[Image.Image] = []
    for index in range(12):
        bob = [0, -1, -1, 0, 0, -1, -2, -2, -1, 0, 0, -1][index]
        idle3.append(
            render_frame(
                base,
                bob=bob,
                squash=(1.0 + 0.006, 1.0 - 0.004),
                sway=math.sin(index / 12 * math.tau) * 1.2,
                lift=abs(bob),
            )
        )

    walk: list[Image.Image] = []
    for index in range(8):
        walk.append(
            render_frame(
                base,
                bob=[0, -2, -1, 0, 0, -2, -1, 0][index],
                squash=(1.0, 1.0 + (0.01 if index in (1, 5) else 0.0)),
                sway=[0, 2, 1, 0, 0, -2, -1, 0][index],
                angle=[0, 2, 1, 0, 0, -2, -1, 0][index],
                lift=abs([0, -2, -1, 0, 0, -2, -1, 0][index]),
            )
        )

    poses = [
        (0, (1.0, 1.0)),
        (0, (1.06, 0.90)),
        (-2, (0.95, 1.05)),
        (-6, (0.93, 1.08)),
        (-6, (0.95, 1.06)),
        (-2, (1.02, 0.96)),
        (0, (1.04, 0.94)),
        (0, (1.0, 1.0)),
    ]
    jump = [
        render_frame(base, bob=bob, squash=squash, lift=abs(bob), angle=(-1 if bob else 0))
        for bob, squash in poses
    ]

    ultra: list[Image.Image] = []
    for index in range(12):
        pulse = 0.55 + 0.45 * math.sin(index / 12 * math.tau) ** 2
        ultra.append(
            render_frame(
                base,
                bob=-3 * pulse,
                squash=(1.0 + 0.02 * pulse, 1.0 + 0.02 * pulse),
                sway=1.5 * pulse,
                glow=pulse,
                lift=3 * pulse,
            )
        )

    return {
        "idle": idle,
        "idle2": idle2,
        "idle3": idle3,
        "walk": walk,
        "jump": jump,
        "ultra": ultra,
    }
