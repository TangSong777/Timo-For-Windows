# 待发布变更

> 每次改动（代码、配置、文档、脚本）完成后，在这里**追加**一条，5 行以内。
> 发版时整本读完，逐条核对是否已写进 `CHANGELOG.md`，然后清空本文件。
> 只写事实，不写推理过程。历史条目不要回头修改。

当前稳定版本：**0.3.0**

---

## 2026-11-06 — 深色模式

- `timodesk/ui/theme.py` 拆成 `LIGHT` / `DARK` 两套色板，`C` 改为原地更新的全局字典；`set_mode()` / `current_mode()` / `resolve()`（system 读 Windows `AppsUseLightTheme`）。
- QSS 全部改为从 `C` 取值，硬编码 hex 清零；`render._css()` 同步参数化。
- 编辑器内联样式改成 `#NoteDesc` / `#DateBig` / `#DateSub` / `#EmptyIcon` / `#EmptyHint` / `#WordLabel` / `#TimeLabel` / `#FmtSep` / `#GalleryHint` / `#AccountTip` / `#TotalLabel` 等 QSS 规则，切换皮肤即时生效。
- 标题栏抽出 `refresh_style()`；主窗口「⋯ → 外观」提供浅色 / 深色 / 跟随系统（`QActionGroup` 互斥），写 `settings.json` 的 `theme_mode`，启动时应用。
- 欢迎页等对话框跟随主题；按钮去掉焦点虚线框。
- 测试：core 13、types 32、ui 20、window 7、sort 9、view_restore 7、hl 8 全绿。
