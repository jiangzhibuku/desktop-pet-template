# 架构说明

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `__main__.py` | 检查平台、开启 DPI 感知、捕获启动异常并弹窗 |
| `app.py` | Kivy App：窗口、菜单、拖拽、气泡、调度、确认框 |
| `pet.py` | 帧动画播放、散步移动、跳跃动画、尺寸适配 |
| `agent.py` | 与 OpenAI 兼容接口对话、工具调用、记忆/统计/日志 |
| `characters.py` | 角色包发现、`character.json` 解析、帧排序与校验 |
| `config.py` | 默认值 + JSON + 环境变量合并，字体解析 |
| `input_panel.py` | 独立 Tk 线程：聊天输入框 |
| `whitelist_panel.py` | 粉白卡片式白名单管理（Kivy） |
| `storage.py` | 线程安全的原子 JSON 读写 |
| `widgets.py` | 气泡、圆形轮盘按钮 |
| `win32_window.py` | 全屏铺满桌面、透明色键、隐藏任务栏图标 |
| `paths.py` | 仓库资源目录 vs 用户数据目录 |
| `creator/spec.py` | 角色规格 + 中英文关键词解析 |
| `creator/draw.py` | 离线程序化绘制物种/配饰/花纹/动作 |
| `creator/image_pack.py` | 图片去背、裁切、变换动作 |
| `creator/pack.py` | 写角色包、预览、来源/授权文件 |
| `creator/pipeline.py` | 图片/文字/旧帧三种生成流程 |
| `creator/ai.py` | 可选的 LLM 解析与图片生成 |
| `creator/cli.py` | 命令行入口 |
| `creator/native_dialog.py` | Windows 原生图片选择框（Tk 线程，不阻塞 Kivy） |
| `creator/wizard.py` | 应用内 Kivy 创建向导 |

## 线程模型

```text
┌─────────────────────────────────────────────┐
│ Kivy 主线程                                  │
│  - 渲染、触摸、动画、Clock 调度              │
│  - 每 50ms poll 结果队列                     │
│  - 每 16ms 处理水平移动                      │
└───────────────┬─────────────────────────────┘
                │ queue.Queue（线程安全）
┌───────────────┴─────────────┐   ┌──────────────────────────┐
│ Agent worker（daemon）       │   │ Tk 线程（daemon）         │
│  - 读取 input_queue          │   │  - 输入框 / 白名单窗口     │
│  - 调 API、执行工具          │   │  - 只通过 Event 与主线程通信│
│  - 写 result_queue           │   └──────────────────────────┘
└─────────────────────────────┘
```

- Kivy 控件**只**在 Kivy 主线程里操作。
- Tk 控件**只**在 Tk 线程里操作；跨线程只传 `Event` 和普通元组。
- Agent 工具在 worker 线程执行，耗时操作不会卡住动画。
- 定时器/护眼提醒在独立 `threading.Timer` 中触发，回调再投递到队列。

## 一次聊天的数据流

1. 双击宠物 → `InputPanel.show_input()`。
2. 回车 → `on_submit(text)` → `input_queue.put(text)`。
3. worker 调 `Agent.chat(text)`。
4. Agent 把 system prompt（人设 + 记忆 + 当前时间）和历史消息发给模型。
5. 模型返回 `tool_calls` 时，Agent 依次执行工具，把结果作为 `role=tool` 回传，
   最多 `max_tool_rounds` 轮。
6. 最终文本 → `result_queue.put((reply, actions))`。
7. Kivy `_poll` 取出，显示气泡；如果动作里有 `animation`，切换动画。

## 窗口透明原理

1. Kivy 窗口无边框、置顶。
2. `win32_window.setup_desktop_window()` 把窗口扩展到整个桌面。
3. 设置 `WS_EX_LAYERED` + `LWA_COLORKEY`，把纯黑设为透明色键。
4. 设置 `WS_EX_TOOLWINDOW`，不在任务栏显示。

因此透明区域不仅看不见，鼠标也可以点到底下的桌面/窗口。副作用：

- 远程桌面、禁用 DWM 的虚拟机里可能变成黑底；
- 某些录屏/截图工具对分层窗口支持不好。

## 角色生成流程

```text
prompt ──► spec.parse_prompt ──► CharacterSpec ──► draw.build_frames ──┐
   │              │（可选 ai.spec_from_prompt）                        │
   │              └──────────────► ai.generate_image ──► image_pack ──┤
image ──────────────────────────► image_pack ─────────────────────────┤
frames ─────────────────────────► pipeline.import_frames ─────────────┤
                                                                       ▼
                                                          pack.save_pack
                                                                       │
                                      %APPDATA%/DesktopPet/characters/<key>
                                                                       │
                                                          config.character
                                                                       │
                                                    app.reload_character()
```

- 生成器只依赖 Pillow + requests，不导入 Kivy；命令行可在无 GUI 环境运行。
- 向导在 worker 线程调用 `pipeline`，通过 `queue.Queue` 把结果交回 Kivy 主线程。
- `reload_character` 停止旧 `PetWidget` 的 Clock、移除旧 widget、创建新 widget，
  并写回 `config.json`；不需要重启应用。
- 生成的角色包与仓库分离，避免把用户素材/第三方素材提交到 Git。

## 数据与安全边界

- **仓库内**：代码、CC0 占位素材、文档。
- **用户目录**：配置、Key、记忆、待办、日志、截图、第三方角色包。
- **网络**：仅聊天/视觉模型与你配置的接口；天气走 `wttr.in`。
- **工具**：`open_app` 仅白名单；`shutdown` 必须确认；`open_url` 仅 http/https。

## 扩展点

### 新增一个工具

1. 在 `agent.py` 的 `TOOLS` 里加 JSON Schema。
2. 在 `Agent._tool_map` 注册同名方法。
3. 方法返回字符串（会回传给模型）。
4. 在 `tests/test_agent.py` 里保证 `TOOLS` 与 `_tool_map` 一致（已有测试会自动覆盖）。
5. 涉及危险操作时，把工具名加入 `CONFIRM_TOOLS` 并在 UI 里处理确认。

### 新增动画

1. 在 `characters.ANIMATION_NAMES` 加名字。
2. 在 `FOLDER_ALIASES` 加默认文件夹。
3. 在 `pet.play()` 处理特殊行为（尺寸、时长、移动）。
4. 在 `app.MENU_ITEMS` 加菜单项。

### 换 UI 框架

`Agent`、`storage`、`characters`、`config` 不依赖 Kivy，可以复用到 PyQt/Tk 前端。
