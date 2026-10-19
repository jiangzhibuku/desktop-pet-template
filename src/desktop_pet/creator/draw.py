"""Procedural character art in the project's pastel, thick-outline style.

The renderer is deliberately simple: a chibi head + body, species-specific
ears/tail, one optional accessory and a handful of patterns.  It is not meant to
replace an artist; it gives every text prompt a usable, transparent character
pack with zero extra API calls.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from .spec import CharacterSpec

W, H = 256, 320
S = 3
CX = W // 2
GROUND = 300

OUTLINE = (74, 59, 66, 255)
BLUSH = (246, 158, 178, 200)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        value = "FFF6E8"
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def mix(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(4))


def lighten(color: tuple[int, ...], amount: float) -> tuple[int, ...]:
    return mix(color, (255, 255, 255, 255), amount)


def darken(color: tuple[int, ...], amount: float) -> tuple[int, ...]:
    return mix(color, (0, 0, 0, 255), amount)


def sc(value: float) -> int:
    return int(round(value * S))


def box(x0: float, y0: float, x1: float, y1: float):
    return sc(x0), sc(y0), sc(x1), sc(y1)


def ellipse(draw, xy, fill=None, outline=None, width=0):
    draw.ellipse(box(*xy), fill=fill, outline=outline, width=sc(width))


def polygon(draw, points, fill=None, outline=None, width=0):
    pts = [(sc(x), sc(y)) for x, y in points]
    draw.polygon(pts, fill=fill)
    if outline:
        draw.line(pts + [pts[0]], fill=outline, width=sc(width), joint="curve")


def line(draw, points, fill, width, joint="curve"):
    draw.line([(sc(x), sc(y)) for x, y in points], fill=fill, width=sc(width), joint=joint)


def star(draw, cx, cy, radius, fill, points=5):
    coords = []
    for index in range(points * 2):
        angle = -math.pi / 2 + index * math.pi / points
        r = radius if index % 2 == 0 else radius * 0.42
        coords.append((sc(cx + math.cos(angle) * r), sc(cy + math.sin(angle) * r)))
    draw.polygon(coords, fill=fill)


def heart(draw, cx, cy, size, fill):
    r = size * 0.32
    draw.ellipse(box(cx - size * 0.5, cy - size * 0.35, cx - size * 0.5 + 2 * r, cy - size * 0.35 + 2 * r), fill=fill)
    draw.ellipse(box(cx + size * 0.5 - 2 * r, cy - size * 0.35, cx + size * 0.5, cy - size * 0.35 + 2 * r), fill=fill)
    draw.polygon(
        [(sc(cx - size * 0.55), sc(cy - size * 0.02)), (sc(cx + size * 0.55), sc(cy - size * 0.02)), (sc(cx), sc(cy + size * 0.7))],
        fill=fill,
    )


# ---------------------------------------------------------------------------
# Character layers
# ---------------------------------------------------------------------------


def _palette(spec: CharacterSpec) -> dict[str, tuple[int, ...]]:
    body = rgba(spec.body_color)
    inner = rgba(spec.inner_color)
    accent = rgba(spec.accent_color)
    eye = rgba(spec.eye_color)
    return {
        "body": body,
        "body_shade": darken(body, 0.10),
        "belly": lighten(body, 0.35),
        "inner": inner,
        "accent": accent,
        "accent_dark": darken(accent, 0.18),
        "eye": eye,
        "outline": OUTLINE,
    }


def _ears(draw, species: str, colors: dict, ear: float, face_y: float) -> None:
    body, inner, outline = colors["body"], colors["inner"], colors["outline"]
    if species in {"cat", "fox"}:
        spread = 2 if species == "fox" else 0
        height = 30 if species == "fox" else 42
        left = [(74 - spread, 116), (86 + ear, height), (132, 94)]
        right = [(182 + spread, 116), (170 + ear, height), (124, 94)]
        polygon(draw, left, body, outline, 7)
        polygon(draw, right, body, outline, 7)
        polygon(draw, [(88 - spread, 104), (94 + ear, height + 22), (118 - spread, 96)], inner)
        polygon(draw, [(168 + spread, 104), (162 + ear, height + 22), (138 + spread, 96)], inner)
    elif species == "rabbit":
        ellipse(draw, (82, 24, 116, 132), body, outline, 7)
        ellipse(draw, (140, 24, 174, 132), body, outline, 7)
        ellipse(draw, (90, 38, 108, 116), inner)
        ellipse(draw, (148, 38, 166, 116), inner)
    elif species == "dog":
        ellipse(draw, (46, 96, 92, 200), colors["body_shade"], outline, 7)
        ellipse(draw, (164, 96, 210, 200), colors["body_shade"], outline, 7)
    elif species == "bear":
        ellipse(draw, (68, 62, 114, 108), body, outline, 7)
        ellipse(draw, (142, 62, 188, 108), body, outline, 7)
        ellipse(draw, (82, 76, 100, 94), inner)
        ellipse(draw, (156, 76, 174, 94), inner)
    elif species == "bird":
        for dx in (-10, 0, 10):
            line(draw, [(128 + dx, 78), (128 + dx * 1.4, 58)], colors["accent"], 5)
    # slime has no ears


def _tail(draw, species: str, colors: dict, swing: float) -> None:
    body, outline = colors["body"], colors["outline"]
    if species in {"cat", "fox"}:
        points = [(176, 276), (204 + swing, 272), (216 + swing, 246), (211 + swing, 220), (198 + swing, 208)]
        line(draw, points, outline, 24)
        line(draw, points, body, 14)
    elif species == "dog":
        points = [(178, 270), (202 + swing, 250), (204 + swing, 226)]
        line(draw, points, outline, 22)
        line(draw, points, body, 13)
    elif species == "rabbit":
        ellipse(draw, (188 + swing, 238, 218 + swing, 268), colors["belly"], outline, 6)
    elif species == "bear":
        ellipse(draw, (178, 254, 204, 280), body, outline, 6)
    elif species == "bird":
        for dx in (-8, 0, 8):
            line(draw, [(150, 250), (182 + swing, 274 + dx)], colors["accent"], 7)


def _body(draw, species: str, colors: dict) -> None:
    body, outline = colors["body"], colors["outline"]
    if species == "slime":
        ellipse(draw, (56, 108, 200, 302), body, outline, 8)
        ellipse(draw, (96, 132, 160, 160), lighten(body, 0.5))
        ellipse(draw, (82, 250, 112, 280), lighten(body, 0.4))
        ellipse(draw, (148, 256, 174, 282), lighten(body, 0.4))
        return
    ellipse(draw, (74, 172, 182, 300), body, outline, 7)
    ellipse(draw, (98, 224, 158, 294), colors["belly"])


def _head(draw, species: str, colors: dict) -> None:
    body, outline = colors["body"], colors["outline"]
    if species == "slime":
        return
    if species == "bird":
        ellipse(draw, (82, 78, 174, 196), body, outline, 7)
    elif species == "rabbit":
        ellipse(draw, (68, 88, 188, 222), body, outline, 7)
    else:
        ellipse(draw, (66, 78, 190, 216), body, outline, 7)


def _feet(draw, species: str, colors: dict, step: float) -> None:
    if species == "slime":
        return
    body, outline = colors["body"], colors["outline"]
    if species == "bird":
        for dx in (-24, 24):
            line(draw, [(128 + dx, 294), (128 + dx, 308)], colors["accent_dark"], 4)
            line(draw, [(128 + dx - 8, 310), (128 + dx, 306), (128 + dx + 8, 310)], colors["accent_dark"], 3)
        return
    ellipse(draw, (76 + step, 278, 126 + step, 310), body, outline, 6)
    ellipse(draw, (130 - step, 278, 180 - step, 310), body, outline, 6)


def _face(draw, species: str, colors: dict, *, blink: bool, wink: bool, sleepy: bool) -> None:
    eye, outline = colors["eye"], colors["outline"]
    if species == "bird":
        eyes = [(106, 140), (150, 140)]
        face_y = 158
    elif species == "slime":
        eyes = [(106, 180), (150, 180)]
        face_y = 202
    else:
        eyes = [(104, 148), (152, 148)]
        face_y = 164

    lx, ly = eyes[0]
    rx, ry = eyes[1]
    if sleepy:
        line(draw, [(lx - 7, ly + 2), (lx + 5, ly + 5)], outline, 4)
        line(draw, [(rx - 5, ry + 5), (rx + 7, ry + 2)], outline, 4)
    elif blink:
        line(draw, [(lx - 7, ly + 2), (lx + 5, ly + 3)], outline, 4)
        line(draw, [(rx - 5, ry + 3), (rx + 7, ry + 2)], outline, 4)
    elif wink:
        ellipse(draw, (lx - 6, ly - 10, lx + 6, ly + 10), eye)
        line(draw, [(rx - 7, ry + 2), (rx + 7, ry + 3)], outline, 4)
    else:
        ellipse(draw, (lx - 6, ly - 10, lx + 6, ly + 10), eye)
        ellipse(draw, (rx - 6, ry - 10, rx + 6, ry + 10), eye)

    if not (blink or sleepy or wink):
        ellipse(draw, (lx - 3, ly - 7, lx + 1, ly - 3), (255, 255, 255, 235))
        ellipse(draw, (rx - 3, ry - 7, rx + 1, ry - 3), (255, 255, 255, 235))

    ellipse(draw, (84, face_y - 4, 102, face_y + 8), BLUSH)
    ellipse(draw, (154, face_y - 4, 172, face_y + 8), BLUSH)

    if species == "bird":
        polygon(draw, [(120, face_y + 2), (136, face_y + 2), (128, face_y + 13)], colors["accent"], outline, 3)
    else:
        draw.polygon(
            [(sc(124), sc(face_y - 2)), (sc(132), sc(face_y - 2)), (sc(128), sc(face_y + 3))],
            fill=colors["accent_dark"],
        )
        draw.arc(box(118, face_y - 1, 128, face_y + 10), 20, 160, fill=outline, width=sc(2.5))
        draw.arc(box(128, face_y - 1, 138, face_y + 10), 20, 160, fill=outline, width=sc(2.5))

    if species in {"cat", "fox", "dog", "bear", "rabbit"}:
        for dy in (0, 6):
            line(draw, [(92, face_y + 4 + dy), (70, face_y + dy)], outline, 2)
            line(draw, [(164, face_y + 4 + dy), (186, face_y + dy)], outline, 2)


def _accessory(draw, spec: CharacterSpec, colors: dict, face_y: float) -> None:
    accent, dark, outline = colors["accent"], colors["accent_dark"], colors["outline"]
    neck = 200 if spec.species != "slime" else 230
    if spec.accessory == "bow":
        polygon(draw, [(128, neck), (104, neck - 12), (104, neck + 12)], accent, outline, 4)
        polygon(draw, [(128, neck), (152, neck - 12), (152, neck + 12)], accent, outline, 4)
        ellipse(draw, (122, neck - 6, 134, neck + 6), dark, outline, 3)
    elif spec.accessory == "scarf":
        if spec.species == "slime":
            return
        scarf_y = 186 if spec.species == "bird" else 212
        draw.rounded_rectangle(
            box(92, scarf_y, 164, scarf_y + 18),
            radius=sc(9),
            fill=accent,
            outline=outline,
            width=sc(4),
        )
        polygon(
            draw,
            [(148, scarf_y + 12), (164, scarf_y + 52), (142, scarf_y + 48)],
            accent,
            outline,
            4,
        )
        line(draw, [(158, scarf_y + 40), (144, scarf_y + 38)], dark, 4)
    elif spec.accessory == "glasses":
        ey = face_y - 16
        draw.rounded_rectangle(box(92, ey, 118, ey + 22), radius=sc(9), outline=accent, width=sc(3))
        draw.rounded_rectangle(box(138, ey, 164, ey + 22), radius=sc(9), outline=accent, width=sc(3))
        line(draw, [(118, ey + 11), (138, ey + 11)], accent, 3)
    elif spec.accessory == "headphones":
        draw.arc(box(74, 58, 182, 170), 180, 360, fill=accent, width=sc(9))
        ellipse(draw, (58, 112, 88, 168), accent, outline, 4)
        ellipse(draw, (168, 112, 198, 168), accent, outline, 4)
        ellipse(draw, (65, 124, 81, 154), dark)
        ellipse(draw, (175, 124, 191, 154), dark)
    elif spec.accessory == "hat":
        draw.pieslice(box(82, 48, 174, 132), 180, 360, fill=accent, outline=outline, width=sc(5))
        draw.rounded_rectangle(box(76, 116, 180, 134), radius=sc(8), fill=dark, outline=outline, width=sc(4))
        ellipse(draw, (150, 58, 172, 80), (255, 255, 255, 160))
    elif spec.accessory == "flower":
        cx, cy = 190, 96
        for index in range(5):
            angle = index * math.tau / 5
            px, py = cx + math.cos(angle) * 10, cy + math.sin(angle) * 10
            ellipse(draw, (px - 7, py - 7, px + 7, py + 7), accent, outline, 3)
        ellipse(draw, (cx - 5, cy - 5, cx + 5, cy + 5), (255, 226, 130, 255))


def _pattern(draw, spec: CharacterSpec, colors: dict, face_y: float) -> None:
    accent = colors["accent"]
    if spec.pattern == "patches":
        ellipse(draw, (86, 220, 126, 262), (accent[0], accent[1], accent[2], 210))
        ellipse(draw, (148, 96, 178, 122), (accent[0], accent[1], accent[2], 190))
    elif spec.pattern == "stripes":
        for index in range(3):
            line(draw, [(92 + index * 14, 190), (98 + index * 14, 214)], darken(colors["body"], 0.3), 5)
        line(draw, [(90, 112), (78, 124)], darken(colors["body"], 0.3), 5)
        line(draw, [(166, 112), (178, 124)], darken(colors["body"], 0.3), 5)
    elif spec.pattern == "star":
        star(draw, 128, 108, 10, (255, 214, 102, 255))
    elif spec.pattern == "heart":
        heart(draw, 128, 236, 14, accent)


def _glow(canvas: Image.Image, strength: float) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = CX * S, 180 * S
    for index, radius in enumerate(range(40, 150, 12)):
        alpha = int((5 + 3 * index) * strength)
        draw.ellipse(
            [
                cx - radius * S,
                cy - int(radius * 0.72) * S,
                cx + radius * S,
                cy + int(radius * 0.72) * S,
            ],
            fill=(255, 190, 220, max(0, min(80, alpha))),
        )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(5 * S)))


def _sparkles(canvas: Image.Image, strength: float) -> None:
    draw = ImageDraw.Draw(canvas)
    for index, (x, y) in enumerate([(78, 96), (188, 112), (70, 190), (196, 210)]):
        size = (5 + (index % 2) * 3) * S * (0.6 + strength * 0.5)
        cx, cy = x * S, y * S
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


def _shadow(canvas: Image.Image) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(box(68, 298, 188, 314), fill=(92, 72, 82, 48))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3 * S)))


def render_frame(
    spec: CharacterSpec,
    *,
    bob: float = 0.0,
    squash: tuple[float, float] = (1.0, 1.0),
    blink: bool = False,
    wink: bool = False,
    sleepy: bool = False,
    tail: float = 0.0,
    ear: float = 0.0,
    step: float = 0.0,
    ultra: float = 0.0,
) -> Image.Image:
    """Render one 256x320 RGBA frame."""
    colors = _palette(spec)
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    _tail(draw, spec.species, colors, tail)
    _ears(draw, spec.species, colors, ear, 148)
    _body(draw, spec.species, colors)
    _head(draw, spec.species, colors)
    _feet(draw, spec.species, colors, step)
    _face(draw, spec.species, colors, blink=blink, wink=wink, sleepy=sleepy)
    _pattern(draw, spec, colors, 148)
    _accessory(draw, spec, colors, 164)

    if squash != (1.0, 1.0):
        new_w, new_h = int(W * squash[0]), int(H * squash[1])
        layer = layer.resize((new_w * S, new_h * S), Image.LANCZOS)
        canvas = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        canvas.alpha_composite(layer, ((W * S - new_w * S) // 2, H * S - new_h * S))
        layer = canvas

    if bob:
        canvas = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        canvas.alpha_composite(layer, (0, sc(bob)))
        layer = canvas

    frame = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    _shadow(frame)
    if ultra:
        _glow(frame, ultra)
    frame.alpha_composite(layer)
    if ultra:
        _sparkles(frame, ultra)
    return frame.resize((W, H), Image.LANCZOS)


def build_frames(spec: CharacterSpec) -> dict[str, list[Image.Image]]:
    """Create all animation sequences for a text-described character."""
    idle = []
    for index, bob in enumerate([0, -1, -2, -2, -1, 0, 0, 0, -1, -2]):
        breathe = 0.008 if index in (2, 3) else 0.0
        idle.append(
            render_frame(
                spec,
                bob=bob,
                squash=(1.0 - breathe * 0.4, 1.0 + breathe),
                blink=index in (6, 7),
                tail=math.sin(index / 10 * math.tau) * 3,
            )
        )

    idle2 = []
    for index, bob in enumerate([0, -1, -2, -2, -1, 0, 0, -1, -2, -1]):
        idle2.append(
            render_frame(
                spec,
                bob=bob,
                wink=index in (4, 5, 6),
                tail=-math.sin(index / 10 * math.tau) * 4,
                ear=1.5 if index in (3, 4, 5) else 0.0,
            )
        )

    idle3 = []
    for index in range(12):
        idle3.append(
            render_frame(
                spec,
                bob=[0, -1, -1, 0, 0, -1, -2, -2, -1, 0, 0, -1][index],
                sleepy=True,
                tail=math.sin(index / 12 * math.tau) * 2,
            )
        )

    walk = []
    for index in range(8):
        walk.append(
            render_frame(
                spec,
                bob=[0, -2, -1, 0, 0, -2, -1, 0][index],
                step=0 if index % 2 == 0 else 2,
                tail=3 if index % 4 < 2 else -3,
                ear=1.0,
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
    jump = [render_frame(spec, bob=bob, squash=squash, tail=2 if index < 4 else -2) for index, (bob, squash) in enumerate(poses)]

    ultra = []
    for index in range(12):
        pulse = 0.55 + 0.45 * math.sin(index / 12 * math.tau) ** 2
        ultra.append(
            render_frame(
                spec,
                bob=-3 * pulse,
                squash=(1.0 + 0.03 * pulse, 1.0 + 0.03 * pulse),
                ultra=pulse,
                tail=4,
                ear=2,
            )
        )

    return {"idle": idle, "idle2": idle2, "idle3": idle3, "walk": walk, "jump": jump, "ultra": ultra}
