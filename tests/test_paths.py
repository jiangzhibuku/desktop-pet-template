from __future__ import annotations

from desktop_pet.paths import build_paths, user_data_dir


def test_data_dir_can_be_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("DESKTOP_PET_HOME", str(tmp_path / "portable"))

    assert user_data_dir() == (tmp_path / "portable").resolve()

    paths = build_paths(root=tmp_path / "repo", data=user_data_dir())

    assert paths.data.is_dir()
    assert paths.config == paths.data / "config.json"
    assert paths.logs.is_dir()
    assert paths.screenshots.is_dir()
