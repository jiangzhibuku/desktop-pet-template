from __future__ import annotations

from pathlib import Path

from PIL import Image

from desktop_pet.characters import load_character
from desktop_pet.config import ApiConfig, Config, load_config
from desktop_pet.creator.ai import generate_image, spec_from_prompt
from desktop_pet.creator.draw import build_frames
from desktop_pet.creator.image_pack import frames_from_image
from desktop_pet.creator.pack import save_pack, slugify
from desktop_pet.creator.pipeline import import_frames
from desktop_pet.creator.spec import CharacterSpec, parse_prompt
from desktop_pet.paths import build_paths


def make_paths(tmp_path):
    root = tmp_path / "repo"
    (root / "assets" / "characters").mkdir(parents=True, exist_ok=True)
    return build_paths(root=root, data=tmp_path / "data")


def test_parse_chinese_prompt():
    spec = parse_prompt("一只白色小猫，戴红围巾，蓝眼睛，叫雪球")

    assert spec.name == "雪球"
    assert spec.species == "cat"
    assert spec.body_color == "#FFF6E8"
    assert spec.accent_color == "#E88A8A"
    assert spec.eye_color == "#A9D4F5"
    assert spec.accessory == "scarf"


def test_parse_english_prompt():
    spec = parse_prompt("a black cat with green eyes and a red scarf named Midnight")

    assert spec.name == "Midnight"
    assert spec.species == "cat"
    assert spec.body_color == "#4B4B52"
    assert spec.eye_color == "#A8D8B9"
    assert spec.accessory == "scarf"


def test_parse_defaults_and_normalization():
    spec = CharacterSpec(name="", species="unknown", body_color="not-a-color")
    spec.normalized()

    assert spec.name == "小可爱"
    assert spec.species == "cat"
    assert spec.body_color == "#FFF6E8"


def test_slugify():
    assert slugify("My Pet!") == "my_pet"
    assert slugify("  雪球  ") == "雪球"
    assert slugify("!!!") == "pet"


def test_draw_frames_are_transparent_and_complete():
    spec = parse_prompt("灰色兔子，戴圆眼镜，星星花纹")
    frames = build_frames(spec)

    assert set(frames) == {"idle", "idle2", "idle3", "walk", "jump", "ultra"}
    assert len(frames["idle"]) == 10
    assert len(frames["idle3"]) == 12
    assert len(frames["walk"]) == 8
    assert frames["idle"][0].size == (256, 320)
    assert frames["idle"][0].mode == "RGBA"


def test_save_pack_and_reload(tmp_path):
    paths = make_paths(tmp_path)
    spec = parse_prompt("白色小猫，戴红围巾，蓝眼睛，叫雪球")
    frames = build_frames(spec)

    result = save_pack(
        spec,
        frames,
        paths,
        source={"type": "prompt", "prompt": spec.description},
    )

    assert result.directory.is_dir()
    assert (result.directory / "character.json").is_file()
    assert (result.directory / "preview.png").is_file()
    assert (result.directory / "SOURCE.txt").is_file()
    assert load_config(paths).character == result.key

    loaded = load_character(result.key, paths)
    assert loaded.name == "雪球"
    assert loaded.animations["idle"]
    assert loaded.frames("ultra")


def test_image_pack_from_transparent_png(tmp_path):
    image_path = tmp_path / "cat.png"
    image = Image.new("RGBA", (200, 260), (0, 0, 0, 0))
    for x in range(40, 160):
        for y in range(40, 240):
            image.putpixel((x, y), (240, 180, 160, 255))
    image.save(image_path)

    frames = frames_from_image(image_path)

    assert len(frames["idle"]) == 10
    assert frames["idle"][0].size == (256, 320)
    assert frames["idle"][0].getchannel("A").getextrema()[1] > 0


def test_import_linked_frames(tmp_path):
    paths = make_paths(tmp_path)
    source = tmp_path / "old_pack"
    for name in ("idle", "walk"):
        folder = source / name
        folder.mkdir(parents=True, exist_ok=True)
        for index in range(2):
            Image.new("RGBA", (64, 80), (255, 200, 210, 255)).save(folder / f"{name}_{index}.png")

    result = import_frames(source, "旧角色", paths, link=True)
    loaded = load_character(result.key, paths)

    assert loaded.frames("idle")
    assert loaded.frames("walk")
    assert loaded.frames("idle")[0].is_absolute()


def test_ai_helpers_fall_back_without_key(tmp_path):
    config = Config(api=ApiConfig(api_key=""), character="mochi")

    assert spec_from_prompt("white cat", config) is None
    assert generate_image("white cat", config, tmp_path / "x.png") is None
