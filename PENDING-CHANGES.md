# 待发布变更

> 每次改动（代码、配置、文档、脚本）完成后，在这里**追加**一条，5 行以内。
> 发版时整本读完，逐条核对是否已写进 `CHANGELOG.md`，然后清空本文件。
> 只写事实，不写推理过程。历史条目不要回头修改。

当前稳定版本：**0.2.0**

---

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
