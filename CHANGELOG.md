# Changelog

所有值得注意的改动都记录在这里。格式参考
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循
[Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [0.3.0] - 2026-10-19

桌宠生成模板。

### Added

- `desktop_pet.creator` 包：文字 / 图片 / 已有帧三种输入。
- 中英文角色描述解析：物种、颜色、配饰、花纹、眼睛、名字。
- 离线程序化绘制：猫、狗、兔、狐、熊、鸟、史莱姆；围巾、蝴蝶结、眼镜、帽子、耳机、小花；斑点、条纹、星星、爱心。
- 图片转动作：去背景、裁切、脚底对齐、idle/walk/jump/ultra 变换动画。
- 角色包写入：`character.json`、六套帧、`preview.png`、`preview.gif`、`SOURCE.txt`、`LICENSE.txt`。
- 命令行：`--prompt`、`--image`、`--frames --link`、`--ai-spec`、`--ai-image`、`--list`、`--use`、`--preview`。
- 应用内「创建」向导：文字/图片、AI 增强、预览、生成后热切换。
- 旧动画兼容：`daiji/daiji1`、`khqn`、`tiaoyue`、`dazhao` 自动映射；`--link` 不复制大文件。
- 可选 AI：LLM 解析描述、OpenAI 兼容 `/images/generations` 出图，失败自动回退。
- 粉白弹窗背景 `assets/ui/popup_bg.png`，向导与现有气泡/轮盘风格一致。

### Changed

- README 重构为「桌宠生成模板」。
- 配置新增 `api.image_model`。
- 角色加载支持 `.gif` 单帧序列。

## [0.2.0] - 2026-10-19

首个可公开发布的整理版本。

### Added

- 原创占位角色 Mochi（60 帧，CC0），由 `tools/generate_placeholder.py` 生成。
- `character.json` 角色包格式，支持 idle / idle2 / idle3 / walk / jump / ultra。
- 角色包搜索路径：用户目录优先，仓库 `assets/characters` 兜底。
- 配置系统：默认值 + `config.json` + 环境变量，API Key 不再硬编码。
- 用户数据目录 `%APPDATA%\DesktopPet`：配置、记忆、待办、统计、日志、截图。
- 原子 JSON 存储，损坏文件自动回退。
- 单元测试（配置、角色加载、工具、文本换行、路径）。
- GitHub CI、Issue/PR 模板、`tools/check_repo.py` 发布前自检。
- 完整文档：README、素材指南、配置、架构、发布清单、安全策略。

### Changed

- 主程序拆分为 `app / pet / agent / characters / config / input_panel / widgets`。
- 动画帧按文件名自然排序，修复 `frame_10` 排在 `frame_2` 前面的问题。
- 大招尺寸改为按 `ultra_scale` 等比缩放，不再使用 4090×1000 的硬编码。
- 气泡定位与拖拽同步，修复坐标重复累加导致的偏移。
- 轮盘「聊天」按钮真正打开输入框。
- 默认人设改为原创角色「小满」，不再引用受版权保护的动漫角色。
- 输入框/白名单管理迁移到独立 Tk 线程，减少 Kivy 卡顿。

### Removed

- 硬编码的 API Key。
- 第三方动画目录与字体（未获得再分发/商用授权）。
- 重复定义的 `_load_stats`、`_screenshot`、`_list_dir` 等方法。
- 个人日志、截图与测试数据。

### Fixed

- `shutdown` 的 `rundll32` / `shutdown` 调用改为参数列表，避免路径解析失败。
- 工具调用参数 JSON 解析失败时不再崩溃。
- 聊天历史裁剪不再产生孤立的 `tool` 消息。
- 透明窗口在拖拽、缩放大招后自动限制在屏幕内。

## [0.1.0] - 2026-09-20

早期本地原型：Kivy 透明窗口、帧动画、轮盘菜单、智谱对话与桌面工具。
未公开发布。
