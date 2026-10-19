# 角色生成器（Creator）

把一张图或一句话变成桌宠角色包。生成后的角色包与运行时完全解耦，放在
`%APPDATA%\DesktopPet\characters`，不会进入 Git 仓库。

## 三种输入

| 输入 | 命令 | 说明 |
| --- | --- | --- |
| 文字描述 | `--prompt "白色小猫，戴红围巾"` | 默认离线绘制，可选 AI |
| 单张图片 | `--image .\cat.png` | 透明 PNG 最佳；JPG 会尝试去纯色底 |
| 已有帧 | `--frames D:\old\pet --link` | 复用旧动画；`--link` 只写路径，不复制 |

## 快速命令

```powershell
# 文字 → 角色（默认离线）
python create_pet.py --name 雪球 --prompt "白色小猫，戴红围巾，蓝眼睛"

# 图片 → 角色
python create_pet.py --name 小蓝 --image .\cat.png

# 旧动画 → 角色（只引用，不复制 168MB）
python create_pet.py --name 旧角色 --frames D:\python---study\桌面宠物图片 --link

# 查看 / 切换 / 打开预览
python create_pet.py --list
python create_pet.py --use 雪球
python create_pet.py --preview 雪球
```

生成后默认会把 `config.json` 的 `character` 切到新角色；加 `--no-use` 可只生成不切换。

## 文字支持范围

这是**规则解析 + 程序化绘制**，不是任意文生图，所以支持有限的组合：

| 类别 | 支持 |
| --- | --- |
| 物种 | 猫、狗、兔、狐、熊、鸟、史莱姆 |
| 颜色 | 白、黑、灰、银、橘、黄、金、粉、蓝、绿、紫、棕、咖啡、红、米色、奶油 |
| 配饰 | 围巾、蝴蝶结、眼镜、帽子、耳机、小花 |
| 花纹 | 花纹/斑点、条纹、星星、爱心 |
| 眼睛 | “蓝眼睛”“green eyes” |
| 名字 | “叫雪球”“named Midnight” |

示例：

```text
一只白色小猫，戴红围巾，蓝眼睛，叫雪球
橘色的小狗，戴蓝色蝴蝶结
a black cat with green eyes and a red scarf named Midnight
灰色兔子，戴圆眼镜，星星花纹
```

不支持的特征（翅膀、机械、复杂服装、特定动漫角色）需要走 AI 出图或直接提供图片。

## 图片输入

### 应用内上传

向导里点「上传图片」会打开 **Windows 原生文件选择框**，只过滤
PNG / JPG / JPEG / WebP。选中后会立即在弹窗里预览，并自动用文件名填角色名。
点「生成并切换」后才会去背景、生成动作和角色包。

> 图片模式会**直接使用你选的图**作为角色，不改变画风。
> 如果你想把真人照片转成 Q 版/动漫角色，需要额外的“图生图”模型；
> 当前版本不保留照片人物身份。可以先用 AI/画师生成一张卡通立绘，再上传。

### 推荐格式

- PNG，透明背景，角色完整、正面或微侧身。
- 建议 512×512 以上，主体占画面 70% 左右。
- 脚底尽量在同一水平线；生成时会自动脚底对齐。

### 去背景

- 有透明通道：直接按 alpha 裁切。
- JPG / 纯色背景：从四角做泛洪填充，只删除**与边缘连通**的背景，尽量保留角色内部的白色区域。
- 不均匀背景、复杂阴影、发丝边缘：建议先用抠图工具处理成透明 PNG。
- `--tolerance` 可调（默认 32，范围 0–120）。白色猫配白底时，容差过高可能吃掉身体。

### 动作生成

只有一张静态图时，不会重绘角色，而是对原图做保持比例的变换：

- `idle`：上下浮动 + 呼吸挤压 + 眨眼（仅离线绘制的角色有眨眼）
- `walk`：弹跳 + 左右倾斜 + 脚步错位
- `jump`：压扁 → 拉伸 → 落地
- `ultra`：放大 + 粉色光晕 + 星星
- 阴影随高度变化

所有帧输出为 256×320 透明 PNG，脚底对齐 `y=300`。

## AI 模式（可选）

默认关闭。加上：

