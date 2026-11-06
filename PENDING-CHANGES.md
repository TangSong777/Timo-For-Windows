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

## 2026-11-06 — 深色细节修正

- 图库缩略图外框底色由硬编码 `#f3f3f5` 改为 `C['input_bg']`，深色下不再是白块。
- `#NoteDesc` 边框改用 `card_border_strong`，深色下说明框边界可见。
- `#WordLabel` / `#TimeLabel` / `#GalleryHint` / `#AccountTip` 由 faint 提为 muted，深色下底部字数与提示可读。

## 2026-11-06 — 深色模式的对话框与细节修正
- 「关于」框统计条、备份列表（背景与选中）、搜索高亮改为跟随主题；新增 `C['hl_bg']`（浅 #d0d0d0 / 深 #4a4a52），预览高亮与主题一致。
- `test_hl.py` 的底色断言改为读取 `C['hl_bg']`，不再写死。

## 2026-11-06 — 多选拖拽与健壮性
- 笔记列表支持**多选后一起拖到主题**：`NoteList.startDrag` 把选中 id 以 JSON 写入 MIME；`TopicList` 信号改为 `notesDropped(list, topic_id)`；`Library.move_notes(ids, topic_id)` 一次落盘，拖完 toast 提示「已移动 N 条」。
- 搜索框按 `Esc` 清空搜索并回到列表。
- `Library.save()` 的 `os.replace` 加 6 次重试（Windows 杀毒/索引短暂占用时不再抛 `PermissionError`）。
- `test_drag.py` 改为每次重建测试库（幂等），并覆盖批量移动；全量 26 个脚本连续两轮全绿。
