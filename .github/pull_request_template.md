## 改了什么

<!-- 简要说明这个 PR 的目的和主要改动。 -->

## 为什么

<!-- 关联 Issue：Closes #123 -->

## 怎么验证

- [ ] `python -m compileall -q src tools tests`
- [ ] `python -m pytest -q`
- [ ] `ruff check .`
- [ ] `python tools/check_repo.py`
- [ ] 本地启动 `python run.py` 手动验证（涉及 UI 时）

## 截图 / 录屏

<!-- 涉及界面变化时请附上。 -->

## 素材与安全

- [ ] 没有提交第三方角色 / 字体 / 音效，或已附授权说明
- [ ] 没有提交 API Key、日志、个人截图
- [ ] 新增工具已同步 `TOOLS`、`_tool_map` 和测试
