# 发布到 GitHub 检查清单

这份文档按顺序执行，可以把当前目录安全地变成一个公开仓库。

## 0. 先吊销旧 Key（最重要）

旧版 `agent.py` 里曾经**明文写死**了一个智谱 API Key。只要这个文件被截图、
发给别人、上传到任何地方，就应该视为已泄露。

1. 登录 <https://open.bigmodel.cn/> → API Keys。
2. **删除/吊销**旧的 Key。
3. 新建一个 Key，只放在 `%APPDATA%\DesktopPet\config.json` 或环境变量里。
4. 不要试图用 `git commit --amend` 掩盖旧历史——直接建一个全新的仓库最干净。

> 本仓库的代码和历史里没有任何 Key；`.gitignore` 也忽略了 `config.json`。
> 但如果你把**旧目录**直接 `git init` 后提交，旧 `agent.py` 仍然可能被带进去。
> 所以请使用这次整理出的新目录。

## 1. 确认工作区干净

```powershell
cd D:\python---study\desktop-pet

# 不应出现 config.json / memory.json / logs / 截图 / 第三方动画
Get-ChildItem -Recurse -File | Where-Object {
    $_.Name -in @("config.json","memory.json","todos.json","stats.json",
                  "whitelist.json","operations.log","screen_shot.png")
}
```

如果上面列出了文件，删掉或移到 `%APPDATA%\DesktopPet`。

## 2. 确认素材版权

```powershell
Get-ChildItem assets\characters
```

应该只看到：

```text
mochi
README.md
```

如果看到 `daiji`、`dazhao`、`khqn`、`tiaoyue`、`ziti` 等目录，**不要提交**。
它们属于第三方素材，不能随开源项目分发，更不能商用。详见
[`ASSETS.md`](ASSETS.md)。

## 3. 跑自动检查

```powershell
python -m compileall -q src tools tests
python -m pytest -q
ruff check .
python tools/check_repo.py
```

`check_repo.py` 会检查：

- 单个文件是否超过 5 MB（GitHub 对 >100 MB 的文件直接拒绝）；
- 是否出现疑似 API Key；
- 是否混入第三方素材目录；
- 关键文件是否齐全。

## 4. 初始化一个全新仓库

```powershell
git init -b main
git add .
git status
```

`git status` 里应该**没有**：

- `config.json`、`.env`
- `memory.json`、`todos.json`、`stats.json`、`whitelist.json`
- `logs/`、`screenshots/`、`screen_shot.png`
- `assets/characters/` 下除 `mochi` 和 `README.md` 之外的内容
- `__pycache__/`、`.venv/`、`dist/`、`build/`

确认后提交：

```powershell
git commit -m "feat: initial public release"
```

## 5. 在 GitHub 创建仓库

用网页或 GitHub CLI：

```powershell
gh repo create desktop-pet --public --source=. --remote=origin --push
```

没有 `gh` 的话：

1. GitHub → New repository → 名字 `desktop-pet`；
2. **不要**勾选 “Add a README / .gitignore / license”（本地已有）；
3. 按页面提示：

```powershell
git remote add origin https://github.com/<your-name>/desktop-pet.git
git push -u origin main
```

## 6. 仓库设置建议

- **Description**：`A desktop pet template: turn an image or a sentence into an animated desktop pet.`
- **Topics**：`desktop-pet`, `desktop-pet-template`, `character-generator`, `kivy`, `python`, `windows`, `llm`, `ai-agent`, `desktop-companion`
- **Website**：可以先留空。
- **Features**：Issues 打开；Discussions 可选。
- **Security**：开启 Dependabot alerts 和 private vulnerability reporting。

## 7. 发布 Release（可选）

```powershell
pip install pyinstaller
pyinstaller packaging/desktop_pet.spec
Compress-Archive -Path dist\DesktopPet\* -DestinationPath DesktopPet-v0.3.0-win64.zip
```

在 GitHub → Releases → Draft a new release：

- Tag：`v0.3.0`
- 附上 zip；
- Release notes 里写明：**不含第三方角色素材；自带占位角色为 CC0**；
- 提醒用户首次运行需要在 `%APPDATA%\DesktopPet\config.json` 填 API Key。

## 8. 发布后自检

- 用无痕窗口打开仓库，确认 README 图片能显示；
- 点开 `LICENSE`、`assets/LICENSE`，确认 GitHub 能识别；
- 搜一下仓库里有没有 `api_key`、`Bearer`、`sk-`；
- 确认 `docs/preview.png` 不是自己的桌面截图（本仓库的预览图是脚本生成的）。

## 9. 如果误传了敏感内容

1. 立刻吊销 Key / 删除素材；
2. 用 `git filter-repo` 或 BFG 清理历史；
3. 强制推送后，联系 GitHub Support 清理缓存；
4. 公开仓库的 fork 无法收回，所以**预防比补救重要**。

