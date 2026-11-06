# 待发布变更

> 每次改动（代码、配置、文档、脚本）完成后，在这里**追加**一条，5 行以内。
> 发版时整本读完，逐条核对是否已写进 `CHANGELOG.md`，然后清空本文件。
> 只写事实，不写推理过程。历史条目不要回头修改。

当前稳定版本：**0.2.0**

---

## 2026-11-06 — 减负与优化

- 打包裁剪用不到的 Qt 库：Qml / QmlModels / Quick / Pdf / VirtualKeyboard / WebSockets / DBus / Network / ANGLE（libEGL + libGLESv2），共 10 个文件。
  - `dist/Timo For Windows` 145.6 MB → **127.6 MB**（231 个文件），安装包 111.9 MB → **104.0 MB**。
  - 保留 `icudt73.dll`（30.5 MB，缺了程序起不来）与 `opengl32sw.dll`（20 MB，给没有显卡驱动的机器兜底）。
  - 裁剪清单固化在 `tools/make-portable.py` 的 `PRUNE` + `prune()`，每次打包自动执行。
- 启动更快：`note_list.setUniformItemSizes(True)` + `QListView.Batched` 布局（批大小 80）；`_reload_notes` 批量加项时 `setUpdatesEnabled(False)` + `blockSignals(True)`。
  - 主窗口构建 1.46s → **1.06s**；全部 ↔ 归档切换 0.01s。
- 回收站**不再默认自动清理**：原来 `trash_days` 默认 30，启动时会静默删掉 30 天前的回收站笔记（实测把示例库的 25 条删了）。现在默认 0（关闭），要开在 `Data/settings.json` 写 `"trash_days": 30`；清空回收站仍走数据菜单的手动操作。
- 验证：26 个测试脚本全绿（test_pdf 需正常平台、offscreen 下字体缺失会退化）；裁剪后 exe 启动、窗口正常，图片插件（qjpeg/qwebp…）与打印插件（windowsprintersupport）都在。


## 2026-11-06 — 搜索命中高亮

- **类型**：功能
- **内容**：搜索后预览里的命中词刷浅灰底（`QTextBrowser` 的 `ExtraSelection`，`#c9c9c9`），多词分别标记；搜索完自动选中第一条命中，右侧立刻能看到高亮
- **文件**：`timodesk/ui/editor.py`、`timodesk/ui/main_window.py`
- **验证**：`test_hl.py` 8/8；截图核对底色可见；19 个脚本 219 项通过
- **影响**：README 里原本就写了「命中词高亮」，这次补上实现

## 2026-11-06 — 图库交互补齐

- **类型**：功能
- **内容**：图片墙支持拖入图片文件、`Ctrl+V` 粘贴剪贴板图片、`Delete` 移除选中（可多选）；提示文案同步
- **文件**：`timodesk/ui/editor.py`（新增 `ImageWall` 类）
- **验证**：`test_wall.py` 12/12
- **影响**：图库从"只能点按钮添加"补齐到和正文一样随手加图

## 2026-11-06 — 单条笔记导出 PDF

- **类型**：功能
- **内容**：笔记右键新增「导出为 PDF…」，用预览同一套 HTML 渲染走 `QPrinter`，A4 页边距 16mm
- **文件**：`timodesk/ui/main_window.py`（`_export_pdf`）
- **验证**：`test_pdf.py` 4/4，产出文件头 `%PDF-`

## 2026-11-06 — 导出为 Markdown 文件夹

- **类型**：功能
- **内容**：数据菜单新增「导出为 Markdown 文件夹…」，按主题建目录、每条笔记一个带 YAML 头的 `.md`，图片统一放 `attachments/` 用相对路径引用；跳过回收站，重名主题/笔记自动加后缀
- **文件**：`timodesk/exporter.py`（`export_markdown_tree`）、`timodesk/ui/main_window.py`（`export_md_tree`）
- **验证**：`test_mdtree.py` 14/14

## 2026-11-06 — 大图查看器支持缩放

- **类型**：体验
- **内容**：双击图片后的查看器加滚轮缩放（0.1×–8×）、双击在「适应窗口 / 100%」间切换，小图不再被放大糊掉；底部按钮改为深色匹配背景
- **文件**：`timodesk/ui/editor.py`（`ImageViewer`）
- **验证**：`test_viewer.py` 10/10

## 2026-11-06 — 回收站自动清理

- **类型**：维护
- **内容**：启动时把回收站里删除超过 30 天的笔记彻底删掉（含正文文件），清了多少条用轻提示告知；`settings.json` 的 `trash_days` 设 0 可关闭
- **文件**：`timodesk/store.py`（`purge_trash`）、`timodesk/app.py`
- **验证**：`test_trash.py` 8/8

## 2026-11-06 — 移除应用锁

- 按用户要求删掉应用锁：`Settings` 不再有 `lock/set_password/check_password`，`dialogs` 去掉 `UnlockDialog`/`LockDialog`，数据菜单去掉「应用锁…」，启动时不再拦密码。
- `settings.json` 里旧的 `lock` 键会在下次保存时自然消失，无需迁移。
- 账号类笔记里的账号/密码字段照旧保留（那是笔记内容）。
- 顺带清理了 `pyflakes` 报出的几处未用导入与一处 f-string 前缀。
- 测试：26 个脚本全绿（原 `test_lock.py` 已删除）。

## 2026-11-06 — 界面向 Pogget 风格靠拢（仍黑白灰）

- 侧栏从「白色卡片」改为浅灰 `#fafafb`，导航项与主题项改用**白胶囊选中**（1px 边 + 10px 圆角），去掉原来的左侧黑色指示条。
- 字号放大一档：中栏标题 15→18px、笔记卡片标题 14→15px、正文 12px、meta 11px、编辑器标题 22→24px。
- 笔记卡片：高度 100px、圆角 14、边框 `#ececee`、阴影更淡；列表内边距调整后卡片间距更均匀。
- 搜索框：高度降一档、加**自绘放大镜图标**（`_search_icon()`，1.6px 线条）。
- 画布色 `#ededf0 → #f1f1f2`，面板边框更淡；`QListWidget#NavList/#TopicList` 背景透明，让侧栏底色透出来。
- 截图重新生成（`docs/screenshot-main.png`、`docs/screenshot-archived.png`），`tools/shot-docs.py` 增加了截图前 `scrollToTop()`。
- 测试：UI 相关 6 个脚本全通过（ui 20、hl 8、window 7、sort 9、view_restore 7、core 13）。
