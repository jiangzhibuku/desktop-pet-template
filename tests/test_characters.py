from __future__ import annotations

import json

import pytest
from PIL import Image

from desktop_pet.characters import CharacterError, available_characters, load_character
from desktop_pet.paths import build_paths


def make_paths(tmp_path):
    root = tmp_path / "repo"
    (root / "assets" / "characters").mkdir(parents=True)
    return build_paths(root=root, data=tmp_path / "data")


def make_frame(path, color=(255, 0, 0, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (8, 10), color).save(path)


def test_frame_order_is_natural(tmp_path):
    paths = make_paths(tmp_path)
    character = paths.characters / "cat"
    for name in ("idle_20.png", "idle_2.png", "idle_10.png", "idle_1.png"):
        make_frame(character / "idle" / name)

    loaded = load_character("cat", paths)

    names = [path.name for path in loaded.animations["idle"]]
    assert names == ["idle_1.png", "idle_2.png", "idle_10.png", "idle_20.png"]


def test_metadata_and_idle_fallback(tmp_path):
    paths = make_paths(tmp_path)
    character = paths.characters / "cat"
    make_frame(character / "idle" / "a.png")
    (character / "character.json").write_text(
        json.dumps({"name": "Cat", "fps": 18, "ultra_scale": 1.5}), encoding="utf-8"
    )

    loaded = load_character("cat", paths)

    assert loaded.name == "Cat"
    assert loaded.fps == 18
    assert loaded.ultra_scale == 1.5
    # idle2/idle3 are aliases of idle when not supplied
    assert loaded.animations["idle2"] == loaded.animations["idle"]
    assert loaded.animations["idle3"] == loaded.animations["idle"]


def test_folder_aliases_are_accepted(tmp_path):
    paths = make_paths(tmp_path)
    character = paths.characters / "legacy"
    make_frame(character / "daiji" / "1.png")
    make_frame(character / "khqn" / "1.png")
    make_frame(character / "tiaoyue" / "1.png")
    make_frame(character / "dazhao" / "1.png")

    loaded = load_character("legacy", paths)

    assert loaded.frames("walk")
    assert loaded.frames("jump")
    assert loaded.frames("ultra")


def test_missing_idle_raises(tmp_path):
    paths = make_paths(tmp_path)
    (paths.characters / "empty").mkdir(parents=True)

    with pytest.raises(CharacterError):
        load_character("empty", paths)


def test_unknown_key_falls_back_to_mochi(tmp_path):
    paths = make_paths(tmp_path)
    make_frame(paths.characters / "mochi" / "idle" / "1.png")

    loaded = load_character("does-not-exist", paths)

    assert loaded.key == "mochi"


def test_available_characters(tmp_path):
    paths = make_paths(tmp_path)
    (paths.characters / "b").mkdir()
    (paths.characters / "a").mkdir()

    assert available_characters(paths) == ["a", "b"]
