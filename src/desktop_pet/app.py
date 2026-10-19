"""The Kivy desktop-pet application."""

from __future__ import annotations

import queue
import random
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from .agent import Agent
from .characters import load_character
from .config import load_config, resolve_font, save_config
from .input_panel import InputPanel
from .paths import build_paths
from .pet import PetWidget
from .widgets import MenuButton, SpeechBubble, layout_menu
from .win32_window import setup_desktop_window

MENU_ITEMS = [
    ("跳跃", "jump", 90),
    ("散步", "walk", 60),
    ("大招", "ultra", 30),
    ("聊天", "chat", 0),
    ("待机2", "idle2", -30),
    ("创建", "create", -60),
    ("扩展", "manage", -90),
    ("退出", "quit", -120),
]


class DesktopPetApp(App):
    title = "Desktop Pet"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.paths = build_paths()
        self.settings = load_config(self.paths)
        self.character = load_character(self.settings.character, self.paths)
        self.agent = Agent(self.settings, self.paths)
        self.agent.reminder_cb = lambda text: self.result_queue.put((text, []))

        self.input_queue: queue.Queue[str] = queue.Queue()
        self.result_queue: queue.Queue[tuple[str, list[dict]]] = queue.Queue()

        self.pet: PetWidget | None = None
        self.menu_buttons: list[MenuButton] = []
        self.menu_visible = False
        self.bubble: SpeechBubble | None = None
        self._bubble_event = None
        self._menu_event = None
        self._last_click = 0.0
        self._dragging = False
        self._drag_offset = (0.0, 0.0)
        self._input_open = False
        self._proactive_busy = False
        self._font_name = "Roboto"
        self._root: FloatLayout | None = None
        self._wizard = None
        self._whitelist = None

        self.input_panel = InputPanel(
            on_submit=self.submit_text,
            get_apps=self.get_apps,
            add_app=self.agent.add_app,
            remove_app=self.agent.remove_app,
            on_hide=self._input_hidden,
        )
        threading.Thread(target=self._worker, name="pet-agent", daemon=True).start()

    # --------------------------------------------------------------- startup
    def build(self) -> FloatLayout:
        self._register_font()
        if self.settings.ui.always_on_top:
            Window.always_on_top = True
        Window.borderless = True
        Window.clearcolor = (0, 0, 0, 0)
        self._set_window_icon()

        self._root = FloatLayout(size_hint=(1, 1))
        self.pet = PetWidget(
            self.character,
            height=self.settings.ui.pet_height,
            walk_speed=self.settings.ui.walk_speed,
            jump_height=self.settings.ui.jump_height,
        )
        self.pet.pos = (40, 60)
        self._root.add_widget(self.pet)

        for text, action, angle in MENU_ITEMS:
            button = MenuButton(text, action, angle, font_name=self._font_name)
            button.pos = (-500, -500)
            button.bind(on_release=self._on_menu_button)
            self._root.add_widget(button)
            self.menu_buttons.append(button)

        Window.bind(on_touch_down=self._on_touch_down)
        Window.bind(on_touch_move=self._on_touch_move)
        Window.bind(on_touch_up=self._on_touch_up)
        Window.bind(on_keyboard=self._on_keyboard)
        Window.bind(size=self._on_window_resize)
        return self._root

    def _register_font(self) -> None:
        font = resolve_font(self.settings, self.paths)
        if not font:
            return
        try:
            LabelBase.register(name="Roboto", fn_regular=str(font))
            LabelBase.register(name="PetFont", fn_regular=str(font))
            self._font_name = "PetFont"
        except Exception:
            self._font_name = "Roboto"

    def _set_window_icon(self) -> None:
        icon = self.paths.assets / "icon.png"
        if icon.is_file():
            try:
                Window.set_icon(str(icon))
            except Exception:
                pass

    def on_start(self) -> None:
        setup_desktop_window()
        self.pet.clamp_to_screen()
        Clock.schedule_interval(self._poll, 1.0 / 20.0)
        Clock.schedule_interval(self._move_step, 1.0 / 60.0)
        Clock.schedule_interval(self._auto_act, 30.0)
        if self.settings.agent.proactive_minutes > 0:
            Clock.schedule_interval(
                self._proactive, self.settings.agent.proactive_minutes * 60.0
            )
        Clock.schedule_once(lambda _dt: self.show_bubble(self._greeting()), 2.5)

    def _greeting(self) -> str:
        hour = time.localtime().tm_hour
        if hour < 6:
            return "夜深了，还不睡吗？"
        if hour < 9:
            return "早上好呀！"
        if hour < 12:
            return "上午好！"
        if hour < 14:
            return "中午好，吃饭了吗？"
        if hour < 18:
            return "下午好！"
        return "晚上好呀！"

    # ---------------------------------------------------------------- fonts
    @property
    def font_name(self) -> str:
        return self._font_name

    # ---------------------------------------------------------------- input
    def submit_text(self, text: str) -> None:
        self._input_open = False
        # Called from the Tk thread: touch Kivy widgets on the next frame.
        Clock.schedule_once(lambda _dt: self.show_bubble("思考中…", auto_hide=False), 0)
        self.input_queue.put(text)

    def _worker(self) -> None:
        while True:
            text = self.input_queue.get()
            try:
                reply = self.agent.chat(text)
            except Exception as exc:  # keep the pet alive on network errors
                reply = "出错了：" + str(exc)
            self.result_queue.put((reply, list(self.agent.actions)))

    def _poll(self, _dt: float) -> None:
        if self.pet is None:
            return
        self.input_panel.set_anchor(self.pet.x, self.pet.y, self.pet.width, self.pet.height)

        while True:
            try:
                tool, args = self.agent.confirm_queue.get_nowait()
            except queue.Empty:
                break
            self.show_confirm(tool, args)

        while True:
            try:
                reply, actions = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if reply:
                self.show_bubble(reply)
            for action in actions:
                animation = action.get("animation")
                if animation:
                    self.play_animation(animation)

    # ------------------------------------------------------------- animation
    def play_animation(self, name: str, *, from_menu: bool = False) -> None:
        if self.pet is None:
            return
        if name == "idle2":
            if self.pet:
                self.pet.play("idle", 1)
        elif name in {"idle", "walk", "jump", "ultra"}:
            self.pet.play(name)
        else:
            return
        self.pet.clamp_to_screen()
        if from_menu:
            self._hide_menu()
        if name == "jump":
            Clock.schedule_once(lambda _dt: self.pet.play("idle"), 2.0)
        elif name == "walk":
            Clock.schedule_once(lambda _dt: self.pet.play("idle"), 6.0)

    def _move_step(self, dt: float) -> None:
        if self.pet is None or self.pet.walk_target is None:
            return
        target = self.pet.walk_target
        step = self.settings.ui.walk_speed * dt
        delta = target - self.pet.x
        if abs(delta) <= step:
            self.pet.x = target
            self.pet.walk_target = None
        else:
            self.pet.x += step if delta > 0 else -step

    def _auto_act(self, _dt: float) -> None:
        if self.pet is None or self._dragging or self._input_open or self.menu_visible:
            return
        if self.pet.mode == "ultra" or self.bubble is not None:
            return
        dx = random.choice([-1, 1]) * random.randint(90, 220)
        target = min(max(0.0, self.pet.x + dx), max(0.0, Window.width - self.pet.width))
        self.pet.walk_target = target
        self.pet.play("jump")
        Clock.schedule_once(lambda _dt: self.pet.play("idle"), 2.0)

    def _proactive(self, _dt: float) -> None:
        if self._proactive_busy or self.agent.offline or self.bubble is not None:
            return
        self._proactive_busy = True

        def work() -> None:
            try:
                text = self.agent.proactive_talk()
                if text:
                    Clock.schedule_once(
                        lambda _dt: self.show_bubble(text), 0
                    )
            finally:
                self._proactive_busy = False

        threading.Thread(target=work, name="pet-proactive", daemon=True).start()

    # ----------------------------------------------------------------- menu
    def _on_menu_button(self, button: MenuButton) -> None:
        action = button.action
        if action == "quit":
            self._confirm_quit()
        elif action == "chat":
            self._hide_menu()
            self.toggle_input()
        elif action == "manage":
            self._hide_menu()
            self.open_whitelist()
        elif action == "create":
            self._hide_menu()
            self.open_creator()
        else:
            self.play_animation(action, from_menu=True)

    def open_creator(self) -> None:
        from .creator.wizard import CreatePetWizard

        self._wizard = CreatePetWizard(
            config=self.settings,
            paths=self.paths,
            on_created=self._on_character_created,
            font_name=self._font_name,
        )
        self._wizard.open()

    def open_whitelist(self) -> None:
        from .whitelist_panel import WhitelistPopup

        self._whitelist = WhitelistPopup(
            agent=self.agent,
            paths=self.paths,
            font_name=self._font_name,
        )
        self._whitelist.open()

    def _on_character_created(self, key: str) -> None:
        try:
            self.reload_character(key)
        except Exception as exc:
            self.show_bubble("切换角色失败：" + str(exc))

    def reload_character(self, key: str) -> None:
        """Swap the visible pet without restarting the app."""
        if self.pet is None or self._root is None:
            return
        character = load_character(key, self.paths)
        old = self.pet
        position = old.pos
        old.stop()
        self._root.remove_widget(old)

        pet = PetWidget(
            character,
            height=self.settings.ui.pet_height,
            walk_speed=self.settings.ui.walk_speed,
            jump_height=self.settings.ui.jump_height,
        )
        pet.pos = position
        self._root.add_widget(pet, index=0)
        self.pet = pet
        self.character = character
        pet.clamp_to_screen()

        self.settings.character = key
        save_config(self.settings, self.paths)
        self.hide_bubble()
        self.show_bubble("我是{}，请多关照～".format(character.name))

    def _show_menu(self) -> None:
        if self.pet is None:
            return
        self.hide_bubble()
        if self._menu_event is not None:
            self._menu_event.cancel()
        center = self.pet.center
        radius = max(170.0, self.pet.height * 0.72)
        layout_menu(self.menu_buttons, center, radius)
        for button in self.menu_buttons:
            button.x = min(max(0.0, button.x), max(0.0, Window.width - button.width))
            button.y = min(max(0.0, button.y), max(0.0, Window.height - button.height))
        self.menu_visible = True
        self._menu_event = Clock.schedule_once(
            lambda _dt: self._hide_menu(), self.settings.ui.menu_seconds
        )

    def _hide_menu(self) -> None:
        for button in self.menu_buttons:
            button.pos = (-500, -500)
        self.menu_visible = False
        if self._menu_event is not None:
            self._menu_event.cancel()
            self._menu_event = None

    # --------------------------------------------------------------- bubble
    def show_bubble(self, text: str, auto_hide: bool = True) -> None:
        if self.pet is None or self._root is None:
            return
        self.hide_bubble()
        gap = 8
        bubble_width = 244.0
        space_right = Window.width - self.pet.right
        tail_side = "left" if space_right >= bubble_width + gap else "right"
        bubble = SpeechBubble(
            text,
            width=bubble_width,
            font_name=self._font_name,
            max_chars=self.settings.ui.max_bubble_chars,
            tail_side=tail_side,
        )
        self._root.add_widget(bubble)
        self._position_bubble(bubble)
        self.bubble = bubble
        if auto_hide:
            self._bubble_event = Clock.schedule_once(
                self.hide_bubble, self.settings.ui.bubble_seconds
            )

    def _position_bubble(self, bubble: SpeechBubble) -> None:
        if self.pet is None:
            return
        gap = 8.0
        if bubble.tail_side == "left":
            x = self.pet.right + gap
        else:
            x = self.pet.x - bubble.width - gap
        x = max(0.0, min(x, Window.width - bubble.width))
        y = max(
            0.0,
            min(self.pet.center_y - bubble.height / 2, Window.height - bubble.height),
        )
        bubble.pos = (x, y)

    def hide_bubble(self, _dt: float | None = None) -> None:
        if self._bubble_event is not None:
            self._bubble_event.cancel()
            self._bubble_event = None
        if self.bubble is not None and self._root is not None:
            self._root.remove_widget(self.bubble)
            self.bubble = None

    # ----------------------------------------------------------- input panel
    def toggle_input(self) -> None:
        if self._input_open:
            self._input_open = False
            self.input_panel.hide_input()
            return
        self._input_open = True
        if self.pet is not None:
            self.input_panel.set_anchor(
                self.pet.x, self.pet.y, self.pet.width, self.pet.height
            )
        self.input_panel.show_input()

    def _input_hidden(self) -> None:
        self._input_open = False

    def get_apps(self) -> dict[str, str]:
        from .agent import BUILTIN_APPS

        return {**BUILTIN_APPS, **self.agent.user_apps}

    # -------------------------------------------------------------- confirm
    def show_confirm(self, tool: str, args: dict) -> None:
        description = {"shutdown": "锁屏 / 关机 / 重启"}.get(tool, tool)
        content = BoxLayout(orientation="vertical", spacing=10, padding=16)
        message = Label(
            text="桌宠想执行：{}\n{}\n是否允许？".format(description, args),
            font_name=self._font_name,
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=110,
        )
        message.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        content.add_widget(message)
        buttons = BoxLayout(spacing=10, size_hint_y=None, height=44)
        allow = Button(text="允许", background_color=(0.3, 0.75, 0.45, 1))
        cancel = Button(text="取消", background_color=(0.6, 0.6, 0.64, 1))
        buttons.add_widget(allow)
        buttons.add_widget(cancel)
        content.add_widget(buttons)

        popup = Popup(
            title="操作确认",
            content=content,
            size_hint=(None, None),
            size=(380, 230),
            auto_dismiss=False,
        )

        def do_allow(_button) -> None:
            popup.dismiss()
            self.show_bubble(self.agent.execute_confirmed(tool, args))

        allow.bind(on_release=do_allow)
        cancel.bind(on_release=lambda _button: popup.dismiss())
        popup.open()

    def _confirm_quit(self) -> None:
        self._hide_menu()
        content = BoxLayout(orientation="vertical", spacing=10, padding=16)
        content.add_widget(
            Label(text="确定要关闭桌面宠物吗？", font_name=self._font_name, halign="center")
        )
        buttons = BoxLayout(spacing=10, size_hint_y=None, height=44)
        confirm = Button(text="确定", background_color=(0.9, 0.35, 0.4, 1))
        cancel = Button(text="取消", background_color=(0.6, 0.6, 0.64, 1))
        buttons.add_widget(confirm)
        buttons.add_widget(cancel)
        content.add_widget(buttons)
        popup = Popup(
            title="关闭确认",
            content=content,
            size_hint=(None, None),
            size=(320, 190),
            auto_dismiss=False,
        )
        confirm.bind(on_release=lambda _b: (popup.dismiss(), self.stop(), Window.close()))
        cancel.bind(on_release=lambda _b: popup.dismiss())
        popup.open()

    # ---------------------------------------------------------------- touch
    def _on_touch_down(self, _window, touch) -> bool:
        if self.pet is None:
            return False
        button = getattr(touch, "button", "left")
        if button == "right":
            if self.pet.collide_point(*touch.pos):
                if self.menu_visible:
                    self._hide_menu()
                else:
                    self._show_menu()
                return True
            self._hide_menu()
            return False

        if button != "left":
            return False
        if any(item.collide_point(*touch.pos) for item in self.menu_buttons):
            return False
        if self.pet.collide_point(*touch.pos):
            now = time.time()
            if now - self._last_click < 0.35:
                self._last_click = 0.0
                self.toggle_input()
                return True
            self._last_click = now
            self._hide_menu()
            self._dragging = True
            self._drag_offset = (touch.x - self.pet.x, touch.y - self.pet.y)
            self.pet.walk_target = None
            self.pet.cancel_motion()
            return True
        self._hide_menu()
        return False

    def _on_touch_move(self, _window, touch) -> bool:
        if not self._dragging or self.pet is None:
            return False
        new_x = max(0.0, min(touch.x - self._drag_offset[0], Window.width - self.pet.width))
        new_y = max(0.0, min(touch.y - self._drag_offset[1], Window.height - self.pet.height))
        self.pet.pos = (new_x, new_y)
        if self.menu_visible:
            self._show_menu()
        if self.bubble is not None:
            self._position_bubble(self.bubble)
        return True

    def _on_touch_up(self, _window, _touch) -> bool:
        self._dragging = False
        return False

    def _on_keyboard(self, _window, key, *_args) -> bool:
        if key == 27:
            self._hide_menu()
            self.hide_bubble()
            return True
        return False

    def _on_window_resize(self, *_args) -> None:
        if self.pet is not None:
            self.pet.clamp_to_screen()

    def on_stop(self) -> None:
        self.input_panel.close()
        self.agent.close()
        super().on_stop()

