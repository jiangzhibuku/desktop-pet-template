"""Reusable Kivy widgets: the speech bubble and the radial menu button."""

from __future__ import annotations

import math
from collections.abc import Iterable

from kivy.graphics import Color, Ellipse, Line, RoundedRectangle, Triangle
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from .textutil import wrap_text


class SpeechBubble(FloatLayout):
    """A rounded speech bubble with a small tail pointing at the pet."""

    def __init__(
        self,
        text: str,
        *,
        width: float = 244,
        font_name: str = "Roboto",
        max_chars: int = 12,
        tail_side: str = "left",
        **kwargs,
    ) -> None:
        super().__init__(size_hint=(None, None), **kwargs)
        self.tail_side = tail_side
        lines = wrap_text(text, max_chars)
        line_height = 23
        self.size = (width, max(52, len(lines) * line_height + 24))

        with self.canvas.before:
            Color(0.3, 0.2, 0.25, 0.12)
            self._shadow = RoundedRectangle(radius=[18])
            Color(0.98, 0.72, 0.82, 1)
            self._border = RoundedRectangle(radius=[18])
            Color(1, 1, 1, 0.97)
            self._fill = RoundedRectangle(radius=[15])
            Color(1, 1, 1, 0.97)
            self._tail = Triangle()
            Color(0.98, 0.72, 0.82, 1)
            self._tail_edge = Line(width=1.4)
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)

        body = "\n".join(lines)
        self.label = Label(
            text=body,
            font_name=font_name,
            font_size=15,
            color=(0.28, 0.24, 0.28, 1),
            halign="center",
            valign="middle",
            size_hint=(None, None),
            text_size=(width - 22, self.height - 14),
        )
        self.add_widget(self.label)
        self._sync_canvas()

    def _sync_canvas(self, *_args) -> None:
        x, y = self.pos
        w, h = self.size
        self._shadow.pos = (x + 1, y - 3)
        self._shadow.size = (w, h)
        self._border.pos = (x, y)
        self._border.size = (w, h)
        self._fill.pos = (x + 2, y + 2)
        self._fill.size = (w - 4, h - 4)
        mid = y + h / 2
        if self.tail_side == "left":
            top = (x + 6, mid + 9)
            tip = (x - 10, mid)
            bottom = (x + 6, mid - 9)
        else:
            top = (x + w - 6, mid + 9)
            tip = (x + w + 10, mid)
            bottom = (x + w - 6, mid - 9)
        self._tail.points = [*top, *bottom, *tip]
        self._tail_edge.points = [*top, *tip, *bottom]
        self.label.pos = (x + 11, y + 7)
        self.label.size = (w - 22, h - 14)
        self.label.text_size = self.label.size


class MenuButton(Button):
    """Circular translucent button used by the right-click radial menu."""

    def __init__(
        self,
        text: str,
        action: str,
        angle: float,
        *,
        font_name: str = "Roboto",
        **kwargs,
    ) -> None:
        super().__init__(text=text, **kwargs)
        self.action = action
        self.angle = angle

        self.size_hint = (None, None)
        self.size = (76, 76)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = (0.33, 0.26, 0.31, 1)
        self.font_name = font_name
        self.font_size = 15
        self.bold = True

        with self.canvas.before:
            Color(0.98, 0.68, 0.79, 0.92)
            self._outer = Ellipse()
            Color(1, 0.94, 0.96, 0.98)
            self._inner = Ellipse()
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self._sync_canvas()

    def _sync_canvas(self, *_args) -> None:
        x, y = self.pos
        w, h = self.size
        self._outer.pos = (x, y)
        self._outer.size = (w, h)
        self._inner.pos = (x + 3, y + 3)
        self._inner.size = (w - 6, h - 6)

    def menu_position(self, center: tuple[float, float], radius: float) -> tuple[float, float]:
        radians = math.radians(self.angle)
        return (
            center[0] + math.cos(radians) * radius - self.width / 2,
            center[1] + math.sin(radians) * radius - self.height / 2,
        )


def layout_menu(buttons: Iterable[MenuButton], center: tuple[float, float], radius: float) -> None:
    for button in buttons:
        button.pos = button.menu_position(center, radius)
