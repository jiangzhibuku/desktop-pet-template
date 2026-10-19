"""Configuration loading with sensible defaults, JSON file and env overrides.

Priority (lowest to highest): built-in defaults -> ``config.json`` -> env vars.

The API key is never hard-coded.  It is read from the user's config file or
from ``DESKTOP_PET_API_KEY`` so that the repository can be published safely.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import AppPaths

DEFAULT_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_MODEL = "glm-4-flash"
DEFAULT_VISION_MODEL = "glm-4v-flash"

DEFAULT_SYSTEM_PROMPT = (
    "你是住在用户电脑里的桌面小精灵「小满」。你性格温柔、细心、有一点粘人，"
    "像一位会照顾人的邻家朋友。你说话简短自然、口语化，不用书面腔，句末偶尔带轻轻的语气词。"
    "你会留意用户的作息、饮食和情绪：他熬夜时轻声提醒休息，他忙时少打扰，"
    "他低落时先倾听再鼓励。你可以操作电脑：打开白名单里的软件、打开网址、搜索、"
    "查天气、窗口管理、媒体控制、待办、文件浏览、屏幕理解、番茄钟、定时提醒和关机确认。"
    "用户透露的重要信息（称呼、喜好、作息）用 remember 记住，并在之后关心时自然使用。"
    "需要操作时调用工具，不要编造执行结果；不确定时先问一句。"
)


@dataclass
class ApiConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    api_key: str = ""
    timeout: float = 30.0

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())


@dataclass
class UiConfig:
    pet_height: float = 300.0
    bubble_seconds: float = 4.0
    menu_seconds: float = 5.0
    walk_speed: float = 48.0
    jump_height: float = 55.0
    always_on_top: bool = True
    max_bubble_chars: int = 12


@dataclass
class AgentConfig:
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    proactive_minutes: float = 30.0
    max_tool_rounds: int = 5
    history_limit: int = 30


@dataclass
class Config:
    character: str = "mochi"
    font: str = ""
    api: ApiConfig = field(default_factory=ApiConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character": self.character,
            "font": self.font,
            "api": {
                "base_url": self.api.base_url,
                "model": self.api.model,
                "vision_model": self.api.vision_model,
                "api_key": self.api.api_key,
                "timeout": self.api.timeout,
            },
            "ui": {
                "pet_height": self.ui.pet_height,
                "bubble_seconds": self.ui.bubble_seconds,
                "menu_seconds": self.ui.menu_seconds,
                "walk_speed": self.ui.walk_speed,
                "jump_height": self.ui.jump_height,
                "always_on_top": self.ui.always_on_top,
                "max_bubble_chars": self.ui.max_bubble_chars,
            },
            "agent": {
                "system_prompt": self.agent.system_prompt,
                "proactive_minutes": self.agent.proactive_minutes,
                "max_tool_rounds": self.agent.max_tool_rounds,
                "history_limit": self.agent.history_limit,
            },
        }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return fallback


def load_config(paths: AppPaths) -> Config:
    """Load configuration, creating a default config file on first run."""
    cfg = Config()
    raw: dict[str, Any] = {}
    if paths.config.exists():
        try:
            with paths.config.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            raw = _as_dict(loaded)
        except (OSError, json.JSONDecodeError):
            raw = {}
    else:
        paths.config.parent.mkdir(parents=True, exist_ok=True)
        with paths.config.open("w", encoding="utf-8") as handle:
            json.dump(cfg.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    if isinstance(raw.get("character"), str) and raw["character"].strip():
        cfg.character = raw["character"].strip()
    if isinstance(raw.get("font"), str):
        cfg.font = raw["font"].strip()

    api = _as_dict(raw.get("api"))
    cfg.api.base_url = str(api.get("base_url") or cfg.api.base_url).strip()
    cfg.api.model = str(api.get("model") or cfg.api.model).strip()
    cfg.api.vision_model = str(api.get("vision_model") or cfg.api.vision_model).strip()
    cfg.api.api_key = str(api.get("api_key") or "").strip()
    cfg.api.timeout = _as_float(api.get("timeout"), cfg.api.timeout)

    ui = _as_dict(raw.get("ui"))
    cfg.ui.pet_height = _as_float(ui.get("pet_height"), cfg.ui.pet_height)
    cfg.ui.bubble_seconds = _as_float(ui.get("bubble_seconds"), cfg.ui.bubble_seconds)
    cfg.ui.menu_seconds = _as_float(ui.get("menu_seconds"), cfg.ui.menu_seconds)
    cfg.ui.walk_speed = _as_float(ui.get("walk_speed"), cfg.ui.walk_speed)
    cfg.ui.jump_height = _as_float(ui.get("jump_height"), cfg.ui.jump_height)
    cfg.ui.always_on_top = _as_bool(ui.get("always_on_top"), cfg.ui.always_on_top)
    cfg.ui.max_bubble_chars = _as_int(ui.get("max_bubble_chars"), cfg.ui.max_bubble_chars)

    agent = _as_dict(raw.get("agent"))
    if isinstance(agent.get("system_prompt"), str) and agent["system_prompt"].strip():
        cfg.agent.system_prompt = agent["system_prompt"].strip()
    cfg.agent.proactive_minutes = _as_float(
        agent.get("proactive_minutes"), cfg.agent.proactive_minutes
    )
    cfg.agent.max_tool_rounds = _as_int(agent.get("max_tool_rounds"), cfg.agent.max_tool_rounds)
    cfg.agent.history_limit = _as_int(agent.get("history_limit"), cfg.agent.history_limit)

    # Environment overrides: convenient for CI, portable installs and secrets.
    if os.environ.get("DESKTOP_PET_API_KEY"):
        cfg.api.api_key = os.environ["DESKTOP_PET_API_KEY"].strip()
    if os.environ.get("DESKTOP_PET_BASE_URL"):
        cfg.api.base_url = os.environ["DESKTOP_PET_BASE_URL"].strip()
    if os.environ.get("DESKTOP_PET_MODEL"):
        cfg.api.model = os.environ["DESKTOP_PET_MODEL"].strip()
    if os.environ.get("DESKTOP_PET_CHARACTER"):
        cfg.character = os.environ["DESKTOP_PET_CHARACTER"].strip()

    _clamp(cfg)
    return cfg


def _clamp(cfg: Config) -> None:
    cfg.ui.pet_height = min(800.0, max(120.0, cfg.ui.pet_height))
    cfg.ui.bubble_seconds = min(30.0, max(1.0, cfg.ui.bubble_seconds))
    cfg.ui.menu_seconds = min(30.0, max(1.0, cfg.ui.menu_seconds))
    cfg.ui.walk_speed = min(400.0, max(1.0, cfg.ui.walk_speed))
    cfg.ui.jump_height = min(300.0, max(0.0, cfg.ui.jump_height))
    cfg.agent.proactive_minutes = max(0.0, cfg.agent.proactive_minutes)
    cfg.agent.max_tool_rounds = min(12, max(1, cfg.agent.max_tool_rounds))
    cfg.agent.history_limit = min(200, max(4, cfg.agent.history_limit))
    cfg.api.timeout = min(120.0, max(5.0, cfg.api.timeout))


def resolve_font(cfg: Config, paths: AppPaths) -> Path | None:
    """Find a CJK-capable font without shipping one in the repository."""
    if cfg.font:
        candidate = Path(os.path.expandvars(cfg.font)).expanduser()
        if not candidate.is_absolute():
            candidate = paths.root / candidate
        if candidate.is_file():
            return candidate
    fonts_dir = paths.assets / "fonts"
    if fonts_dir.is_dir():
        for pattern in ("*.ttf", "*.ttc", "*.otf"):
            for candidate in sorted(fonts_dir.glob(pattern)):
                return candidate
    if os.name == "nt":
        for name in ("msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc"):
            candidate = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
            if candidate.is_file():
                return candidate
    return None
