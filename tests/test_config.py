from __future__ import annotations

import json

from desktop_pet.config import load_config
from desktop_pet.paths import build_paths


def make_paths(tmp_path):
    root = tmp_path / "repo"
    (root / "assets" / "characters").mkdir(parents=True)
    return build_paths(root=root, data=tmp_path / "data")


def test_first_run_creates_config_without_key(tmp_path):
    paths = make_paths(tmp_path)
    cfg = load_config(paths)

    assert paths.config.is_file()
    assert cfg.api.api_key == ""
    assert cfg.api.configured is False
    assert cfg.character == "mochi"


def test_env_overrides_file_and_defaults(tmp_path, monkeypatch):
    paths = make_paths(tmp_path)
    paths.config.write_text(
        json.dumps(
            {
                "character": "file-cat",
                "api": {"model": "file-model"},
                "ui": {"pet_height": 260},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DESKTOP_PET_API_KEY", "env-key")
    monkeypatch.setenv("DESKTOP_PET_MODEL", "env-model")
    monkeypatch.setenv("DESKTOP_PET_CHARACTER", "env-cat")

    cfg = load_config(paths)

    assert cfg.api.api_key == "env-key"
    assert cfg.api.configured is True
    assert cfg.api.model == "env-model"
    assert cfg.character == "env-cat"
    assert cfg.ui.pet_height == 260


def test_values_are_clamped(tmp_path):
    paths = make_paths(tmp_path)
    paths.config.write_text(
        json.dumps(
            {
                "ui": {"pet_height": 9999, "bubble_seconds": 0, "max_bubble_chars": 1},
                "agent": {"max_tool_rounds": 99, "history_limit": 1},
            }
        ),
        encoding="utf-8",
    )

    cfg = load_config(paths)

    assert cfg.ui.pet_height == 800
    assert cfg.ui.bubble_seconds == 1
    assert cfg.ui.max_bubble_chars == 1
    assert cfg.agent.max_tool_rounds == 12
    assert cfg.agent.history_limit == 4


def test_broken_json_falls_back_to_defaults(tmp_path):
    paths = make_paths(tmp_path)
    paths.config.write_text("{not json", encoding="utf-8")

    cfg = load_config(paths)

    assert cfg.api.base_url.startswith("https://")
    assert cfg.character == "mochi"
