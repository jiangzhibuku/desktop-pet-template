# Desktop Pet · 桌面宠物

一个跑在 Windows 桌面上的透明桌宠：会待机、散步、跳跃、放大招，也能通过大模型聊天，并在你确认后帮忙打开软件、查天气、管理待办、设置提醒。

![Desktop Pet 预览](docs/preview.png)

![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)
[![License: MIT](https://img.shields.io/badge/code-MIT-green)](LICENSE)
[![Assets: CC0](https://img.shields.io/badge/placeholder%20art-CC0-green)](assets/LICENSE)

> [!IMPORTANT]
> **素材版权说明**
>
> 本仓库**不包含**任何第三方人物动画、角色立绘或字体。早期本地版本里使用的
> `daiji / dazhao / khqn / tiaoyue` 动画和 `ChillHuoFangSong` 字体来自第三方，
> **版权不属于本项目，也不能用于商业用途**，因此已从发布版本中移除。
>
> 仓库内置的「Mochi」是 `tools/generate_placeholder.py` 生成的**原创占位角色**，
> 以 CC0-1.0 释出，可自由使用、修改，包括商用。想换成自己的角色，请看
> [自定义角色](#自定义角色) 和 [`docs/ASSETS.md`](docs/ASSETS.md)。

---

## 目录

- [功能](#功能)
- [快速开始](#快速开始)
- [配置](#配置)
- [操作方式](#操作方式)
- [自定义角色](#自定义角色)
- [打包为 exe](#打包为-exe)
- [项目结构](#项目结构)
- [开发与测试](#开发与测试)
- [安全与隐私](#安全与隐私)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 功能

- **透明桌宠窗口**：无边框、置顶、不占任务栏，鼠标可穿透透明区域。
- **帧动画**：待机（3 套）、散步、跳跃、大招；帧率与尺寸由角色包定义。
- **拖拽与互动**：左键拖拽，双击弹出聊天框，右键打开轮盘菜单，`Esc` 收起。
- **大模型对话**：支持 OpenAI 兼容接口（默认智谱 `glm-4-flash`），带长期记忆与主动关心。
- **桌面工具**（共 23 个）：打开白名单软件、打开网址、搜索、天气、系统信息、剪贴板、番茄钟、护眼提醒、定时提醒、待办、窗口切换/最小化、媒体控制、截屏理解、文件浏览/搜索、掷骰子、喂食/状态、锁屏/关机/重启（必须二次确认）。
- **数据本地化**：配置、记忆、待办、统计、日志、截图全部放在 `%APPDATA%\DesktopPet`，不污染仓库。
- **可替换角色**：角色包与代码分离，自带原创占位角色，开箱即用。

## 快速开始

### 环境要求

- Windows 10 / 11
- Python 3.10 – 3.12（推荐 3.12）
- 可选：一个大模型 API Key（没有 Key 也能运行，只是不能聊天）

### 安装

```powershell
git clone https://github.com/<your-name>/desktop-pet.git
cd desktop-pet

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

### 配置 API Key（二选一）

第一次运行会自动生成 `%APPDATA%\DesktopPet\config.json`。把 Key 填进去：

```json
{
  "api": {
    "api_key": "你的 API Key"
  }
}
```

或者用环境变量（推荐，不会写进任何文件）：

```powershell
$env:DESKTOP_PET_API_KEY = "你的 API Key"
```

### 运行

```powershell
python run.py
```

也可以双击 `run.bat`，或：

```powershell
.\run.ps1
```

首次启动会在桌面左下角出现 Mochi，并弹出一句问候。没有配置 Key 时，宠物依然会动、会拖拽；聊天会提示你去配置。

> 默认接口是智谱 BigModel 的 OpenAI 兼容端点。换服务商时改
> `api.base_url` 和 `api.model` 即可，只要接口兼容 `/chat/completions` 与
> `tools`（function calling）。

## 配置

配置文件位置：

```
%APPDATA%\DesktopPet\config.json
```

可用 `DESKTOP_PET_HOME` 环境变量改到便携目录：

```powershell
$env:DESKTOP_PET_HOME = "D:\DesktopPetData"
```

完整示例见 [`config.example.json`](config.example.json)。

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `character` | `"mochi"` | 角色包名称，对应 `assets/characters/<名字>` 或用户目录下的同名文件夹 |
| `font` | `""` | 自定义字体路径；留空则自动找 `assets/fonts` 或系统中文字体 |
| `api.base_url` | 智谱端点 | OpenAI 兼容接口根地址 |
| `api.model` | `"glm-4-flash"` | 对话模型 |
| `api.vision_model` | `"glm-4v-flash"` | 截屏理解模型 |
| `api.api_key` | `""` | API Key；也可用 `DESKTOP_PET_API_KEY` |
| `api.timeout` | `30` | 请求超时（秒） |
| `ui.pet_height` | `300` | 桌宠高度（像素），宽度按角色比例计算 |
| `ui.walk_speed` | `48` | 散步速度（像素/秒） |
| `ui.jump_height` | `55` | 跳跃高度（像素） |
| `ui.bubble_seconds` | `4` | 气泡自动消失时间 |
| `ui.menu_seconds` | `5` | 轮盘菜单自动收起时间 |
| `ui.max_bubble_chars` | `12` | 气泡每行字数 |
| `ui.always_on_top` | `true` | 是否置顶 |
| `agent.system_prompt` | 内置人设 | 想换性格/说话风格就改这里 |
| `agent.proactive_minutes` | `30` | 主动说话的间隔，`0` 关闭 |
| `agent.max_tool_rounds` | `5` | 单轮对话最多连续调用工具次数 |
| `agent.history_limit` | `30` | 保留的上下文消息条数 |

环境变量优先级高于 `config.json`：

| 环境变量 | 对应配置 |
| --- | --- |
| `DESKTOP_PET_API_KEY` | `api.api_key` |
| `DESKTOP_PET_BASE_URL` | `api.base_url` |
| `DESKTOP_PET_MODEL` | `api.model` |
| `DESKTOP_PET_CHARACTER` | `character` |
| `DESKTOP_PET_HOME` | 用户数据目录 |

更多说明见 [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)。

## 操作方式

| 操作 | 效果 |
| --- | --- |
| 左键按住拖动 | 移动桌宠 |
| 左键双击 | 打开聊天输入框 |
| 右键单击桌宠 | 打开轮盘菜单（跳跃 / 散步 / 大招 / 聊天 / 待机2 / 扩展 / 退出） |
| `Esc` | 收起菜单和气泡 |
| 轮盘「扩展」 | 管理允许打开的软件白名单 |

聊天框回车发送，`Esc` 取消。输入框和宠物之间会自动跟随位置。

## 自定义角色

角色包是一个文件夹 + 一串按顺序编号的透明 PNG：

```text
assets/characters/my_pet/
├── character.json          # 可选，推荐
├── idle/                   # 待机（必需）
│   ├── idle_00.png
│   └── idle_01.png ...
├── idle2/                  # 第二套待机（可选，缺省复用 idle）
├── idle3/                  # 第三套待机（可选）
├── walk/                   # 散步
├── jump/                   # 跳跃
└── ultra/                  # 大招
```

`character.json` 示例：

```json
{
  "name": "My Pet",
  "author": "your-name",
  "license": "CC0-1.0",
  "frame_width": 256,
  "frame_height": 320,
  "fps": 12,
  "ultra_scale": 1.35,
  "animations": {
    "idle": "idle",
    "idle2": "idle2",
    "idle3": "idle3",
    "walk": "walk",
    "jump": "jump",
    "ultra": "ultra"
  }
}
```

- 推荐 8–12 fps，角色朝右，脚底对齐画布底部。
- 帧按文件名里的数字自然排序，所以 `frame_2.png` 会排在 `frame_10.png` 前面。
- 不想改仓库时，把角色包放进 `%APPDATA%\DesktopPet\characters\my_pet\`，
  再把 `config.json` 的 `character` 改成 `"my_pet"` 即可。

**素材格式、命名、授权检查清单**见 [`docs/ASSETS.md`](docs/ASSETS.md)。

### ⚠️ 关于商业使用

- 仓库自带的 Mochi 占位角色是 CC0，可商用。
- 你自己找的动画/立绘/字体，能不能商用取决于**它的授权**，不是取决于这个项目。
- 「网上免费下载」「别人分享的」「游戏拆包」「动漫角色同人图」通常**不能**商用，
  很多甚至不允许再分发。把它们放进 `%APPDATA%\DesktopPet\characters` 本地使用，
  不要提交到 GitHub。
- 如果角色来自素材商店，请保留购买凭证并确认 license 是否允许随开源项目分发。

## 打包为 exe

```powershell
pip install pyinstaller
pyinstaller packaging/desktop_pet.spec
```

产物在 `dist/DesktopPet/`，双击 `DesktopPet.exe` 即可。打包配置会把
`assets/` 一起带进去；第三方角色包不要放进仓库，可以打包后手动复制到
`dist/DesktopPet/_internal/assets/characters/`，或放到用户目录。

> PyInstaller 产物可能被杀毒软件误报，这是常见现象；如需分发，建议签名或
> 在 Release 里说明。

## 项目结构

```text
desktop-pet/
├── src/desktop_pet/
│   ├── __main__.py        # 入口、DPI、错误提示
│   ├── app.py             # Kivy 主界面、菜单、拖拽、气泡调度
│   ├── pet.py             # 帧动画与移动
│   ├── agent.py           # LLM 对话与 23 个桌面工具
│   ├── characters.py      # 角色包发现与校验
│   ├── config.py          # 配置合并、环境变量、字体解析
│   ├── input_panel.py     # Tk 输入框 / 白名单管理
│   ├── storage.py         # 原子 JSON 存储
│   ├── widgets.py         # 气泡、圆形菜单按钮
│   ├── win32_window.py    # 透明 / 置顶 / 点击穿透
│   └── paths.py           # 仓库目录 vs 用户数据目录
├── assets/
│   ├── characters/mochi/  # 原创占位角色（CC0）
│   ├── fonts/             # 不放字体，只放说明
│   └── icon.ico
├── docs/                  # 预览图、素材/配置/架构/发布文档
├── packaging/             # PyInstaller spec
├── tests/                 # pytest 单元测试
├── tools/                 # 占位素材生成器、仓库自检
├── run.py / run.bat       # 源码运行
└── pyproject.toml
```

更细的模块与线程说明见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

## 开发与测试

```powershell
pip install -r requirements-dev.txt

python -m pytest -q
ruff check .
python tools/check_repo.py          # 检查大文件、疑似密钥、素材目录
python tools/generate_placeholder.py  # 重新生成占位角色与预览图
```

- 代码风格：Ruff（`E/F/W/I/B/UP`），行宽 100。
- 提交前请跑一遍测试和 `check_repo.py`。
- 素材相关的 PR 请附上授权说明，详见 [`docs/ASSETS.md`](docs/ASSETS.md)。
- 贡献流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 安全与隐私

- **API Key 不会进入仓库**：只从 `%APPDATA%\DesktopPet\config.json` 或环境变量读取。
- **工具最小化授权**：打开软件只允许白名单；关机/重启/锁屏必须弹窗确认；
  网址只允许 `http/https`。
- **提示词注入风险**：模型可能被屏幕内容或网页诱导调用工具。请只配置可信的
  模型服务，定期查看 `%APPDATA%\DesktopPet\logs\operations.log`，并保持白名单精简。
- **截图会发送给视觉模型**：使用 `screenshot` 工具时，整屏截图会以 base64 发送到
  你配置的 API；截图同时保存在本地 `screenshots/`。介意的话不要使用该工具。
- 详细安全策略与漏洞上报方式见 [`SECURITY.md`](SECURITY.md)。

## 常见问题

**Q：启动后看不到宠物？**
A：先看终端报错。确认 Python 3.10+、Kivy 2.3.1 安装成功；双屏/高 DPI 下可先把
`ui.pet_height` 调小。透明窗口需要 Windows 10/11 的桌面合成。

**Q：宠物是黑底方块？**
A：说明透明/色键没有生效，常见于远程桌面、部分虚拟机或禁用 DWM 的环境。

**Q：聊天提示没有 API Key？**
A：编辑 `%APPDATA%\DesktopPet\config.json` 的 `api.api_key`，或设置
`DESKTOP_PET_API_KEY` 后重启。

**Q：输入框不出现？**
A：输入框是独立的 Tk 窗口，可能被其他置顶窗口挡住；按 `Esc` 再双击重试。
远程桌面/多屏缩放异常时可先用轮盘里的「聊天」按钮。

**Q：能换成自己的 Live2D / GIF 吗？**
A：当前播放的是 PNG 序列帧，GIF 可以用 ffmpeg 拆帧后放入对应文件夹。
Live2D 需要额外的渲染后端，暂未内置。

**Q：可以商用吗？**
A：代码 MIT 可商用；占位角色 CC0 可商用；**第三方素材请自行确认授权**。

## 许可证

| 内容 | 许可证 |
| --- | --- |
| 源代码 | [MIT](LICENSE) |
| 原创占位角色、图标、预览图 | [CC0-1.0](assets/LICENSE) |
| 第三方角色包 / 字体 | 不包含；遵循各自许可证 |
| Python 依赖 | 见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

如果这个项目帮到你，欢迎 Star ⭐ 或提交 Issue / PR。
