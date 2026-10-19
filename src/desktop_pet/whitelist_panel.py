"""A pink/white whitelist panel that matches the rest of the UI.

The old panel was a plain Tk window.  This version uses the same popup
background, rounded cards and soft colors as the character wizard.
"""

from __future__ import annotations

from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from .agent import BUILTIN_APPS, Agent
from .paths import AppPaths

PINK = (0.96, 0.58, 0.72, 1)
SOFT_BLUE = (0.86, 0.90, 0.97, 1)
INK = (0.30, 0.24, 0.28, 1)
MUTED = (0.52, 0.44, 0.49, 1)


def _flat_button(
    text: str,
    color=PINK,
    *,
    height: int = 38,
    width: int | None = None,
) -> Button:
    button = Button(
        text=text,
        size_hint=(None if width else 1, None),
        width=width or 0,
        height=height,
        background_normal="",
        background_down="",
        background_color=color,
        color=(1, 1, 1, 1),
        bold=True,
    )
    return button


def _card(widget, color=(1, 1, 1, 0.94), radius: int = 10) -> None:
    with widget.canvas.before:
        Color(*color)
        rect = RoundedRectangle(radius=[radius])
    widget.bind(
        pos=lambda _w, value: setattr(rect, "pos", value),
        size=lambda _w, value: setattr(rect, "size", value),
    )


class WhitelistPopup(Popup):
    def __init__(
        self,
        *,
        agent: Agent,
        paths: AppPaths,
        font_name: str = "Roboto",
        **kwargs,
    ) -> None:
        super().__init__(
            title="白名单管理",
            title_size=18,
            title_color=INK,
            separator_color=(0.97, 0.68, 0.79, 1),
            separator_height=1,
            background=str(paths.assets / "ui" / "popup_bg.png"),
            border=(14, 14, 14, 14),
            size_hint=(None, None),
            size=(620, 640),
            auto_dismiss=False,
            **kwargs,
        )
        self.agent = agent
        self._font = font_name

        root = BoxLayout(orientation="vertical", spacing=6, padding=12)
        with root.canvas.before:
            Color(1, 0.975, 0.985, 1)
            self._bg = RoundedRectangle(radius=[14])
        root.bind(
            pos=lambda _w, value: setattr(self._bg, "pos", value),
            size=lambda _w, value: setattr(self._bg, "size", value),
        )
        self.root_box = root

        root.add_widget(
            Label(
                text="允许桌宠打开的程序",
                font_name=font_name,
                font_size=19,
                bold=True,
                color=(0.72, 0.34, 0.47, 1),
                size_hint_y=None,
                height=30,
            )
        )
        root.add_widget(
            Label(
                text="只有名单里的软件才能被 AI 打开；内置应用不可删除。",
                font_name=font_name,
                font_size=12,
                color=MUTED,
                size_hint_y=None,
                height=20,
            )
        )

        self.stats = Label(
            text="",
            font_name=font_name,
            font_size=12,
            color=MUTED,
            size_hint_y=None,
            height=20,
        )
        root.add_widget(self.stats)

        scroll = ScrollView(size_hint_y=None, height=306, do_scroll_x=False, bar_width=6)
        self.list_box = BoxLayout(orientation="vertical", spacing=6, size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)

        form = BoxLayout(spacing=8, size_hint_y=None, height=44)
        self.name_input = TextInput(
            hint_text="应用名",
            multiline=False,
            font_name=font_name,
            size_hint=(None, 1),
            width=132,
            background_color=(1, 1, 1, 0.97),
            foreground_color=INK,
            cursor_color=PINK,
        )
        self.cmd_input = TextInput(
            hint_text="启动命令或 exe 路径",
            multiline=False,
            font_name=font_name,
            background_color=(1, 1, 1, 0.97),
            foreground_color=INK,
            cursor_color=PINK,
        )
        add = _flat_button("添加", PINK, height=40, width=68)
        add.bind(on_release=lambda _b: self._add())
        form.add_widget(self.name_input)
        form.add_widget(self.cmd_input)
        form.add_widget(add)
        root.add_widget(form)

        self.status = Label(
            text="自定义应用会保存到 whitelist.json。",
            font_name=font_name,
            font_size=12,
            color=MUTED,
            size_hint_y=None,
            height=30,
            text_size=(560, None),
            halign="left",
            valign="middle",
        )
        root.add_widget(self.status)

        footer = BoxLayout(spacing=8, size_hint_y=None, height=42)
        footer.add_widget(
            Label(
                text="建议只加入你信任的程序",
                font_name=font_name,
                font_size=11,
                color=(0.60, 0.50, 0.55, 1),
            )
        )
        close = _flat_button("关闭", (0.72, 0.72, 0.76, 1), height=38, width=76)
        close.bind(on_release=lambda _b: self.dismiss())
        footer.add_widget(close)
        root.add_widget(footer)

        self.content = root
        self._rebuild()

    # ------------------------------------------------------------------ list
    def _row(self, name: str, command: str, builtin: bool) -> BoxLayout:
        row = BoxLayout(
            orientation="horizontal",
            spacing=8,
            padding=(12, 5),
            size_hint_y=None,
            height=50,
        )
        _card(row)
        row.add_widget(
            Label(
                text=name,
                font_name=self._font,
                font_size=14,
                bold=True,
                color=INK,
                size_hint_x=None,
                width=132,
                halign="left",
                valign="middle",
                text_size=(132, None),
            )
        )
        command_label = Label(
            text=command,
            font_name=self._font,
            font_size=11,
            color=MUTED,
            halign="left",
            valign="middle",
            size_hint_x=1,
            shorten=True,
            max_lines=1,
        )
        command_label.bind(
            size=lambda widget, size: setattr(widget, "text_size", (size[0], None))
        )
        row.add_widget(command_label)
        if builtin:
            row.add_widget(
                Label(
                    text="内置",
                    font_name=self._font,
                    font_size=11,
                    color=(0.62, 0.52, 0.57, 1),
                    size_hint_x=None,
                    width=40,
                )
            )
        else:
            remove = _flat_button("移除", (0.94, 0.52, 0.58, 1), height=30, width=56)
            remove.size_hint_y = None
            remove.bind(on_release=lambda _b, app_name=name: self._remove(app_name))
            row.add_widget(remove)
        return row

    def _rebuild(self) -> None:
        self.list_box.clear_widgets()
        all_apps = {**BUILTIN_APPS, **self.agent.user_apps}
        for name, command in sorted(all_apps.items()):
            self.list_box.add_widget(self._row(name, str(command), name in BUILTIN_APPS))
        builtin_count = len(BUILTIN_APPS)
        user_count = len(self.agent.user_apps)
        self.stats.text = f"内置 {builtin_count} 个 · 自定义 {user_count} 个"

    # --------------------------------------------------------------- actions
    def _add(self) -> None:
        name = self.name_input.text.strip()
        command = self.cmd_input.text.strip()
        if not name or not command:
            self.status.text = "应用名和启动命令都要填。"
            return
        message = self.agent.add_app(name, command)
        self.status.text = message
        if message.startswith("已添加"):
            self.name_input.text = ""
            self.cmd_input.text = ""
        self._rebuild()

    def _remove(self, name: str) -> None:
        self.status.text = self.agent.remove_app(name)
        self._rebuild()
