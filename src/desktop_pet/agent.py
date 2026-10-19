"""The LLM agent and the desktop tools it is allowed to call.

Design notes
------------
* The API key is supplied through :class:`~desktop_pet.config.Config`; it is
  never stored in source code.
* Every tool has a narrow, explicit job.  ``shutdown`` is the only tool that
  always asks for confirmation in the UI.
* Platform-specific imports (pywin32, tkinter) are done lazily so the module
  can be imported by tests on non-Windows machines.
"""

from __future__ import annotations

import base64
import ctypes
import datetime as dt
import io
import json
import os
import platform
import queue
import random
import subprocess
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import requests

from .config import Config
from .paths import AppPaths
from .storage import JsonStore

BUILTIN_APPS = {
    "记事本": "notepad",
    "计算器": "calc",
    "画图": "mspaint",
    "命令提示符": "cmd",
    "资源管理器": "explorer",
    "浏览器": "msedge",
    "控制面板": "control",
}

CONFIRM_TOOLS = {"shutdown"}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "play_animation",
            "description": "切换桌宠动画",
            "parameters": {
                "type": "object",
                "properties": {
                    "animation": {
                        "type": "string",
                        "enum": ["idle", "walk", "jump", "ultra"],
                        "description": "待机 idle / 散步 walk / 跳跃 jump / 大招 ultra",
                    }
                },
                "required": ["animation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": "让桌宠说一句话（显示在气泡里）",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "打开电脑里的软件（仅限白名单）",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "软件名，如 记事本、浏览器"}
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "在浏览器打开一个网址",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "完整网址，含 https://"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "用浏览器搜索关键词",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "打开文件或文件夹",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件或文件夹的绝对路径"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "查询当前时间、日期、系统版本、内存占用",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard",
            "description": "把文字复制到剪贴板",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "设置定时提醒，到点后桌宠提醒你",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "number", "description": "多少分钟后提醒"},
                    "message": {"type": "string", "description": "提醒内容"},
                },
                "required": ["minutes", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown",
            "description": "锁屏、关机或重启电脑（需用户确认）",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["lock", "shutdown", "restart"]}
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "记住用户的重要信息（称呼、喜好、常用软件等），长期保存",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "信息类别，如 称呼/喜欢的游戏/工作"},
                    "value": {"type": "string", "description": "信息内容"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "查询某城市的实时天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，如 杭州"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pomodoro",
            "description": "开始一个番茄钟专注计时，到点提醒休息",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "number", "description": "专注分钟数，默认 25"}
                },
                "required": ["minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "window",
            "description": "窗口管理：列出可见窗口、切换到指定窗口、最小化窗口",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "activate", "minimize"]},
                    "title": {"type": "string", "description": "窗口标题关键词"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "media",
            "description": "媒体控制：音量加减、静音、播放暂停、上一首下一首",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "volume_up",
                            "volume_down",
                            "mute",
                            "play_pause",
                            "next",
                            "prev",
                        ],
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo",
            "description": "待办清单：添加、查看、完成待办",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "done"]},
                    "item": {"type": "string", "description": "待办内容或编号"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eye_rest",
            "description": "开启护眼提醒，每隔一段时间提醒看远方休息",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {"type": "number", "description": "间隔分钟数，默认 45"}
                },
                "required": ["minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "截取当前屏幕并理解内容，返回屏幕描述并打开截图",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出文件夹里的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件夹路径，留空则默认用户目录"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_file",
            "description": "在文件夹里按名字搜索文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "文件名关键字，如 报告"},
                    "path": {"type": "string", "description": "搜索的文件夹，留空则默认桌面"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dice",
            "description": "掷骰子出随机数，用于抽签/做决定",
            "parameters": {
                "type": "object",
                "properties": {
                    "sides": {"type": "number", "description": "骰子面数，默认 6"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "feed",
            "description": "喂食桌宠，增加亲密度和经验",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pet_status",
            "description": "查看桌宠的养成状态：等级、经验、喂食次数、互动次数",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class Agent:
    def __init__(self, config: Config, paths: AppPaths) -> None:
        self.config = config
        self.paths = paths
        self.messages: list[dict[str, Any]] = []
        self.actions: list[dict[str, Any]] = []
        self.offline = not config.api.configured
        self.lock = threading.RLock()
        self.reminder_cb = None
        self.confirm_queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue()
        self.timers: list[threading.Timer] = []
        self._log_lock = threading.Lock()

        self.memory_store = JsonStore(paths.memory, {})
        self.todo_store = JsonStore(paths.todos, [])
        self.stats_store = JsonStore(paths.stats, {})
        self.whitelist_store = JsonStore(paths.whitelist, {})
        self.user_apps = self._load_user_apps()

        self._tool_map = {
            "play_animation": self._play_animation,
            "speak": self._speak,
            "open_app": self._open_app,
            "open_url": self._open_url,
            "search": self._search,
            "open_file": self._open_file,
            "system_info": self._system_info,
            "clipboard": self._clipboard,
            "set_timer": self._set_timer,
            "shutdown": self._shutdown,
            "remember": self._remember,
            "weather": self._weather,
            "pomodoro": self._pomodoro,
            "window": self._window,
            "media": self._media,
            "todo": self._todo,
            "eye_rest": self._eye_rest,
            "screenshot": self._screenshot,
            "list_dir": self._list_dir,
            "find_file": self._find_file,
            "dice": self._dice,
            "feed": self._feed,
            "pet_status": self._pet_status,
        }

    # ------------------------------------------------------------------ data
    def _load_user_apps(self) -> dict[str, str]:
        data = self.whitelist_store.load()
        if not isinstance(data, dict):
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save_user_apps(self) -> None:
        self.whitelist_store.save(self.user_apps)

    def add_app(self, name: str, command: str) -> str:
        name, command = name.strip(), command.strip()
        if not name or not command:
            return "应用名和启动命令都要填"
        self.user_apps[name] = command
        self._save_user_apps()
        return "已添加：" + name

    def remove_app(self, name: str) -> str:
        if name in BUILTIN_APPS:
            return "内置应用不能删除：" + name
        if name in self.user_apps:
            del self.user_apps[name]
            self._save_user_apps()
            return "已移除：" + name
        return "白名单里没有：" + name

    def _load_memory(self) -> dict[str, Any]:
        data = self.memory_store.load()
        return data if isinstance(data, dict) else {}

    def _load_stats(self) -> dict[str, Any]:
        data = self.stats_store.load()
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------ misc
    def _log(self, name: str, args: dict[str, Any], result: Any) -> None:
        try:
            line = "[{}] {} {} -> {}\n".format(
                dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                json.dumps(args, ensure_ascii=False),
                result,
            )
            with self._log_lock:
                with (self.paths.logs / "operations.log").open("a", encoding="utf-8") as handle:
                    handle.write(line)
        except OSError:
            pass

    def _run_tool(self, name: str, args: dict[str, Any]) -> Any:
        fn = self._tool_map.get(name)
        if fn is None:
            return "没有这个工具"
        try:
            return fn(**args)
        except Exception as exc:  # tools must never crash the UI thread
            self._log(name, args, "失败：" + str(exc))
            return "执行失败：" + str(exc)

    # ------------------------------------------------------------- animation
    def _play_animation(self, animation: str) -> str:
        return "动画已切换：" + animation

    def _speak(self, text: str) -> str:
        return "ok"

    # ---------------------------------------------------------------- system
    def _open_app(self, app_name: str) -> str:
        all_apps = {**BUILTIN_APPS, **self.user_apps}
        command = all_apps.get(app_name)
        if not command:
            msg = "白名单里没有" + app_name + "，右键「扩展」可以添加"
            self._log("open_app", {"app_name": app_name}, msg)
            return msg
        try:
            if os.path.exists(command):
                subprocess.Popen([command], cwd=os.path.dirname(command) or None)
            else:
                subprocess.Popen(command, shell=True)
            msg = "已打开" + app_name
        except Exception as exc:
            msg = "打开失败：" + str(exc)
        self._log("open_app", {"app_name": app_name}, msg)
        return msg

    def _open_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return "只支持 http/https 网址"
        webbrowser.open(url)
        msg = "已打开网址：" + url
        self._log("open_url", {"url": url}, msg)
        return msg

    def _search(self, query: str) -> str:
        url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query)
        webbrowser.open(url)
        msg = "已搜索：" + query
        self._log("search", {"query": query}, msg)
        return msg

    def _open_file(self, path: str) -> str:
        target = Path(path).expanduser()
        if not target.exists():
            return "路径不存在：" + str(target)
        try:
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            return "打开失败：" + str(exc)
        msg = "已打开：" + str(target)
        self._log("open_file", {"path": str(target)}, msg)
        return msg

    def _memory_info(self) -> tuple[float, float]:
        if os.name != "nt":
            return 0.0, 0.0

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys / 1024**3, stat.ullAvailPhys / 1024**3

    def _system_info(self) -> str:
        now = dt.datetime.now()
        total, avail = self._memory_info()
        if total:
            msg = "现在是 {}，{}，系统内存共 {:.1f}GB，剩余 {:.1f}GB".format(
                now.strftime("%Y-%m-%d %H:%M"), platform.platform(), total, avail
            )
        else:
            msg = "现在是 {}，{}".format(now.strftime("%Y-%m-%d %H:%M"), platform.platform())
        self._log("system_info", {}, msg)
        return msg

    def _clipboard(self, text: str) -> str:
        if os.name != "nt":
            return "剪贴板工具目前只支持 Windows"
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
        finally:
            win32clipboard.CloseClipboard()
        msg = "已复制到剪贴板：" + text
        self._log("clipboard", {"text": text}, msg)
        return msg

    def _timer(self, minutes: float, message: str, repeat: bool = False) -> None:
        delay = max(1.0, float(minutes)) * 60
        timer: threading.Timer

        def fire() -> None:
            if self.reminder_cb:
                try:
                    self.reminder_cb(message)
                except Exception:
                    pass
            if repeat:
                self._timer(minutes, message, repeat=True)

        timer = threading.Timer(delay, fire)
        timer.daemon = True
        timer.start()
        self.timers.append(timer)

    def _set_timer(self, minutes: float, message: str) -> str:
        self._timer(minutes, "提醒：" + message)
        msg = "好的，{} 分钟后提醒你：{}".format(minutes, message)
        self._log("set_timer", {"minutes": minutes, "message": message}, msg)
        return msg

    def _pomodoro(self, minutes: float) -> str:
        self._timer(minutes, "番茄钟结束！休息 5 分钟吧")
        msg = "番茄钟已开始，{} 分钟后提醒你休息".format(minutes)
        self._log("pomodoro", {"minutes": minutes}, msg)
        return msg

    def _eye_rest(self, minutes: float = 45) -> str:
        minutes = max(1.0, float(minutes))
        self._timer(minutes, "护眼提醒：该休息啦，看看窗外 5 分钟吧", repeat=True)
        msg = "已开启护眼提醒，每 {} 分钟提醒一次".format(int(minutes))
        self._log("eye_rest", {"minutes": minutes}, msg)
        return msg

    def _remember(self, key: str, value: str) -> str:
        def mutate(data: dict[str, Any]) -> None:
            data[key] = value

        self.memory_store.update(mutate)
        msg = "已记住：" + key + " = " + value
        self._log("remember", {"key": key, "value": value}, msg)
        return msg

    def _weather(self, city: str) -> str:
        try:
            url = "https://wttr.in/" + urllib.parse.quote(city) + "?format=3&lang=zh"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "desktop-pet"})
            resp.raise_for_status()
            msg = resp.text.strip()
        except Exception as exc:
            msg = "天气查询失败：" + str(exc)
        self._log("weather", {"city": city}, msg)
        return msg

    # ------------------------------------------------------------- windows UI
    def _window(self, action: str, title: str = "") -> str:
        if os.name != "nt":
            return "窗口管理目前只支持 Windows"
        import win32api
        import win32con
        import win32gui

        hwnds: list[tuple[str, int]] = []

        def callback(hwnd: int, _extra: Any) -> None:
            text = win32gui.GetWindowText(hwnd)
            if win32gui.IsWindowVisible(hwnd) and text.strip():
                hwnds.append((text, hwnd))

        win32gui.EnumWindows(callback, None)
        if action == "list":
            if not hwnds:
                return "没有找到可见窗口"
            return "当前窗口：\n" + "\n".join(text for text, _ in hwnds[:15])

        target = None
        if title:
            for text, hwnd in hwnds:
                if title.lower() in text.lower():
                    target = hwnd
                    break
        if target is None:
            return "没找到包含「" + title + "」的窗口"
        if action == "activate":
            try:
                win32gui.ShowWindow(target, win32con.SW_RESTORE)
                win32api.keybd_event(0x12, 0, 0, 0)
                win32gui.SetForegroundWindow(target)
                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
                return "已切换到：" + win32gui.GetWindowText(target)
            except Exception as exc:
                return "切换失败：" + str(exc)
        if action == "minimize":
            win32gui.ShowWindow(target, win32con.SW_MINIMIZE)
            return "已最小化：" + win32gui.GetWindowText(target)
        return "不支持的操作：" + action

    def _media(self, action: str) -> str:
        if os.name != "nt":
            return "媒体控制目前只支持 Windows"
        import win32api
        import win32con

        keys = {
            "volume_up": 0xAF,
            "volume_down": 0xAE,
            "mute": 0xAD,
            "play_pause": 0xB3,
            "next": 0xB0,
            "prev": 0xB1,
        }
        key = keys.get(action)
        if not key:
            return "不支持的媒体操作：" + action
        try:
            win32api.keybd_event(key, 0, 0, 0)
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "已执行：" + action
        except Exception as exc:
            return "媒体控制失败：" + str(exc)

    # ----------------------------------------------------------------- todos
    def _todo(self, action: str, item: str = "") -> str:
        todos = self.todo_store.load()
        if not isinstance(todos, list):
            todos = []

        if action == "add":
            if not item.strip():
                return "待办内容不能为空"
            todos.append(item.strip())
            self.todo_store.save(todos)
            return "已添加待办：" + item
        if action == "list":
            if not todos:
                return "待办清单是空的"
            return "待办清单：\n" + "\n".join(
                "{}. {}".format(index + 1, text) for index, text in enumerate(todos)
            )
        if action == "done":
            index = None
            if item.isdigit():
                index = int(item) - 1
            else:
                for i, text in enumerate(todos):
                    if item in text:
                        index = i
                        break
            if index is None or not (0 <= index < len(todos)):
                return "没找到这条待办：" + item
            done_item = todos.pop(index)
            self.todo_store.save(todos)
            return "已完成：" + str(done_item)
        return "不支持的操作：" + action

    # ------------------------------------------------------------- screenshot
    def _vision_description(self, image_bytes: bytes) -> str:
        if self.offline:
            return "（未配置视觉模型，只保存了截图）"
        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            response = requests.post(
                self.config.api.base_url + "/chat/completions",
                json={
                    "model": self.config.api.vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "用两三句话描述这张屏幕截图的内容，说明屏幕上有什么",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "data:image/png;base64," + encoded},
                                },
                            ],
                        }
                    ],
                },
                headers={"Authorization": "Bearer " + self.config.api.api_key},
                timeout=max(60.0, self.config.api.timeout),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            return "（图片理解失败：" + str(exc) + "）"

    def _screenshot(self) -> str:
        if os.name != "nt":
            return "截屏工具目前只支持 Windows"
        from PIL import ImageGrab

        image = ImageGrab.grab()
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        shot_path = self.paths.screenshots / f"screen_{stamp}.png"
        image.save(shot_path)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        description = self._vision_description(buffer.getvalue())
        try:
            os.startfile(str(shot_path))  # type: ignore[attr-defined]
        except OSError:
            pass
        msg = "已截屏并保存到 {}。屏幕内容：{}".format(shot_path, description)
        self._log("screenshot", {"path": str(shot_path)}, msg)
        return msg

    # ----------------------------------------------------------------- files
    def _list_dir(self, path: str = "") -> str:
        target = Path(path).expanduser() if path else Path.home()
        if not target.is_dir():
            return "路径不存在或不是文件夹：" + str(target)
        try:
            items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError as exc:
            return "无法读取：" + str(exc)
        if not items:
            return str(target) + " 是空文件夹"
        lines = [
            ("[文件夹] " if item.is_dir() else "[文件] ") + item.name for item in items[:30]
        ]
        more = "…（还有 {} 项）".format(len(items) - 30) if len(items) > 30 else ""
        msg = "{}\n{}\n{}".format(target, "\n".join(lines), more).rstrip()
        self._log("list_dir", {"path": str(target)}, msg)
        return msg

    def _find_file(self, name: str, path: str = "") -> str:
        if path:
            target = Path(path).expanduser()
        else:
            desktop = Path.home() / "Desktop"
            target = desktop if desktop.is_dir() else Path.home()
        hits: list[str] = []
        try:
            for root, _dirs, files in os.walk(target):
                for filename in files:
                    if name.lower() in filename.lower():
                        hits.append(os.path.join(root, filename))
                        if len(hits) >= 20:
                            break
                if len(hits) >= 20:
                    break
        except OSError:
            pass
        if not hits:
            return "没找到包含「" + name + "」的文件"
        msg = "找到 {} 个：\n{}".format(len(hits), "\n".join(hits))
        self._log("find_file", {"name": name, "path": str(target)}, msg)
        return msg

    def _dice(self, sides: float = 6) -> str:
        n = max(1, int(sides))
        msg = "掷出了 {} 面骰子：{}".format(n, random.randint(1, n))
        self._log("dice", {"sides": n}, msg)
        return msg

    # ------------------------------------------------------------------- pet
    def _feed(self) -> str:
        stats = self._load_stats()
        stats["exp"] = int(stats.get("exp", 0)) + 15
        stats["feed_count"] = int(stats.get("feed_count", 0)) + 1
        self.stats_store.save(stats)
        level = stats["exp"] // 100 + 1
        msg = "喂食成功！经验 +15，当前等级 Lv.{}".format(level)
        self._log("feed", {}, msg)
        return msg

    def _pet_status(self) -> str:
        stats = self._load_stats()
        exp = int(stats.get("exp", 0))
        level = exp // 100 + 1
        next_exp = level * 100 - exp
        msg = "桌宠状态：等级 Lv.{}，经验 {}，距升级还差 {}，喂食 {} 次，互动 {} 次".format(
            level,
            exp,
            next_exp,
            stats.get("feed_count", 0),
            stats.get("interact_count", 0),
        )
        self._log("pet_status", {}, msg)
        return msg

    # ---------------------------------------------------------------- confirm
    def _shutdown(self, action: str) -> str:
        if action not in {"lock", "shutdown", "restart"}:
            return "不支持的操作：" + action
        self.confirm_queue.put(("shutdown", {"action": action}))
        msg = {"lock": "锁屏", "shutdown": "关机", "restart": "重启"}[action] + "需要你确认"
        self._log("shutdown", {"action": action}, "等待用户确认")
        return msg

    def execute_confirmed(self, name: str, args: dict[str, Any]) -> str:
        if name != "shutdown":
            return "未知操作"
        action = args.get("action")
        try:
            if action == "lock":
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
                msg = "已锁屏"
            elif action == "shutdown":
                subprocess.Popen(["shutdown", "/s", "/t", "5"])
                msg = "5 秒后关机"
            elif action == "restart":
                subprocess.Popen(["shutdown", "/r", "/t", "5"])
                msg = "5 秒后重启"
            else:
                msg = "未知操作"
        except Exception as exc:
            msg = "执行失败：" + str(exc)
        self._log(name, args, msg)
        return msg

    # ------------------------------------------------------------------- llm
    def _call(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        response = requests.post(
            self.config.api.base_url + "/chat/completions",
            json={
                "model": self.config.api.model,
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
            },
            headers={"Authorization": "Bearer " + self.config.api.api_key},
            timeout=self.config.api.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    def _trim_history(self) -> None:
        limit = self.config.agent.history_limit
        if len(self.messages) <= limit:
            return
        self.messages = self.messages[-limit:]
        # Never start with an orphaned tool result or an assistant tool call
        # whose results were trimmed away: both are rejected by the API.
        while self.messages:
            first = self.messages[0]
            if first.get("role") == "tool" or (
                first.get("role") == "assistant" and first.get("tool_calls")
            ):
                self.messages.pop(0)
                continue
            break

    def _system_message(self) -> dict[str, str]:
        memory = self._load_memory()
        memory_text = json.dumps(memory, ensure_ascii=False) if memory else "（暂无）"
        now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        content = (
            self.config.agent.system_prompt
            + "\n你记得的关于用户的信息："
            + memory_text
            + "\n当前时间："
            + now
        )
        return {"role": "system", "content": content}

    def chat(self, text: str) -> str:
        if self.offline:
            return (
                "还没有配置 API Key。请编辑 "
                + str(self.paths.config)
                + " 里的 api.api_key，或设置 DESKTOP_PET_API_KEY 环境变量。"
            )
        with self.lock:
            self.actions = []
            self.messages.append({"role": "user", "content": text})
            self._trim_history()
            for _ in range(self.config.agent.max_tool_rounds):
                message = self._call([self._system_message()] + self.messages)
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    content = (message.get("content") or "").strip()
                    while content.startswith("speak"):
                        content = content[5:].lstrip("\n").strip()
                    self.messages.append({"role": "assistant", "content": content})
                    self._bump_interaction()
                    return content

                self.messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                )
                for call in tool_calls:
                    function = call.get("function", {})
                    name = function.get("name", "")
                    try:
                        args = json.loads(function.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    if not isinstance(args, dict):
                        args = {}
                    self.actions.append(args)
                    result = self._run_tool(name, args)
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id", ""),
                            "content": str(result),
                        }
                    )
                self._trim_history()
            return "我有点忙，稍后再聊"

    def _bump_interaction(self) -> None:
        stats = self._load_stats()
        stats["exp"] = int(stats.get("exp", 0)) + 5
        stats["interact_count"] = int(stats.get("interact_count", 0)) + 1
        self.stats_store.save(stats)

    def proactive_talk(self) -> str:
        if self.offline:
            return ""
        try:
            with self.lock:
                memory = self._load_memory()
                memory_text = json.dumps(memory, ensure_ascii=False) if memory else "（暂无）"
                messages = [
                    {
                        "role": "system",
                        "content": self.config.agent.system_prompt
                        + "\n关于他的信息："
                        + memory_text,
                    },
                    {
                        "role": "user",
                        "content": (
                            "现在是你主动和他说句话的时刻。可以是关心他吃饭/休息/天气，"
                            "也可以是随便聊一句日常、分享心情、或者小小撒娇。"
                            "温柔简短，一两句话就好（不要调用任何工具）。"
                        ),
                    },
                ]
                response = requests.post(
                    self.config.api.base_url + "/chat/completions",
                    json={"model": self.config.api.model, "messages": messages},
                    headers={"Authorization": "Bearer " + self.config.api.api_key},
                    timeout=self.config.api.timeout,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""

    def reset_history(self) -> None:
        with self.lock:
            self.messages.clear()

    def close(self) -> None:
        for timer in self.timers:
            timer.cancel()
        self.timers.clear()
