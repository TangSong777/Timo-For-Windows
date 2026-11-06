# 待发布变更

> 每次改动（代码、配置、文档、脚本）完成后，在这里**追加**一条，5 行以内。
> 发版时整本读完，逐条核对是否已写进 `CHANGELOG.md`，然后清空本文件。
> 只写事实，不写推理过程。历史条目不要回头修改。

当前稳定版本：**0.1.0**

---

## 2026-11-06 — 新增发布打包脚本

- **类型**：流程
- **内容**：`tools/make-release.py` 把 `dist/Timo笔记` 打成发布 zip 并生成 `SHA256SUMS.txt`
- **文件**：`tools/make-release.py`、`.gitignore`
- **验证**：重新打包哈希与线上 0.1.0 资产一致（`92a1613…`）
- **影响**：发版时改用该脚本，不再手写压缩

## 2026-11-06 — 自绘无边框窗口

- **类型**：界面
- **内容**：移除 Windows 原生标题栏，改为自绘标题栏（Timo 品牌 + 最小化 / 最大化 / 关闭）、11px 圆角、1px 描边、边缘八向拖拽缩放、双击标题栏最大化；侧栏顶部重复的品牌行删除，交给标题栏
- **文件**：`timodesk/ui/title_bar.py`（新增）、`timodesk/ui/main_window.py`、`timodesk/ui/theme.py`
- **验证**：`test_core.py` 13/13；圆角遮罩（角落不在 mask、6px 在内）、八向命中码、最大化铺满可用区且还原后恢复遮罩，均截图核对
- **影响**：主窗口外观全部自绘；数据与笔记功能未改动

## 2026-11-06 — 自绘对话框

- **类型**：界面
- **内容**：欢迎页、消息框、确认框、导入进度框全部改为无边框自绘（统一标题条 + 圆角 + 描边），不再调用 `QMessageBox` / `QProgressDialog`
- **文件**：`timodesk/ui/dialogs.py`（新增）、`timodesk/app.py`、`timodesk/ui/main_window.py`、`docs/screenshot-*.png`
- **验证**：欢迎页 / 消息框 / 进度框三处截图核对；`test_core.py` 13/13；打包 exe 空库启动显示无边框欢迎页
- **影响**：全应用不再出现系统标题栏；文档截图同步更新

## 2026-11-06 — 改名 Timo For Windows、便携安装包、系统托盘

- **类型**：功能 / 打包 / 命名
- **内容**：
  - 项目改名 **Timo For Windows**（GitHub 仓库同步改名 `TangSong777/Timo-For-Windows`）
  - 数据目录由 `data/` 改为 `Data/`（便携文件夹看起来更整齐）
  - 新增单文件安装包 `Timo For Windows 安装包.exe`：自解压到指定文件夹、自动启动主程序、删除自身，全程无控制台
  - 新增系统托盘：单击唤出窗口、关闭窗口收进托盘、右键菜单（打开 / 新建笔记 / 打开数据文件夹 / 退出）
  - 主程序 exe 名改为 `Timo For Windows.exe`，标题栏副标题改为 `For Windows`
  - 发版资产由 zip 改为单文件安装包；`tools/make-release.py` 重写
- **文件**：`installer.py`、`tools/make-portable.py`、`tools/make-release.py`、`timodesk/ui/tray.py`、`timodesk/app.py`、`timodesk/ui/main_window.py`、`timodesk/ui/title_bar.py`、`assets/timo-tray.ico`、`README.md`、`.gitignore`
- **验证**：托盘三态测试（显示 / 关闭收进托盘 / 唤出）；安装包 `--silent` 解压 238 个文件含 `Data/`；onedir 主程序空库启动显示欢迎页；`--auto` 端到端通过（解压→启动→安装包自身 5 秒内删除）
- **影响**：安装包体积约 111 MB；未签名，首次运行会遇到 SmartScreen 提示

## 2026-11-06 — 界面质感：卡片、投影与动效，配色收成黑白灰

- **类型**：界面
- **内容**：三栏改成浮在浅灰画布上的白色圆角卡片（16px 圆角 + 1px 描边 + 自绘柔和投影）；编辑区格式栏、账号/链路/日子卡片改为统一的小卡片样式；窗口入场淡入、切页淡入、列表切换淡入、滚动条闲置时半透明；颜色标记由彩色改为 8 档灰阶；选中项加左侧指示条
- **文件**：`timodesk/ui/theme.py`、`timodesk/ui/widgets.py`、`timodesk/ui/main_window.py`、`timodesk/ui/editor.py`、`timodesk/ui/title_bar.py`
- **验证**：`test_core.py` 13/13；多轮截图核对三栏比例、卡片圆角、hover/选中态；确认「瑟瑟」主题名不是重影 bug（13px 下「瑟」字的正常字形）
- **影响**：纯视觉层，数据与交互未变

## 2026-11-06 — 功能一致性：待办勾选、全库搜索、类型菜单、回收站

- **类型**：功能
- **内容**：
  - 预览里的 `- [ ]` 变成可点击方框，点一下就回写正文（保留撤销栈）；便签常见的「标题下一行直接接列表」也能正确渲染
  - 搜索改为全库（在回收站内仍只搜回收站），标题显示当前搜索词
  - 「＋ 新建」右侧加类型菜单，可直接新建文章 / 图库 / 链接 / 日子 / 账号
  - 数据菜单加「清空回收站…」，带二次确认
  - 全部笔记、归档与搜索结果里的卡片显示所属主题
  - 列表空状态提示（这里还没有笔记 / 没有找到 xxx / 回收站是空的）
  - 图库支持批量添加图片、拖拽调整顺序
  - 删除主题时，主题内的笔记一起进回收站；恢复时若原主题已删，落到「（未分类）」
- **文件**：`timodesk/render.py`、`timodesk/ui/editor.py`、`timodesk/ui/main_window.py`、`timodesk/ui/widgets.py`、`timodesk/store.py`、`timodesk/exporter.py`
- **验证**：新增 `test_types.py`（32/32，六类型端到端 + 导出往返）、`test_ui.py`（20/20，真实控件写回）、`test_todo.py`（6/6）、`test_topic.py`（8/8）；`test_core.py` 13/13
- **影响**：修复了图库 / 链接 / 日子的说明字段之前不会写回 `library.json` 的问题
