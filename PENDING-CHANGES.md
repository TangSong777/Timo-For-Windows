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
