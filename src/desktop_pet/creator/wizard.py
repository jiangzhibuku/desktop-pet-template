"""Kivy "create a pet" wizard used by the radial menu.

The actual generation runs in a worker thread; only the Kivy widgets are
touched on the main thread.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from pathlib import Path

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from ..config import Config
from ..paths import AppPaths
from .native_dialog import pick_image
from .pipeline import create_from_image, create_from_prompt

PINK = (0.96, 0.58, 0.72, 1)
SOFT = (0.98, 0.90, 0.93, 1)
INK = (0.30, 0.24, 0.28, 1)


def _button(text: str, color=PINK, *, height: int = 42) -> Button:
    button = Button(
        text=text,
        size_hint_y=None,
        height=height,
        background_normal="",
        background_down="",
        background_color=color,
        color=(1, 1, 1, 1),
        bold=True,
    )
    return button


class CreatePetWizard(Popup):
    def __init__(
        self,
        *,
        config: Config,
        paths: AppPaths,
        on_created: Callable[[str], None],
        font_name: str = "Roboto",
        **kwargs,
    ) -> None:
        super().__init__(
            title="创建你的桌宠",
            title_size=18,
            title_color=INK,
            separator_color=(0.97, 0.68, 0.79, 1),
            separator_height=1,
            background=str(paths.assets / "ui" / "popup_bg.png"),
            border=(14, 14, 14, 14),
            size_hint=(None, None),
            size=(560, 650),
            auto_dismiss=False,
            **kwargs,
        )
        self.settings = config
        self.paths = paths
        self._on_created = on_created
        self._font_name = font_name
        self.mode = "prompt"
        self.image_path: str | None = None
        self.result = None
        self._done = False
        self._alive = True
        self._queue: queue.Queue = queue.Queue()
        self._poll_event = None

        root = BoxLayout(orientation="vertical", spacing=6, padding=12)
        with root.canvas.before:
            Color(1, 0.975, 0.985, 1)
            self._background = RoundedRectangle(radius=[14])
        root.bind(
            pos=lambda widget, pos: setattr(self._background, "pos", pos),
            size=lambda widget, size: setattr(self._background, "size", size),
        )
        self.root_box = root
        root.add_widget(
            Label(
                text="写一句描述，或者选一张图；生成后立即切换",
                font_name=font_name,
                font_size=13,
                color=(0.52, 0.43, 0.48, 1),
                size_hint_y=None,
                height=22,
            )
        )

        self.name_input = TextInput(
            hint_text="名字（可留空，会自动起名）",
            multiline=False,
            font_name=font_name,
            size_hint_y=None,
            height=40,
            background_color=(1, 1, 1, 0.96),
            foreground_color=INK,
            cursor_color=PINK,
        )
        root.add_widget(self.name_input)

        modes = BoxLayout(spacing=8, size_hint_y=None, height=40)
        self.prompt_mode = _button("用文字描述", SOFT, height=38)
        self.image_mode = _button("用一张图片", (0.86, 0.90, 0.97, 1), height=38)
        self.prompt_mode.color = INK
        self.image_mode.color = INK
        self.prompt_mode.bind(on_release=lambda _b: self._set_mode("prompt"))
        self.image_mode.bind(on_release=lambda _b: self._set_mode("image"))
        modes.add_widget(self.prompt_mode)
        modes.add_widget(self.image_mode)
        root.add_widget(modes)

        self.prompt_box = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None, height=124)
        self.prompt_box.add_widget(
            Label(
                text="描述它：颜色、动物、配饰、花纹",
                font_name=font_name,
                font_size=13,
                color=(0.45, 0.38, 0.42, 1),
                size_hint_y=None,
                height=20,
            )
        )
        self.prompt_input = TextInput(
            hint_text="例如：白色小猫，戴红围巾，蓝眼睛，星星花纹",
            multiline=True,
            font_name=font_name,
            size_hint_y=None,
            height=96,
            background_color=(1, 1, 1, 0.96),
            foreground_color=INK,
            cursor_color=PINK,
        )
        self.prompt_box.add_widget(self.prompt_input)
        root.add_widget(self.prompt_box)

        self.image_box = BoxLayout(orientation="vertical", spacing=4, size_hint_y=None, height=158)
        self.image_box.add_widget(
            Label(
                text="上传一张图片（PNG/JPG），自动去背景并生成动画",
                font_name=font_name,
                font_size=13,
                color=(0.45, 0.38, 0.42, 1),
                size_hint_y=None,
                height=20,
            )
        )
        pick_row = BoxLayout(spacing=8, size_hint_y=None, height=44)
        self.path_label = Label(
            text="还没有上传图片",
            font_name=font_name,
            font_size=12,
            color=(0.45, 0.38, 0.42, 1),
            text_size=(360, None),
            halign="left",
            valign="middle",
        )
        choose = _button("上传图片", (0.86, 0.90, 0.97, 1), height=40)
        choose.color = INK
        choose.bind(on_release=lambda _b: self._choose_image())
        pick_row.add_widget(self.path_label)
        pick_row.add_widget(choose)
        self.image_box.add_widget(pick_row)

        cutout_row = BoxLayout(spacing=6, size_hint_y=None, height=30)
        cutout_row.add_widget(
            Label(
                text="抠图方式",
                font_name=font_name,
                font_size=12,
                color=(0.45, 0.38, 0.42, 1),
                size_hint_x=None,
                width=62,
            )
        )
        default_cutout = {
            "auto": "自动抠图",
            "rembg": "本地 rembg",
            "none": "保留原图",
        }.get(self.settings.creator.cutout, "自动抠图")
        self.cutout_spinner = Spinner(
            text=default_cutout,
            values=("自动抠图", "本地 rembg", "保留原图"),
            font_name=font_name,
            font_size=12,
            size_hint=(None, 1),
            width=136,
            background_normal="",
            background_down="",
            background_color=(0.99, 0.93, 0.95, 1),
            color=INK,
        )
        cutout_row.add_widget(self.cutout_spinner)
        cutout_row.add_widget(
            Label(
                text="v",
                font_name=font_name,
                font_size=12,
                color=INK,
                size_hint_x=None,
                width=12,
            )
        )
        cutout_row.add_widget(
            Label(
                text="rembg 需安装；保留原图会带矩形底",
                font_name=font_name,
                font_size=10,
                color=(0.58, 0.50, 0.54, 1),
            )
        )
        self.image_box.add_widget(cutout_row)
        root.add_widget(self.image_box)

        self.ai_row = BoxLayout(spacing=6, size_hint_y=None, height=34)
        self.ai_check = CheckBox(active=False, size_hint_x=None, width=34)
        self.ai_row.add_widget(self.ai_check)
        self.ai_row.add_widget(
            Label(
                text="AI 增强（用模型解析描述并出图；失败会自动回退离线）",
                font_name=font_name,
                font_size=12,
                color=(0.45, 0.38, 0.42, 1),
            )
        )
        root.add_widget(self.ai_row)

        self.preview = Image(
            source=str(paths.assets / "icon.png"),
            size_hint_y=None,
            height=130,
            allow_stretch=True,
            keep_ratio=True,
        )
        root.add_widget(self.preview)

        self.status = Label(
            text="填好后点「生成并切换」",
            font_name=font_name,
            font_size=13,
            color=(0.45, 0.38, 0.42, 1),
            text_size=(520, None),
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=36,
        )
        root.add_widget(self.status)

        actions = BoxLayout(spacing=10, size_hint_y=None, height=46)
        self.generate_btn = _button("生成并切换", PINK)
        self.cancel_btn = _button("取消", (0.72, 0.72, 0.76, 1))
        self.generate_btn.bind(on_release=lambda _b: self._on_generate())
        self.cancel_btn.bind(on_release=lambda _b: self.dismiss())
        actions.add_widget(self.generate_btn)
        actions.add_widget(self.cancel_btn)
        root.add_widget(actions)

        self.content = root
        self._set_mode("prompt")

    # ------------------------------------------------------------------ mode
    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        prompt = mode == "prompt"
        self.prompt_box.height = 124 if prompt else 0
        self.prompt_box.opacity = 1 if prompt else 0
        self.prompt_box.disabled = not prompt
        self.image_box.height = 0 if prompt else 158
        self.image_box.opacity = 0 if prompt else 1
        self.image_box.disabled = prompt
        self.ai_check.disabled = not prompt
        self.ai_row.height = 34 if prompt else 0
        self.ai_row.opacity = 1 if prompt else 0
        self.ai_row.disabled = not prompt
        self.prompt_mode.background_color = SOFT if prompt else (0.92, 0.92, 0.94, 1)
        self.image_mode.background_color = (0.86, 0.90, 0.97, 1) if not prompt else (0.92, 0.92, 0.94, 1)

    def _choose_image(self) -> None:
        self.status.text = "正在打开文件选择框…"
        pick_image(self._image_selected)

    def _image_selected(self, path: str) -> None:
        if not self._alive:
            return
        if not path:
            self.status.text = "已取消选择"
            return
        suffix = Path(path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            self.status.text = "请选择 PNG / JPG / JPEG / WebP 图片"
            return

        self.image_path = path
        self.path_label.text = Path(path).name
        if not self.name_input.text.strip():
            self.name_input.text = (Path(path).stem.lstrip("._- ") or "我的桌宠")[:16]
        try:
            self.preview.source = path
        except Exception:
            pass
        self._done = False
        self.result = None
        self.generate_btn.text = "生成并切换"
        self._set_mode("image")
        self.status.text = "已选择：{}，点「生成并切换」".format(Path(path).name)

    # -------------------------------------------------------------- generate
    def _on_generate(self) -> None:
        if self._done:
            self.dismiss()
            return
        if self.mode == "prompt":
            prompt = self.prompt_input.text.strip()
            if not prompt:
                self.status.text = "先写一句描述吧"
                return
        else:
            if not self.image_path or not Path(self.image_path).is_file():
                self.status.text = "先选一张图片吧"
                return

        self.generate_btn.disabled = True
        self.cancel_btn.disabled = True
        self.status.text = "生成中…（AI 出图可能需要十几秒）"
        name = self.name_input.text.strip() or None
        if self.mode == "image":
            thread = threading.Thread(target=self._work_image, args=(self.image_path, name), daemon=True)
        else:
            thread = threading.Thread(
                target=self._work_prompt,
                args=(self.prompt_input.text.strip(), name, bool(self.ai_check.active)),
                daemon=True,
            )
        thread.start()
        self._poll_event = Clock.schedule_interval(self._poll, 0.15)

    def _work_image(self, image_path: str, name: str | None) -> None:
        try:
            cutout = {
                "自动抠图": "auto",
                "本地 rembg": "rembg",
                "保留原图": "none",
            }.get(self.cutout_spinner.text, "auto")
            notices: list[str] = []
            result = create_from_image(
                image_path,
                name or Path(image_path).stem,
                self.paths,
                author="local user",
                license="unverified",
                cutout=cutout,
                cutout_model=self.settings.creator.cutout_model,
                notices=notices,
            )
            self._queue.put(("ok", result, ["角色图：用户提供的图片", *notices]))
        except Exception as exc:
            self._queue.put(("error", str(exc), []))

    def _work_prompt(self, prompt: str, name: str | None, ai: bool) -> None:
        try:
            result, notices = create_from_prompt(
                prompt,
                name,
                self.paths,
                config=self.settings,
                use_ai_spec=ai,
                use_ai_image=ai,
                author="local user",
                license="unverified",
            )
            self._queue.put(("ok", result, notices))
        except Exception as exc:
            self._queue.put(("error", str(exc), []))

    def _poll(self, _dt: float) -> bool:
        try:
            kind, payload, notices = self._queue.get_nowait()
        except queue.Empty:
            return True

        if self._poll_event is not None:
            self._poll_event.cancel()
            self._poll_event = None

        if kind == "error":
            self.status.text = "生成失败：" + str(payload)[:120]
            self.generate_btn.disabled = False
            self.cancel_btn.disabled = False
            return False

        result = payload
        self.result = result
        self._done = True
        self.preview.source = str(result.preview)
        self.status.text = "已生成「{}」\n{}".format(
            result.key, " / ".join(notices) if notices else ""
        )
        self.generate_btn.text = "完成"
        self.generate_btn.disabled = False
        self.cancel_btn.disabled = False
        try:
            self._on_created(result.key)
        except Exception:
            pass
        return False

    def dismiss(self, *args, **kwargs):
        self._alive = False
        if self._poll_event is not None:
            self._poll_event.cancel()
            self._poll_event = None
        return super().dismiss(*args, **kwargs)
