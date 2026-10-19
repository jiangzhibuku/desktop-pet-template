"""The animated pet widget (frame playback, walking and jumping)."""

from __future__ import annotations

from collections.abc import Callable

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Rectangle
from kivy.uix.widget import Widget

from .characters import Character


class PetWidget(Widget):
    """A sprite whose image is kept in sync with the widget position/size."""

    def __init__(
        self,
        character: Character,
        *,
        height: float = 300.0,
        walk_speed: float = 48.0,
        jump_height: float = 55.0,
        on_auto_idle: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.character = character
        self.base_height = height
        self.walk_speed = walk_speed
        self.jump_height = jump_height
        self.on_auto_idle = on_auto_idle

        self.size_hint = (None, None)
        self.base_size = character.size_for(height, "idle")
        self.size = self.base_size
        self.pos = (40, 60)

        self.mode = "idle"
        self.walk_target: float | None = None
        self._frames = character.frames("idle")
        self._index = 0
        self._clock = None
        self._auto_idle = None
        self._jump_start_y: float | None = None

        with self.canvas:
            self.image = Rectangle(
                source=str(self._frames[0]) if self._frames else "",
                size=self.size,
                pos=self.pos,
            )
        self.bind(pos=self._sync_canvas, size=self._sync_canvas)
        self.play("idle")

    # ------------------------------------------------------------------ view
    def _sync_canvas(self, *_args) -> None:
        self.image.pos = self.pos
        self.image.size = self.size

    def _show_current(self) -> None:
        if not self._frames:
            return
        self.image.source = str(self._frames[self._index])

    # ------------------------------------------------------------- playback
    def play(self, name: str, idle_index: int = 0) -> None:
        if name == "idle" and idle_index in (1, 2):
            name = f"idle{idle_index + 1}"
        frames = self.character.frames(name)
        if not frames:
            name, frames = "idle", self.character.frames("idle")
        if not frames:
            return

        self.stop()
        self.mode = name
        self._frames = frames
        self._index = 0
        self._auto_idle = None

        if name == "ultra":
            self.size = self.character.size_for(self.base_height, "ultra")
        else:
            self.size = self.base_size
        self._show_current()
        self._clock = Clock.schedule_interval(self._tick, 1.0 / self.character.fps)

        if name == "ultra":
            self._auto_idle = Clock.schedule_once(lambda _dt: self.play("idle"), 8.5)
        elif name == "jump":
            self._start_jump()

    def stop(self) -> None:
        if self._clock is not None:
            self._clock.cancel()
            self._clock = None
        if self._auto_idle is not None:
            self._auto_idle.cancel()
            self._auto_idle = None
        Animation.cancel_all(self)
        if self._jump_start_y is not None:
            self.y = self._jump_start_y
            self._jump_start_y = None

    def cancel_motion(self) -> None:
        """Stop a jump without leaving the pet floating in mid-air."""
        Animation.cancel_all(self)
        if self._jump_start_y is not None:
            self.y = self._jump_start_y
            self._jump_start_y = None

    def _tick(self, dt: float) -> None:
        self._index = (self._index + 1) % len(self._frames)
        self._show_current()
        if self.mode == "walk":
            self.x += self.walk_speed * dt
            if self.x > Window.width:
                self.x = -self.width
            if self.walk_target is not None:
                if abs(self.x - self.walk_target) <= self.walk_speed * dt:
                    self.x = self.walk_target
                    self.walk_target = None

    def _start_jump(self) -> None:
        start = self.y
        peak = min(start + self.jump_height, Window.height - self.height)
        if peak <= start:
            return
        self._jump_start_y = start
        animation = Animation(y=peak, duration=0.45, transition="out_quad") + Animation(
            y=start, duration=0.45, transition="in_quad"
        )
        animation.bind(on_complete=lambda *_args: setattr(self, "_jump_start_y", None))
        animation.start(self)

    # --------------------------------------------------------------- helpers
    def clamp_to_screen(self) -> None:
        max_x = max(0.0, Window.width - self.width)
        max_y = max(0.0, Window.height - self.height)
        self.pos = (
            min(max(0.0, self.x), max_x),
            min(max(0.0, self.y), max_y),
        )

    def idle(self, idle_index: int = 0) -> None:
        self.play("idle", idle_index)
