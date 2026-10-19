# 配置说明

## 文件位置

```text
%APPDATA%\DesktopPet\
├── config.json          # 主配置
├── memory.json          # 长期记忆（remember 工具）
├── todos.json           # 待办
├── stats.json           # 等级 / 经验 / 互动次数
├── whitelist.json       # 自定义可打开软件
├── logs/operations.log  # 工具调用日志
├── screenshots/         # screenshot 工具保存的截图
└── characters/          # 用户本地角色包（不会被提交）
```

第一次运行会自动创建 `config.json`（`api_key` 为空）。删除它可以恢复默认配置，
但不会删除记忆、待办等数据。

### 便携模式

设置 `DESKTOP_PET_HOME` 后，以上所有文件都会放到指定目录：

```powershell
$env:DESKTOP_PET_HOME = "D:\DesktopPetData"
python run.py
```

适合放在 U 盘里，或不想污染 `%APPDATA%` 的场景。

## 优先级

```text
内置默认值  <  config.json  <  环境变量
```

环境变量适合 CI、临时切换模型，以及不想把 Key 写进文件的情况。

## 完整字段

```json
{
  "character": "mochi",
  "font": "",
  "api": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "glm-4-flash",
    "vision_model": "glm-4v-flash",
    "image_model": "cogview-3-flash",
    "api_key": "",
    "timeout": 30
  },
  "ui": {
    "pet_height": 300,
    "bubble_seconds": 4,
    "menu_seconds": 5,
    "walk_speed": 48,
    "jump_height": 55,
    "always_on_top": true,
    "max_bubble_chars": 12
  },
  "agent": {
    "system_prompt": "你是住在用户电脑里的桌面小精灵「小满」……",
    "proactive_minutes": 30,
    "max_tool_rounds": 5,
    "history_limit": 30
  }
}
```

### `character`

角色包名称。查找顺序：

1. `%APPDATA%\DesktopPet\characters\<名字>\`
2. `assets/characters/<名字>/`
3. 找不到时回退到 `mochi`

### `font`

- 绝对路径：直接使用。
- 相对路径：相对仓库根目录。
- 留空：先找 `assets/fonts/` 下第一个 `.ttf/.ttc/.otf`，再找 Windows 的
  微软雅黑 / 黑体 / 宋体。

### `api`

任何 OpenAI 兼容的 `/chat/completions` 服务都可以。要求：

- 支持 `tools` / `tool_choice`（function calling）；
- 返回结构包含 `choices[0].message`；
- 截图理解需要支持 `image_url`（base64 data URL）。

常见组合：

| 服务 | base_url | model 示例 |
| --- | --- | --- |
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 本地 Ollama | `http://127.0.0.1:11434/v1` | `qwen2.5:7b` |

> 本地模型不一定支持 function calling；不支持时模型只会聊天，不会调用桌面工具。

### `api.image_model`

只在角色生成器的 AI 出图模式使用（`--ai-image` 或向导里的「AI 增强」）。
默认 `cogview-3-flash`，需要服务商支持 OpenAI 兼容的
`POST /images/generations`。失败会自动回退离线绘制，不影响使用。

## 角色生成器

```powershell
python create_pet.py --name 雪球 --prompt "白色小猫，戴红围巾"
python create_pet.py --name 小蓝 --image .\cat.png
python create_pet.py --name 旧角色 --frames D:\old\pet --link
python create_pet.py --list
```

生成的配置写入 `%APPDATA%\DesktopPet\characters\<名字>\character.json`，并自动更新
本文件的 `character` 字段。完整参数见 [`CREATOR.md`](CREATOR.md)。

### `ui`

- `pet_height`：120–800。
- `walk_speed`：1–400 px/s。
- `jump_height`：0–300 px。
- `bubble_seconds`：1–30 秒。
- `menu_seconds`：1–30 秒。
- `max_bubble_chars`：每行字数，影响气泡高度。

### `agent`

- `system_prompt`：人设和工具使用要求。默认人设是原创角色「小满」，
  不含任何受版权保护的动漫角色设定。
- `proactive_minutes`：主动说话间隔；`0` 表示关闭。
- `max_tool_rounds`：一轮对话里最多连续调用几次工具，防止死循环。
- `history_limit`：上下文保留条数；越大越贵，也越容易“记得”之前的话。

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `DESKTOP_PET_HOME` | 用户数据目录 |
| `DESKTOP_PET_API_KEY` | API Key，优先级高于 config.json |
| `DESKTOP_PET_BASE_URL` | 接口根地址 |
| `DESKTOP_PET_MODEL` | 对话模型 |
| `DESKTOP_PET_CHARACTER` | 角色包名称 |

PowerShell 临时设置：

```powershell
$env:DESKTOP_PET_API_KEY = "..."
$env:DESKTOP_PET_MODEL = "glm-4-air"
python run.py
```

永久设置（当前用户）：

```powershell
[Environment]::SetEnvironmentVariable("DESKTOP_PET_API_KEY", "...", "User")
```

## 安全建议

- 不要 `git add config.json`；`.gitignore` 已经忽略它。
- 不要把 Key 写进 README、Issue、截图或日志。
- 如果 Key 曾经出现在公开仓库/聊天记录里，立刻去服务商后台**吊销并重建**。
- 日志可能包含你让宠物打开的路径和搜索词，分享日志前先检查。

