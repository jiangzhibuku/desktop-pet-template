#!/usr/bin/env python3
"""Generate the original placeholder character used by this project.

The project deliberately ships *original* placeholder art (CC0-1.0) instead of
the third-party animation packs that were used during early development.  Run
this script to regenerate every frame, the app icon and the README preview:

    python tools/generate_placeholder.py

Requirements: Pillow (already listed in requirements.txt).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CHAR_DIR = ROOT / "assets" / "characters" / "mochi"
DOCS_DIR = ROOT / "docs"
ASSETS_DIR = ROOT / "assets"

W, H = 256, 320          # logical canvas / frame size
S = 3                    # supersampling factor
CX = W // 2

OUTLINE = (74, 59, 66, 255)
BODY = (255, 246, 232, 255)
BODY_SHADE = (246, 227, 208, 255)
BELLY = (255, 252, 245, 255)
INNER_EAR = (247, 179, 192, 255)
BLUSH = (246, 158, 178, 210)
EYE = (62, 49, 56, 255)
BOW = (245, 139, 167, 255)
BOW_DARK = (214, 96, 130, 255)
SHADOW = (90, 70, 80, 46)


def sc(v: float) -> int:
    return int(round(v * S))


def box(x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
    return sc(x0), sc(y0), sc(x1), sc(y1)


def ellipse(draw: ImageDraw.ImageDraw, xy, fill=None, outline=None, width=0):
    draw.ellipse(box(*xy), fill=fill, outline=outline, width=sc(width))


def polygon(draw: ImageDraw.ImageDraw, points, fill=None, outline=None, width=0):
    pts = [(sc(x), sc(y)) for x, y in points]
    draw.polygon(pts, fill=fill)
    if outline:
        draw.line(pts + [pts[0]], fill=outline, width=sc(width), joint="curve")


def line(draw: ImageDraw.ImageDraw, points, fill, width, joint="curve"):
    draw.line([(sc(x), sc(y)) for x, y in points], fill=fill, width=sc(width), joint=joint)


def cat_layer(
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
    """Draw one upright cat pose on a transparent canvas."""
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # ---- tail (behind the body) -------------------------------------------
    tail_pts = [
        (176, 276),
        (204 + tail, 272),
        (216 + tail, 246),
        (211 + tail, 220),
        (198 + tail, 208),
    ]
    line(d, tail_pts, OUTLINE, 24)
    line(d, tail_pts, BODY, 14)

    # ---- ears -------------------------------------------------------------
    left_ear = [(74, 116), (86 + ear, 42), (132, 94)]
    right_ear = [(182, 116), (170 + ear, 42), (124, 94)]
    polygon(d, left_ear, BODY, OUTLINE, 7)
    polygon(d, right_ear, BODY, OUTLINE, 7)
    polygon(d, [(88, 104), (94 + ear, 64), (118, 96)], INNER_EAR)
    polygon(d, [(168, 104), (162 + ear, 64), (138, 96)], INNER_EAR)

    # ---- body / head ------------------------------------------------------
    ellipse(d, (66, 78, 190, 216), BODY, OUTLINE, 7)
    ellipse(d, (74, 172, 182, 300), BODY, OUTLINE, 7)
    ellipse(d, (98, 224, 158, 294), BELLY)

    # ---- feet -------------------------------------------------------------
    ellipse(d, (76 + step, 278, 126 + step, 310), BODY, OUTLINE, 6)
    ellipse(d, (130 - step, 278, 180 - step, 310), BODY, OUTLINE, 6)

    # ---- face -------------------------------------------------------------
    if sleepy:
        line(d, [(97, 150), (110, 154), (112, 150)], OUTLINE, 4)
        line(d, [(144, 154), (156, 150), (159, 150)], OUTLINE, 4)
    elif blink:
        line(d, [(97, 150), (110, 152)], OUTLINE, 4)
        line(d, [(146, 152), (159, 150)], OUTLINE, 4)
    elif wink:
        ellipse(d, (98, 138, 110, 158), EYE)
        line(d, [(145, 150), (159, 151)], OUTLINE, 4)
    else:
        ellipse(d, (97, 136, 111, 158), EYE)
        ellipse(d, (145, 136, 159, 158), EYE)

    if not (blink or sleepy):
        ellipse(d, (100, 139, 105, 144), (255, 255, 255, 235))
        ellipse(d, (148, 139, 153, 144), (255, 255, 255, 235))

    # blush
    ellipse(d, (82, 160, 100, 172), BLUSH)
    ellipse(d, (156, 160, 174, 172), BLUSH)

    # nose + mouth (small "ω")
    d.polygon([(sc(124), sc(162)), (sc(132), sc(162)), (sc(128), sc(167))], fill=BOW_DARK)
    d.arc(box(118, 163, 128, 174), 20, 160, fill=OUTLINE, width=sc(2.5))
    d.arc(box(128, 163, 138, 174), 20, 160, fill=OUTLINE, width=sc(2.5))

    # whiskers
    line(d, [(96, 168), (72, 164)], OUTLINE, 2)
    line(d, [(96, 174), (72, 176)], OUTLINE, 2)
    line(d, [(160, 168), (184, 164)], OUTLINE, 2)
    line(d, [(160, 174), (184, 176)], OUTLINE, 2)

    # ---- bow --------------------------------------------------------------
    polygon(d, [(128, 200), (104, 188), (104, 212)], BOW, OUTLINE, 4)
    polygon(d, [(128, 200), (152, 188), (152, 212)], BOW, OUTLINE, 4)
    ellipse(d, (122, 194, 134, 206), BOW_DARK, OUTLINE, 3)

    if ultra:
        # little sparkle badge on the forehead
        cx, cy = 128, 118
        for dx, dy in ((0, -10), (10, 0), (0, 10), (-10, 0)):
            d.polygon(
                [
                    (sc(cx + dx * 0.35), sc(cy + dy * 0.35)),
                    (sc(cx + dx * 0.2 + 2), sc(cy + dy * 0.2 + 2)),
                    (sc(cx + dx), sc(cy + dy)),
                    (sc(cx + dx * 0.2 - 2), sc(cy + dy * 0.2 - 2)),
                ],
                fill=(255, 214, 102, 255),
            )

    # apply squash / stretch, anchored at the feet
    if squash != (1.0, 1.0):
        sx, sy = squash
        new_w, new_h = int(W * sx), int(H * sy)
        layer = layer.resize((new_w * S, new_h * S), Image.LANCZOS)
        canvas = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        canvas.alpha_composite(layer, ((W * S - new_w * S) // 2, H * S - new_h * S))
        layer = canvas

    if bob:
        canvas = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        canvas.alpha_composite(layer, (0, sc(bob)))
        layer = canvas

    return layer


def shadow_layer(lift: float = 0.0) -> Image.Image:
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    grow = max(0.0, 1.0 - lift / 120.0)
    spread = 60 * grow
    ellipse(
        d,
        (CX - spread, 298, CX + spread, 314),
        fill=SHADOW,
    )
    return layer.filter(ImageFilter.GaussianBlur(sc(3)))


def glow_layer(strength: float) -> Image.Image:
    layer = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, radius in enumerate(range(42, 150, 14)):
        alpha = int((6 + 3 * i) * strength)
        ellipse(
            d,
            (CX - radius, 178 - radius * 0.72, CX + radius, 178 + radius * 0.72),
            fill=(255, 190, 220, max(0, min(80, alpha))),
        )
    return layer.filter(ImageFilter.GaussianBlur(sc(6)))


def frame(
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
    lift: float = 0.0,
) -> Image.Image:
    canvas = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    canvas.alpha_composite(shadow_layer(lift))
    if ultra:
        canvas.alpha_composite(glow_layer(ultra))
    canvas.alpha_composite(
        cat_layer(
            bob=bob,
            squash=squash,
            blink=blink,
            wink=wink,
            sleepy=sleepy,
            tail=tail,
            ear=ear,
            step=step,
            ultra=ultra,
        )
    )
    return canvas.resize((W, H), Image.LANCZOS)


def save_frames(folder: str, frames: list[Image.Image]) -> None:
    out = CHAR_DIR / folder
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    for i, img in enumerate(frames):
        img.save(out / f"{folder}_{i:02d}.png", optimize=True)


def build_animations() -> dict[str, int]:
    counts: dict[str, int] = {}

    # idle: gentle breathing, two blinks
    frames = []
    for i in range(10):
        bob = [0, -1, -2, -2, -1, 0, 0, 0, -1, -2][i]
        frames.append(
            frame(
                bob=bob,
                blink=i in (6, 7),
                tail=math.sin(i / 10 * math.tau) * 3,
                ear=0.0,
            )
        )
    save_frames("idle", frames)
    counts["idle"] = len(frames)

    # idle2: curious head tilt + wink
    frames = []
    for i in range(10):
        frames.append(
            frame(
                bob=[0, -1, -2, -2, -1, 0, 0, -1, -2, -1][i],
                wink=i in (4, 5, 6),
                tail=-math.sin(i / 10 * math.tau) * 4,
                ear=1.5 if i in (3, 4, 5) else 0.0,
            )
        )
    save_frames("idle2", frames)
    counts["idle2"] = len(frames)

    # idle3: sleepy
    frames = []
    for i in range(12):
        frames.append(
            frame(
                bob=[0, -1, -1, 0, 0, -1, -2, -2, -1, 0, 0, -1][i],
                sleepy=True,
                tail=math.sin(i / 12 * math.tau) * 2,
            )
        )
    save_frames("idle3", frames)
    counts["idle3"] = len(frames)

    # walk: 8-frame loop with alternating feet
    frames = []
    for i in range(8):
        frames.append(
            frame(
                bob=[0, -2, -1, 0, 0, -2, -1, 0][i],
                step=0 if i % 2 == 0 else 2,
                tail=3 if i % 4 < 2 else -3,
                ear=1.0,
            )
        )
    save_frames("walk", frames)
    counts["walk"] = len(frames)

    # jump: crouch, stretch, air, land
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
    frames = [
        frame(bob=b, squash=sq, tail=2 if i < 4 else -2, lift=abs(b))
        for i, (b, sq) in enumerate(poses)
    ]
    save_frames("jump", frames)
    counts["jump"] = len(frames)

    # ultra: glowing power-up
    frames = []
    for i in range(12):
        pulse = 0.55 + 0.45 * math.sin(i / 12 * math.tau) ** 2
        sq = (1.0 + 0.03 * pulse, 1.0 + 0.03 * pulse)
        frames.append(frame(bob=-3 * pulse, squash=sq, ultra=pulse, tail=4, ear=2))
    save_frames("ultra", frames)
    counts["ultra"] = len(frames)
    return counts


def find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_preview() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    scale = 2
    width, height = 900, 560
    bg = Image.new("RGBA", (width * scale, height * scale))
    d = ImageDraw.Draw(bg)
    for y in range(height * scale):
        t = y / (height * scale)
        d.line([(0, y), (width * scale, y)], fill=(int(255 - 8 * t), int(242 + 6 * t), int(246 + 6 * t)))
    for cx, cy, r, color in [
        (110, 80, 90, (255, 220, 232, 255)),
        (790, 120, 120, (222, 240, 255, 255)),
        (770, 480, 90, (255, 236, 214, 255)),
    ]:
        d.ellipse(
            [(cx - r) * scale, (cy - r) * scale, (cx + r) * scale, (cy + r) * scale],
            fill=color,
        )

    idle = sorted((CHAR_DIR / "idle").glob("*.png"))[0]
    pet = Image.open(idle).convert("RGBA").resize((int(W * 1.35), int(H * 1.35)), Image.LANCZOS)
    bg.alpha_composite(pet, (110 * scale, 120 * scale))

    # speech bubble; its tail points left towards the pet
    bubble = Image.new("RGBA", (420 * scale, 140 * scale), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bubble)
    left, top, right, bottom = 24 * scale, 6 * scale, 408 * scale, 120 * scale
    bd.rounded_rectangle(
        [left, top, right, bottom],
        radius=26 * scale,
        fill=(255, 255, 255, 242),
        outline=(255, 183, 205, 255),
        width=2 * scale,
    )
    tail = [(34 * scale, 76 * scale), (0 * scale, 102 * scale), (38 * scale, 102 * scale)]
    bd.polygon(tail, fill=(255, 255, 255, 242))
    bd.line(
        [(34 * scale, 76 * scale), (0 * scale, 102 * scale), (38 * scale, 102 * scale)],
        fill=(255, 183, 205, 255),
        width=2 * scale,
        joint="curve",
    )
    bg.alpha_composite(bubble, (480 * scale, 128 * scale))

    font = find_font(24 * scale)
    bd2 = ImageDraw.Draw(bg)
    bd2.text((506 * scale, 166 * scale), "今天也要好好休息呀～", font=font, fill=(90, 70, 80))

    title_font = find_font(18 * scale)
    bd2.text((40 * scale, 28 * scale), "Desktop Pet · Mochi", font=title_font, fill=(150, 120, 135))
    bg.resize((width, height), Image.LANCZOS).save(DOCS_DIR / "preview.png", optimize=True)

    # animated preview (idle loop)
    idle_frames = [Image.open(p).convert("RGBA") for p in sorted((CHAR_DIR / "idle").glob("*.png"))]
    gif_frames = []
    for img in idle_frames:
        canvas = Image.new("RGBA", (W, H), (253, 243, 247, 255))
        canvas.alpha_composite(img)
        gif_frames.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=64))
    gif_frames[0].save(
        DOCS_DIR / "preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=90,
        loop=0,
        optimize=True,
    )


def build_ui_asset() -> None:
    ui_dir = ASSETS_DIR / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    size = 64
    scale = 4
    image = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        [0, 0, size * scale - 1, size * scale - 1],
        radius=14 * scale,
        fill=(255, 249, 251, 255),
        outline=(248, 196, 211, 255),
        width=2 * scale,
    )
    image.resize((size, size), Image.LANCZOS).save(ui_dir / "popup_bg.png", optimize=True)


def build_icon() -> None:
    face = cat_layer()
    small = face.resize((W, H), Image.LANCZOS).crop((36, 60, 220, 244)).resize(
        (256, 256), Image.LANCZOS
    )
    bg = Image.new("RGBA", (256, 256), (255, 246, 232, 255))
    bg.alpha_composite(small, (0, 0))
    bg.save(ASSETS_DIR / "icon.png", optimize=True)
    bg.save(
        ASSETS_DIR / "icon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    counts = build_animations()
    meta = {
        "name": "Mochi",
        "description": "Original placeholder character generated by tools/generate_placeholder.py",
        "author": "Desktop Pet contributors",
        "license": "CC0-1.0",
        "frame_width": W,
        "frame_height": H,
        "fps": 12,
        "base_height": 300,
        "ultra_scale": 1.35,
        "animations": {key: key for key in counts},
    }
    (CHAR_DIR / "character.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build_preview()
    build_icon()
    build_ui_asset()
    total = sum(counts.values())
    print(f"Generated {total} frames in {len(counts)} animations -> {CHAR_DIR}")
    print(f"Preview -> {DOCS_DIR / 'preview.png'}")
    print(f"Icon    -> {ASSETS_DIR / 'icon.ico'}")


if __name__ == "__main__":
    main()
