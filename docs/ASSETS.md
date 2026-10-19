# 角色素材指南（格式、替换与版权）

本项目的代码和素材是分开的：代码用 MIT，内置占位角色用 CC0，但**你后来加进去的
角色包不自动获得任何授权**。这份文档说明格式怎么放、授权怎么判断。

## 1. 仓库里有什么

| 路径 | 内容 | 授权 |
| --- | --- | --- |
| `assets/characters/mochi/` | `tools/generate_placeholder.py` 生成的原创小猫，60 帧 | CC0-1.0 |
| `assets/icon.png` / `icon.ico` | 由同一脚本生成 | CC0-1.0 |
| `assets/ui/popup_bg.png` | 生成向导的粉白弹窗背景 | CC0-1.0 |
| `docs/preview.png` / `preview.gif` | 由同一脚本生成 | CC0-1.0 |
| `docs/creator-preview.png` / `.gif` | 生成器示例角色「奶油」 | CC0-1.0 |
| `assets/fonts/` | 只有说明文件，不含字体 | — |

早期本地版本使用过 `daiji/`、`dazhao/`、`khqn/`、`tiaoyue/` 动画和
`ChillHuoFangSong` 字体。它们**没有**进入这个仓库，原因见第 5 节。

## 2. 目录格式

```text
<角色名>/
├── character.json          # 可选；没有也能跑，但建议写
├── idle/                   # 必需：待机
├── idle2/                  # 可选：第二套待机
├── idle3/                  # 可选：第三套待机
├── walk/                   # 可选：散步
├── jump/                   # 可选：跳跃
└── ultra/                  # 可选：大招
```

缺省的动画会自动回退到 `idle`，所以最小可用角色只需要一个 `idle/` 文件夹。

### 兼容旧文件夹名

为了方便迁移旧项目，加载器也接受这些别名（不区分大小写）：

| 动画 | 可用文件夹名 |
| --- | --- |
| idle | `idle`, `daiji`, `stand`, `wait` |
| idle2 | `idle2`, `idle_2`, `daiji2` |
| idle3 | `idle3`, `idle_3`, `daiji3` |
| walk | `walk`, `khqn`, `run`, `move` |
| jump | `jump`, `tiaoyue`, `hop` |
| ultra | `ultra`, `dazhao`, `skill`, `special` |

## 3. 帧文件要求

- 格式：PNG（推荐 RGBA 透明背景）；也支持 `.jpg/.jpeg/.webp`，但没有透明通道。
- 同一动画内尺寸一致；不同动画之间可以不同，程序会按 `frame_width/height` 等比缩放。
- 按文件名中的数字**自然排序**：`frame_1.png` → `frame_2.png` → `frame_10.png`。
- 推荐帧率 8–12 fps；帧数 6–20 张即可循环。
- 角色默认朝右；脚底尽量对齐画布底部，否则拖拽和气泡定位会显得偏。
- 透明区域不要裁得太紧，给耳朵/尾巴/特效留一点边距。

### 从 GIF / 视频拆帧

```powershell
# GIF -> PNG 序列
ffmpeg -i walk.gif -vsync 0 walk_%03d.png

# 视频 -> 12fps PNG 序列
ffmpeg -i idle.mp4 -vf fps=12 idle_%03d.png
```

拆完把文件放进对应子目录即可。

## 4. character.json

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

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `name` | 文件夹名 | 显示名称 |
| `author` | `unknown` | 作者，便于署名 |
| `license` | `unknown` | 素材授权，例如 `CC0-1.0`、`CC-BY-4.0`、`LicenseRef-Commercial` |
| `frame_width/height` | `256/320` | 画布尺寸，用于计算宽高比 |
| `fps` | `12` | 播放帧率，1–60 |
| `ultra_scale` | `1.35` | 大招时放大倍数，1–3 |
| `animations` | 约定目录 | 动画名 → 文件夹名（或文件夹名数组） |

如果 `animations` 里写了自定义文件夹，程序会优先用它；找不到再按约定名和别名查找。

## 5. 授权检查清单（重要）

在把任何角色包提交到 GitHub 之前，逐条确认：

1. **这是谁的作品？** 能找到作者和原始发布页吗？
2. **许可证写的是什么？** 是 CC0 / CC-BY / MIT / 商业素材 license，还是
   “仅供个人使用 / 禁止商用 / 禁止再分发”？
3. **“免费下载”不等于“可以再分发”。** 很多素材站只授予你个人使用权，
   不允许把源文件放进公开仓库。
4. **角色本身是否受版权保护？** 动漫/游戏角色的同人图、拆包立绘，
   即使画师允许转载，角色版权方仍可能限制商用。
5. **字体是独立的。** 字体通常有单独的 license，不能因为“随项目一起”就默认可以分发。
6. **保留证据。** 保存购买记录、license 截图或作者授权邮件；在角色目录放一个
   `LICENSE.txt` / `NOTICE.txt` 说明来源。

### 推荐做法

| 场景 | 建议 |
| --- | --- |
| 自己画的 / 自己买的、license 允许分发 | 可以提交，附 `LICENSE.txt` 和署名 |
| 只有个人使用权的素材 | **不要提交**；放 `%APPDATA%\DesktopPet\characters` 本地用 |
| 动漫角色同人 / 游戏拆包 | **不要提交**，也不建议商用 |
| 不确定 | 当作“不能提交”处理 |

### 角色目录里的授权文件示例

```text
my_pet/
├── LICENSE.txt
├── character.json
└── idle/...
```

`LICENSE.txt`：

```text
Character: My Pet
Author: your-name
Source: https://example.com/my-pet
License: CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)
Changes: resized to 256x320, renamed frames
```

## 6. 用户本地角色（推荐）

把角色包放到：

```text
%APPDATA%\DesktopPet\characters\<角色名>\
```

然后在 `%APPDATA%\DesktopPet\config.json` 里改：

```json
{ "character": "<角色名>" }
```

这样：

- 不会误提交到 GitHub；
- 换电脑时只需复制用户目录；
- 仓库始终只保留可公开的 CC0 占位角色。

### 生成器产出的角色包

`python create_pet.py` 或应用内「创建」会生成：

```text
%APPDATA%\DesktopPet\characters\<名字>\
├── character.json
├── SOURCE.txt      # 来源：prompt / 图片路径 / AI 模型
├── LICENSE.txt     # 默认 unverified
├── preview.png
└── idle/ walk/ jump/ ultra/ ...
```

- **离线程序化绘制**：图形由本项目脚本生成，可按 CC0 使用；但如果你描述的是某个受版权保护的角色，角色本身的版权仍可能限制商用。
- **用户图片**：版权归原权利人；`SOURCE.txt` 会记录图片路径，`LICENSE.txt` 默认 `unverified`。
- **AI 出图**：受图片服务商的条款约束，商用前确认服务商是否授予商用权。
- 发布/出售前，把 `LICENSE.txt` 改成真实授权，并保留来源证据。

## 7. 字体

- 程序优先使用 `config.json` 的 `font` 路径；
- 其次找 `assets/fonts/` 下的第一个字体；
- 最后回退到 Windows 自带的微软雅黑。

如果要随仓库分发字体，请确认字体 license 允许再分发（很多免费字体只允许个人使用）。
更稳妥的做法是让用户自己指定系统字体。

## 8. 发现侵权内容怎么办

如果你是权利人，认为本仓库包含你的素材，请通过仓库 Issue 或
[`SECURITY.md`](../SECURITY.md) 中的联系方式提供：

- 作品名称与原始链接；
- 你拥有版权的说明；
- 仓库中具体文件路径。

我们会尽快删除相关内容。

