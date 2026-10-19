"""Character specification and a small Chinese/English prompt parser.

The parser is intentionally rule-based: it works offline, is deterministic and
only needs the keywords listed below.  When an API key is available the CLI can
optionally ask an LLM to produce the same JSON structure (see ``ai.py``); the
rule parser remains the fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

COLOR_WORDS: dict[str, tuple[str, str]] = {
    # key: (hex, Chinese label)
    "奶油": ("#FFF1D6", "奶油"),
    "cream": ("#FFF1D6", "奶油"),
    "米色": ("#FFF1D6", "米色"),
    "beige": ("#FFF1D6", "米色"),
    "雪白": ("#FFFFFF", "雪白"),
    "白色": ("#FFF6E8", "白"),
    "white": ("#FFF6E8", "白"),
    "白": ("#FFF6E8", "白"),
    "黑色": ("#4B4B52", "黑"),
    "black": ("#4B4B52", "黑"),
    "黑": ("#4B4B52", "黑"),
    "银灰": ("#D8DEE6", "银灰"),
    "灰色": ("#C9CDD4", "灰"),
    "grey": ("#C9CDD4", "灰"),
    "gray": ("#C9CDD4", "灰"),
    "灰": ("#C9CDD4", "灰"),
    "橘色": ("#F6B26B", "橘"),
    "橙色": ("#F6B26B", "橘"),
    "orange": ("#F6B26B", "橘"),
    "橘": ("#F6B26B", "橘"),
    "橙": ("#F6B26B", "橘"),
    "黄色": ("#F7D774", "黄"),
    "yellow": ("#F7D774", "黄"),
    "金黄": ("#F2C14E", "金"),
    "黄": ("#F7D774", "黄"),
    "粉色": ("#F7B6C2", "粉"),
    "pink": ("#F7B6C2", "粉"),
    "桃粉": ("#F5A8B8", "桃粉"),
    "粉": ("#F7B6C2", "粉"),
    "蓝色": ("#A9D4F5", "蓝"),
    "blue": ("#A9D4F5", "蓝"),
    "天蓝": ("#BFE3FA", "天蓝"),
    "蓝": ("#A9D4F5", "蓝"),
    "绿色": ("#A8D8B9", "绿"),
    "green": ("#A8D8B9", "绿"),
    "薄荷": ("#A8D8B9", "薄荷"),
    "绿": ("#A8D8B9", "绿"),
    "紫色": ("#C9B6E4", "紫"),
    "purple": ("#C9B6E4", "紫"),
    "紫": ("#C9B6E4", "紫"),
    "棕色": ("#C89F7B", "棕"),
    "brown": ("#C89F7B", "棕"),
    "咖啡": ("#A98262", "咖啡"),
    "棕": ("#C89F7B", "棕"),
    "红色": ("#E88A8A", "红"),
    "red": ("#E88A8A", "红"),
    "红": ("#E88A8A", "红"),
    "金色": ("#F2C14E", "金"),
    "gold": ("#F2C14E", "金"),
    "silver": ("#D8DEE6", "银"),
    "银": ("#D8DEE6", "银"),
}

SPECIES_WORDS: dict[str, str] = {
    "史莱姆": "slime",
    "slime": "slime",
    "小猫": "cat",
    "cat": "cat",
    "kitten": "cat",
    "猫": "cat",
    "小狗": "dog",
    "dog": "dog",
    "puppy": "dog",
    "狗": "dog",
    "兔子": "rabbit",
    "rabbit": "rabbit",
    "bunny": "rabbit",
    "兔": "rabbit",
    "狐狸": "fox",
    "fox": "fox",
    "狐": "fox",
    "小熊": "bear",
    "bear": "bear",
    "熊": "bear",
    "小鸟": "bird",
    "bird": "bird",
    "鸟": "bird",
}

SPECIES_LABELS = {
    "cat": "猫",
    "dog": "狗",
    "rabbit": "兔",
    "fox": "狐",
    "bear": "熊",
    "bird": "鸟",
    "slime": "史莱姆",
}

ACCESSORY_WORDS: dict[str, str] = {
    "蝴蝶结": "bow",
    "bowtie": "bow",
    "bow": "bow",
    "围巾": "scarf",
    "scarf": "scarf",
    "眼镜": "glasses",
    "glasses": "glasses",
    "耳机": "headphones",
    "headphones": "headphones",
    "帽子": "hat",
    "hat": "hat",
    "cap": "hat",
    "小花": "flower",
    "flower": "flower",
}

PATTERN_WORDS: dict[str, str] = {
    "条纹": "stripes",
    "stripes": "stripes",
    "花纹": "patches",
    "斑": "patches",
    "patches": "patches",
    "星星": "star",
    "star": "star",
    "爱心": "heart",
    "心": "heart",
    "heart": "heart",
}

ALLOWED_SPECIES = set(SPECIES_LABELS)
ALLOWED_ACCESSORIES = {"none", "bow", "scarf", "glasses", "headphones", "hat", "flower"}
ALLOWED_PATTERNS = {"none", "patches", "stripes", "star", "heart"}

_COLOR_LOOKUP = {key.lower(): value[0] for key, value in COLOR_WORDS.items()}
_COLOR_LABEL = {key.lower(): value[1] for key, value in COLOR_WORDS.items()}
_COLOR_ALT = "|".join(
    re.escape(key) for key in sorted(COLOR_WORDS, key=len, reverse=True)
)
_COLOR_RE = re.compile(f"({_COLOR_ALT})", re.IGNORECASE)
_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def _first_word(text: str, mapping: dict[str, str]) -> tuple[str, re.Match] | None:
    pattern = re.compile(
        "|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True)),
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return mapping[match.group(0).lower()], match


def _cut(text: str, match: re.Match) -> str:
    """Blank out a matched span while keeping the rest of the text intact."""
    return text[: match.start()] + " " * (match.end() - match.start()) + text[match.end() :]


def _color(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    value = value.strip()
    if value.lower() in _COLOR_LOOKUP:
        return _COLOR_LOOKUP[value.lower()]
    if _HEX_RE.match(value):
        return value if value.startswith("#") else "#" + value
    return fallback


def _color_label(value: str) -> str:
    return _COLOR_LABEL.get(value.lower(), "")


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------


@dataclass
class CharacterSpec:
    name: str = "Mochi"
    species: str = "cat"
    body_color: str = "#FFF6E8"
    inner_color: str = "#F7B6C2"
    eye_color: str = "#3E3138"
    accent_color: str = "#F58BA7"
    accessory: str = "none"
    pattern: str = "none"
    description: str = ""
    author: str = "unknown"
    license: str = "unknown"
    fps: float = 12.0
    ultra_scale: float = 1.35
    extras: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "CharacterSpec":
        self.species = self.species if self.species in ALLOWED_SPECIES else "cat"
        self.accessory = (
            self.accessory if self.accessory in ALLOWED_ACCESSORIES else "none"
        )
        self.pattern = self.pattern if self.pattern in ALLOWED_PATTERNS else "none"
        self.body_color = _color(self.body_color, "#FFF6E8")
        self.inner_color = _color(self.inner_color, "#F7B6C2")
        self.eye_color = _color(self.eye_color, "#3E3138")
        self.accent_color = _color(self.accent_color, "#F58BA7")
        self.name = (self.name or "小可爱").strip()[:24]
        self.description = (self.description or "").strip()
        self.author = (self.author or "unknown").strip()[:60]
        self.license = (self.license or "unknown").strip()[:60]
        try:
            self.fps = min(30.0, max(1.0, float(self.fps)))
        except (TypeError, ValueError):
            self.fps = 12.0
        try:
            self.ultra_scale = min(3.0, max(1.0, float(self.ultra_scale)))
        except (TypeError, ValueError):
            self.ultra_scale = 1.35
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "species": self.species,
            "body_color": self.body_color,
            "inner_color": self.inner_color,
            "eye_color": self.eye_color,
            "accent_color": self.accent_color,
            "accessory": self.accessory,
            "pattern": self.pattern,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "fps": self.fps,
            "ultra_scale": self.ultra_scale,
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterSpec":
        if not isinstance(data, dict):
            return cls()
        spec = cls(
            name=str(data.get("name") or "小可爱"),
            species=str(data.get("species") or "cat"),
            body_color=str(data.get("body_color") or "#FFF6E8"),
            inner_color=str(data.get("inner_color") or "#F7B6C2"),
            eye_color=str(data.get("eye_color") or "#3E3138"),
            accent_color=str(data.get("accent_color") or "#F58BA7"),
            accessory=str(data.get("accessory") or "none"),
            pattern=str(data.get("pattern") or "none"),
            description=str(data.get("description") or ""),
            author=str(data.get("author") or "unknown"),
            license=str(data.get("license") or "unknown"),
            fps=data.get("fps") or 12,
            ultra_scale=data.get("ultra_scale") or 1.35,
            extras=data.get("extras") if isinstance(data.get("extras"), dict) else {},
        )
        return spec.normalized()


# ---------------------------------------------------------------------------
# Prompt parsing
# ---------------------------------------------------------------------------

_NAME_PATTERNS = [
    re.compile(
        r"(?:名字|名叫|叫|name\s+is|named|called|call\s+it)\s*[「『\"“']?"
        r"([\u4e00-\u9fa5A-Za-z0-9_·-]{1,16})",
        re.IGNORECASE,
    )
]


def _parse_eye_color(text: str) -> tuple[str | None, str]:
    patterns = [
        rf"(?:眼睛|眼珠|眼)\s*(?:是|为|颜色是|颜色|:|：)?\s*({_COLOR_ALT})",
        rf"({_COLOR_ALT})\s*(?:色)?\s*(?:的)?\s*(?:眼睛|眼珠)",
        rf"({_COLOR_ALT})\s+eyes?",
        rf"eyes?\s+(?:are|is|:)?\s*({_COLOR_ALT})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            color = _color(match.group(1), "#3E3138")
            return color, _cut(text, match)
    return None, text


def _parse_accent_color(text: str, accessory_word: str | None) -> tuple[str | None, str]:
    if not accessory_word:
        return None, text
    word = re.escape(accessory_word)
    patterns = [
        rf"({_COLOR_ALT})\s*(?:色)?\s*(?:的)?\s*{word}",
        rf"{word}\s*(?:是|为|颜色是)?\s*({_COLOR_ALT})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            color = _color(match.group(1), "#F58BA7")
            return color, _cut(text, match)
    return None, text


def parse_prompt(prompt: str, name: str | None = None) -> CharacterSpec:
    """Turn a short description into a :class:`CharacterSpec`.

    Missing information gets friendly defaults (a cream cat with a pink bow).
    """
    original = (prompt or "").strip()
    text = original

    parsed_name = (name or "").strip()
    if not parsed_name:
        for pattern in _NAME_PATTERNS:
            match = pattern.search(text)
            if match:
                candidate = match.group(1).strip()
                if candidate and candidate not in {"猫", "狗", "兔", "狐", "熊", "鸟"}:
                    parsed_name = candidate
                text = _cut(text, match)
                break

    species_hit = _first_word(text, SPECIES_WORDS)
    species = species_hit[0] if species_hit else "cat"

    accessory_hit = _first_word(text, ACCESSORY_WORDS)
    accessory = accessory_hit[0] if accessory_hit else "none"

    # A colour directly attached to the accessory ("红围巾") is the accent,
    # not the body colour.
    accent = None
    if accessory_hit:
        accessory_word = accessory_hit[1].group(0)
        accent, text = _parse_accent_color(text, accessory_word)

    eye, text = _parse_eye_color(text)
    colors = list(_COLOR_RE.finditer(text))
    body = _color(colors[0].group(1), "#FFF6E8") if colors else "#FFF6E8"
    if accent is None and len(colors) > 1:
        accent = _color(colors[1].group(1), "#F58BA7")
    if accent is None:
        accent = "#F58BA7"

    pattern_hit = _first_word(text, PATTERN_WORDS)
    pattern = pattern_hit[0] if pattern_hit else "none"

    if not parsed_name:
        label = _color_label(colors[0].group(1)) if colors else ""
        species_label = SPECIES_LABELS.get(species, "猫")
        parsed_name = (label + species_label) if label else ("小" + species_label)

    return CharacterSpec(
        name=parsed_name,
        species=species,
        body_color=body,
        inner_color="#F7B6C2",
        eye_color=eye or "#3E3138",
        accent_color=accent,
        accessory=accessory,
        pattern=pattern,
        description=original,
    ).normalized()
