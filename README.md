# Timo 桌面版（Windows）

把 Android 上的 [Timo笔记](https://timo.idik.net/) 搬到 Windows 的本地笔记软件：**数据全在本机，不需要账号，不联网**。
直接导入手机 App 导出的 ZIP，改完还能再导出回去。

![主界面](docs/screenshot-main.png)

> 非官方项目，与 Timo 官方无关。本仓库只处理用户自己导出的数据，不包含、也不分发 Timo 的应用本体。

## 下载

到 [Releases](../../releases/latest) 下载 `TimoDesktop-<版本>-win64.zip`，解压后双击 `Timo笔记.exe`。

要求：Windows 10 / 11 64 位。无需安装，也不写注册表——整个文件夹拷到别处就能用。

## 快速开始

1. 打开手机上的 Timo笔记 → 设置 → 导出可读副本，得到 `Timo_Export_xxxx.zip`。
2. 双击 `Timo笔记.exe`，首次启动选择「导入 Timo 导出包（.zip）」。
3. 也可以把 ZIP 直接拖到 exe 上，或先从空白开始、之后再从左上角 `⋯` 菜单导入。

数据保存在程序旁的 `data/` 目录：

```
data/
├── library.json      # 主题与笔记元数据
├── notes/*.md        # 每条笔记的正文（Markdown）
└── attachments/      # 图片等附件原件
```

## 功能

| 功能 | 说明 |
| --- | --- |
| 六种笔记类型 | 便签、文章、图库、账号、链接、日子，各自保留 Timo 的展示样式 |
| Markdown | 编辑 + 实时预览，支持粘贴图片、拖入图片文件 |
| 整理 | 搜索、置顶、8 种颜色标记、归档、回收站、跨主题移动 |
| 主题 | 新建 / 改名 / 删除 / 拖拽排序；归档主题在侧栏灰显 |
| 导入导出 | 与 Timo 官方 ZIP 结构兼容，可往返 |
| 自动保存 | 停顿 0.7 秒写盘，关窗时再存一次 |

常用快捷键：`Ctrl+N` 新建笔记、`Ctrl+Shift+N` 新建主题、`Ctrl+F` 搜索、`Ctrl+S` 保存、`Ctrl+E` 切换编辑/分屏/预览。

### 界面

三栏布局，左栏主题与导航，中栏笔记卡片，右栏按类型切换的编辑器：

![归档主题视图](docs/screenshot-archived.png)

## 已知说明

- 密码以明文保存在 `library.json`（与 Timo 导出的 `accounts.csv` 一致）。程序不加密、不联网，别把数据目录发给别人。
- 手机端的指纹锁、提醒、云同步、桌面小组件没有移植——本地版只做笔记本身。
- 首次导入 1000 条笔记约需 5 秒。

## 从源码运行

```bat
pip install PyQt5 markdown
python run.py
```

打包（PyInstaller）：

```bat
pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --name "Timo笔记" ^
  --icon assets/timo-icon.ico --add-data "assets;assets" run.py
```

## 开发

- 分支模型：`snapshot` 是日常工作分支，`master` 只接受 `git merge --ff-only snapshot`，发版时打 tag 并发布 Release。
- 每次改动追加一条到 `PENDING-CHANGES.md`，发版时汇总进 `CHANGELOG.md`。

## 许可

[MIT](LICENSE)
