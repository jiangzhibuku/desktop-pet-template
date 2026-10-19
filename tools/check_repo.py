#!/usr/bin/env python3
"""Pre-flight checks for publishing this repository.

Run from the repository root:

    python tools/check_repo.py

It fails (exit code 1) when it finds something that should not be pushed:
hard-coded secrets, huge files, personal data, or third-party asset folders.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".localdata",
    ".testtmp",
    ".offline",
    ".testdeps",
    ".kivy",
}
TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".json",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".spec",
    ".bat",
    ".ps1",
    ".cfg",
    ".ini",
}
PERSONAL_FILES = {
    "config.json",
    "memory.json",
    "todos.json",
    "stats.json",
    "whitelist.json",
    "operations.log",
    "pet_crash.log",
    "pet_debug.log",
    "screen_shot.png",
}
REQUIRED_PATHS = [
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "requirements.txt",
    "run.py",
    "create_pet.py",
    "src/desktop_pet/__main__.py",
    "src/desktop_pet/agent.py",
    "assets/characters/mochi/character.json",
    "assets/ui/popup_bg.png",
    "assets/LICENSE",
    "docs/ASSETS.md",
    "docs/CREATOR.md",
]
FORBIDDEN_ASSET_DIRS = {"daiji", "dazhao", "khqn", "tiaoyue", "ziti"}

SECRET_PATTERNS = [
    re.compile(r"[0-9a-fA-F]{32}\.[A-Za-z0-9]{16,}"),          # Zhipu style key
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),                   # OpenAI style key
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),                # hard-coded bearer
    re.compile(r"api_key\s*[:=]\s*['\"][^'\"]{12,}['\"]"),      # obvious key literal
]
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_REPO_BYTES = 50 * 1024 * 1024


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return files


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    errors: list[str] = []
    warnings: list[str] = []

    for required in REQUIRED_PATHS:
        if not (ROOT / required).exists():
            errors.append(f"缺少必需文件：{required}")

    total = 0
    for path in iter_files():
        relative = path.relative_to(ROOT)
        size = path.stat().st_size
        total += size

        if path.name in PERSONAL_FILES:
            errors.append(f"个人数据文件不应提交：{relative}")
        if size > MAX_FILE_BYTES:
            errors.append(f"文件超过 5 MB：{relative} ({size / 1024 / 1024:.1f} MB)")

        if path.suffix.lower() in TEXT_EXTENSIONS:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    errors.append(f"疑似密钥：{relative}（匹配 {pattern.pattern}）")
                    break
            if "你的 API Key" in text or "YOUR_API_KEY" in text:
                pass  # documented placeholders are fine

    characters = ROOT / "assets" / "characters"
    if characters.is_dir():
        for child in characters.iterdir():
            if not child.is_dir():
                continue
            if child.name in FORBIDDEN_ASSET_DIRS:
                errors.append(f"第三方素材目录不应提交：assets/characters/{child.name}")
            elif child.name != "mochi":
                if not (child / "LICENSE.txt").exists():
                    warnings.append(
                        f"自定义角色 {child.name} 没有 LICENSE.txt，请确认有权分发"
                    )

    if total > MAX_REPO_BYTES:
        errors.append(f"仓库体积 {total / 1024 / 1024:.1f} MB 超过 50 MB")

    print(f"检查了 {len(iter_files())} 个文件，总计 {total / 1024 / 1024:.2f} MB")
    for warning in warnings:
        print("WARN  " + warning)
    for error in errors:
        print("ERROR " + error)

    if errors:
        print(f"\n失败：{len(errors)} 个问题需要处理。")
        return 1
    print("通过：没有发现密钥、超大文件或第三方素材目录。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