```powershell
python create_pet.py --name 雪球 --prompt "..." --ai-spec --ai-image
```

- `--ai-spec`：让对话模型把描述解析成角色 JSON（失败回退规则解析）。
- `--ai-image`：调用 OpenAI 兼容的 `/images/generations` 生成角色图，再做去背和动作生成（失败回退出离线绘制）。
- 配置项：`api.image_model`，默认 `cogview-3-flash`。
- 需要 `api.api_key` 或 `DESKTOP_PET_API_KEY`。

不同服务商对 images 接口的支持不同；失败不会中断，会打印回退提示。

## 应用内向导

运行桌宠 → 右键 → **创建**：

1. 填名字（可留空）。
2. 选「用文字描述」或「用一张图片」。
3. 可选「AI 增强」。
4. 点「生成并切换」，几秒后桌宠立即换角色。
5. 预览图显示在弹窗里；点「完成」关闭。

生成在后台线程执行，不会卡住动画。

## 输出结构

```text
%APPDATA%\DesktopPet\characters\<名字>\
├── character.json       # 元数据，运行时读取
├── SOURCE.txt           # 来源、prompt、图片路径、版权提醒
├── LICENSE.txt          # 默认 unverified，需自行确认
├── preview.png          # 900×560 预览卡
├── preview.gif          # 待机循环
├── idle/
├── idle2/
├── idle3/
├── walk/
├── jump/
└── ultra/
```

`character.json` 关键字段：

```json
{
  "name": "雪球",
  "species": "cat",
  "fps": 12,
  "ultra_scale": 1.35,
  "frame_width": 256,
  "frame_height": 320,
  "animations": {
    "idle": "idle",
    "walk": "walk",
    "jump": "jump",
    "ultra": "ultra"
  }
}
```

## 旧动画迁移

旧项目的目录通常是：

```text
daiji/daiji1, daiji2, daiji3
khqn/*.gif
tiaoyue/*.png
dazhao/*.png
```

`--frames ... --link` 会自动识别：

| 新名称 | 兼容旧目录 |
| --- | --- |
| idle | `idle`, `daiji/daiji1`, `daiji1`, `stand` |
| idle2 | `idle2`, `daiji/daiji2`, `daiji2` |
| idle3 | `idle3`, `daiji/daiji3`, `daiji3` |
| walk | `walk`, `khqn` |
| jump | `jump`, `tiaoyue` |
| ultra | `ultra`, `dazhao` |

`--link` 只写绝对路径，不复制文件；移动原目录后链接会失效。要生成独立副本，去掉 `--link`。

> 第三方动画只适合本地使用。不要把 `--frames` 生成的链接包或原素材提交到 GitHub。

## 代码结构

| 模块 | 职责 |
| --- | --- |
| `creator/spec.py` | 角色规格、中英文解析 |
| `creator/draw.py` | 离线程序化绘制 7 种物种 + 配饰/花纹 |
| `creator/image_pack.py` | 图片去背、裁切、动作帧 |
| `creator/pack.py` | 写角色包、预览、`SOURCE.txt` |
| `creator/pipeline.py` | 图片/文字/旧帧三种流程 |
| `creator/ai.py` | 可选的 LLM 解析与图片生成 |
| `creator/cli.py` | 命令行 |
| `creator/native_dialog.py` | Windows 原生选图框 |
| `creator/wizard.py` | 应用内 Kivy 向导 |

## 扩展

新增物种：

1. `spec.py` 的 `SPECIES_WORDS` / `SPECIES_LABELS` 加词。
2. `draw.py` 的 `_ears` / `_tail` / `_head` / `_feet` 加分支。
3. `tests/test_creator.py` 加一个解析与帧数测试。

新增配饰：

1. `spec.py` 的 `ACCESSORY_WORDS` / `ALLOWED_ACCESSORIES` 加词。
2. `draw.py` 的 `_accessory` 加绘制分支。

新增花纹同理。

## 限制

- 离线绘制是风格化模板，不会按描述画出任意细节。
- 单张图的 walk/jump 是变换动画，不是骨骼动画；想要真跑步需要多帧素材。
- 去背景对复杂背景效果有限；建议透明 PNG。
- AI 出图依赖服务商，可能失败、收费或产生不符合预期的图；失败会自动回退离线。

