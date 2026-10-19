# 贡献指南

感谢你愿意改进这个桌宠！请先花两分钟读完下面几条。

## 开发环境

```powershell
git clone https://github.com/<your-name>/desktop-pet.git
cd desktop-pet
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

python run.py
```

## 提交前

```powershell
python -m compileall -q src tools tests
python -m pytest -q
ruff check .
python tools/check_repo.py
```

四条都通过再提 PR。

## 代码风格

- Python 3.10+，使用类型标注。
- 行宽 100，Ruff 规则 `E/F/W/I/B/UP`。
- Kivy 控件只在主线程操作；耗时任务放 worker 线程，通过 `queue.Queue` 回传。
- 新增工具时同步更新 `TOOLS`、`Agent._tool_map` 和测试。
- 不要引入新的重量级依赖；确需引入时先开 Issue 讨论。

## 素材政策（重要）

- **不要提交**你没有版权或授权不允许再分发的角色动画、立绘、字体、音效。
- 仓库只接受：
  - 你自己创作并同意以 CC0 / CC-BY 等许可释出的素材；
  - 明确允许随开源项目分发的商业素材（请附 license 和购买凭证说明）。
- 新增角色包请放在 `assets/characters/<name>/`，并附 `LICENSE.txt` 与来源。
- 不确定时，放到 `%APPDATA%\DesktopPet\characters` 本地测试即可，不要进 PR。

## PR 流程

1. Fork 并新建分支：`feat/xxx`、`fix/xxx`、`docs/xxx`。
2. 小而聚焦的提交；提交信息用祈使句，例如 `fix: keep bubble inside screen`。
3. 描述里写清楚：改了什么、为什么、怎么验证的。
4. 涉及 UI 的改动请附截图或 GIF。
5. 涉及素材的改动请附授权说明。

## Issue

- Bug 请附：Windows 版本、Python 版本、Kivy 版本、复现步骤、终端报错。
- 功能建议请说明使用场景，而不是只写“想要 xxx”。
- 不要贴 API Key、完整日志或含个人信息的截图。
