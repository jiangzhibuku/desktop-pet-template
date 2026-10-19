from __future__ import annotations

from PIL import Image, ImageDraw

from desktop_pet.creator import cutout
from desktop_pet.creator.cutout import prepare
from desktop_pet.creator.image_pack import frames_from_image


def make_png(path, *, transparent=True, size=(200, 200)):
    image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 50, 150, 150), fill=(220, 80, 90, 255))
    image.save(path)
    return path


def test_transparent_png_uses_alpha(tmp_path):
    path = make_png(tmp_path / "transparent.png", transparent=True)

    result = prepare(path, mode="auto")

    assert result.method == "alpha"
    assert result.image.size == (101, 101)


def test_opaque_png_flood_fills_connected_background(tmp_path):
    path = make_png(tmp_path / "white.png", transparent=False)

    result = prepare(path, mode="auto", tolerance=24)

    assert result.method == "flood"
    assert result.image.size == (101, 101)
    assert result.image.getchannel("A").getextrema()[1] == 255


def test_none_keeps_full_opaque_image(tmp_path):
    path = make_png(tmp_path / "white.png", transparent=False)

    result = prepare(path, mode="none")

    assert result.method == "none"
    assert result.image.size == (200, 200)


def test_rembg_without_package_falls_back(tmp_path, monkeypatch):
    path = make_png(tmp_path / "white.png", transparent=False)
    monkeypatch.setattr(cutout, "rembg_available", lambda: False)

    result = prepare(path, mode="rembg")

    assert result.method == "flood"
    assert "未安装 rembg" in result.notices[0]


def test_rembg_failure_falls_back(tmp_path, monkeypatch):
    path = make_png(tmp_path / "white.png", transparent=False)
    monkeypatch.setattr(cutout, "rembg_available", lambda: True)

    def boom(image, model):
        raise RuntimeError("model download failed")

    monkeypatch.setattr(cutout, "_remove_with_rembg", boom)

    result = prepare(path, mode="rembg")

    assert result.method == "flood"
    assert "rembg 失败" in result.notices[0]


def test_frames_from_image_collects_notices(tmp_path):
    path = make_png(tmp_path / "white.png", transparent=False)
    notices: list[str] = []

    frames = frames_from_image(path, tolerance=24, notices=notices)

    assert len(frames["idle"]) == 10
    assert frames["idle"][0].size == (256, 320)
    assert isinstance(notices, list)

