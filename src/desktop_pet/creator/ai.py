"""Optional AI helpers: prompt -> spec and prompt -> image.

Both are opt-in.  The offline renderer remains the default so the template
works without an image-model subscription.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import requests
from PIL import Image

from ..config import Config
from .spec import SPECIES_LABELS, CharacterSpec, parse_prompt

SPEC_SCHEMA_PROMPT = """你是一个桌宠角色设计助手。把用户的中文或英文描述转成 JSON，只输出 JSON，不要解释。
字段：
- name: 角色名字（字符串，1-16 字）
- species: cat / dog / rabbit / fox / bear / bird / slime
- body_color: 主体颜色，十六进制，如 #FFF6E8
- inner_color: 耳朵内侧/腮红颜色，十六进制
- eye_color: 眼睛颜色，十六进制
- accent_color: 配饰颜色，十六进制
- accessory: none / bow / scarf / glasses / headphones / hat / flower
- pattern: none / patches / stripes / star / heart
- description: 原始描述
如果描述没有提到，选择可爱、柔和的默认值。"""


def _strip_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型没有返回 JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("模型返回的不是 JSON 对象")
    return data


def spec_from_prompt(prompt: str, config: Config, *, timeout: float | None = None) -> CharacterSpec | None:
    """Ask the chat model for a structured character spec.

    Returns ``None`` when no key is configured or the model/API does not support
    the request; callers should fall back to :func:`parse_prompt`.
    """
    if not config.api.configured:
        return None
    payload = {
        "model": config.api.model,
        "messages": [
            {"role": "system", "content": SPEC_SCHEMA_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "response_format": {"type": "json_object"},
    }
    url = config.api.base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + config.api.api_key}
    timeout = timeout or config.api.timeout
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if response.status_code == 400:
            payload.pop("response_format", None)
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = _strip_json(content)
        spec = CharacterSpec.from_dict(data)
        spec.description = prompt
        return spec
    except Exception:
        return None


def image_prompt(spec: CharacterSpec) -> str:
    species = SPECIES_LABELS.get(spec.species, "猫")
    accessory = {
        "none": "",
        "bow": "戴蝴蝶结",
        "scarf": "戴围巾",
        "glasses": "戴圆眼镜",
        "headphones": "戴耳机",
        "hat": "戴小帽子",
        "flower": "戴小花",
    }.get(spec.accessory, "")
    text = spec.description or f"一只{species}"
    return (
        f"可爱的Q版{species}角色，{text}，{accessory}。"
        "厚描边，奶油色和粉色点缀，贴纸风格，全身，正面站立，"
        "纯白背景，居中，无文字，高质量"
    )


def generate_image(prompt: str, config: Config, output_path: Path, *, timeout: float | None = None) -> Path | None:
    """Call an OpenAI-compatible ``/images/generations`` endpoint.

    Returns the saved PNG path, or ``None`` on any failure.  The caller decides
    whether to fall back to the procedural renderer.
    """
    if not config.api.configured:
        return None
    url = config.api.base_url.rstrip("/") + "/images/generations"
    headers = {"Authorization": "Bearer " + config.api.api_key}
    payload = {
        "model": config.api.image_model,
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1,
    }
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout or max(60.0, config.api.timeout),
        )
        response.raise_for_status()
        item = response.json()["data"][0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        else:
            image_url = item.get("url")
            if not image_url:
                return None
            image_response = requests.get(image_url, timeout=60)
            image_response.raise_for_status()
            raw = image_response.content
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG")
        return output_path
    except Exception:
        return None


def spec_for_prompt(prompt: str, config: Config, *, use_ai: bool) -> tuple[CharacterSpec, str]:
    """Return a spec and a short note describing which path was used."""
    fallback = parse_prompt(prompt)
    if not use_ai:
        return fallback, "offline"
    ai_spec = spec_from_prompt(prompt, config)
    if ai_spec is None:
        return fallback, "offline (AI 解析不可用，已回退)"
    return ai_spec, "ai"
