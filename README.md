# Timo For Windows

把 Android 上的 [Timo笔记](https://timo.idik.net/) 搬到 Windows 的本地笔记软件：**数据全在本机，不需要账号，不联网**。
直接导入手机 App 导出的 ZIP，改完还能再导出回去。

![主界面](docs/screenshot-main.png)

> 非官方项目，与 Timo 官方无关。本仓库只处理用户自己导出的数据，不包含、也不分发 Timo 的应用本体。

## 下载

到 [Releases](../../releases/latest) 下载 **`Timo For Windows 安装包.exe`**。

要求：Windows 10 / 11 64 位。

## 怎么用（便携版）

### 1. 解包

双击下载的 `Timo For Windows 安装包.exe`：

1. 弹出小窗口，显示要解压到的位置，默认是安装包旁边新建的 `Timo For Windows` 文件夹；
2. 想换地方就点 **更改…** 选一个目录（会在里面再建一个 `Timo For Windows`）；
3. 点 **解压到这里**，等进度条走完。

解压完成后：程序会自动打开，**安装包自己删除**，留下的就是一个可以直接用的文件夹：

```
Timo For Windows/
├── Timo For Windows.exe   ← 双击这个启动
├── _internal/             ← 运行需要的 Qt 等 dll，别删
└── Data/                  ← 你的笔记数据
```

整个过程不写注册表、不装服务、不出现命令行黑框。

> **第一次运行会被 Windows 拦一下。** 这个安装包没有买代码签名证书，Windows SmartScreen 会提示「Windows 已保护你的电脑」——点 **更多信息** → **仍要运行** 就行。少数杀毒软件也会对「自己解压自己」的安装包报警，可以把它加进白名单。

### 2. 第一次打开

双击 `Timo For Windows.exe`，会问你要不要导入手机上的数据：

1. 打开手机上的 Timo笔记 → 设置 → 导出可读副本，得到 `Timo_Export_xxxx.zip`；
2. 在欢迎页点 **导入 Timo 导出包（.zip）**，选中那个 ZIP；
3. 等几秒，主题、笔记、图片、账号就都进来了。

也可以跳过欢迎页，之后从侧栏底部的 `⋯` 菜单导入；把 ZIP 直接拖到 `Timo For Windows.exe` 图标上也能导入。

### 3. 搬家 / 备份

所有东西都在这个文件夹里：

```
Data/
├── library.json      # 主题与笔记元数据
├── notes/*.md        # 每条笔记的正文（Markdown）
└── attachments/      # 图片等附件原件
```

要换电脑或备份，直接复制整个 `Timo For Windows` 文件夹即可；想回手机上用，从 `⋯` 菜单 **导出为 Timo ZIP**，再把 ZIP 导回手机。

### 4. 托盘

- 点窗口右上角的 **✕** 不会退出，而是收进系统托盘（右下角时间旁边）；
- **单击托盘图标** 重新打开窗口；
- **右键托盘图标**：打开 Timo For Windows / 新建笔记 / 打开数据文件夹 / 退出。

## 功能

| 功能 | 说明 |
| --- | --- |
| 六种笔记类型 | 便签、文章、图库、账号、链接、日子，各自保留 Timo 的展示样式；「＋ 新建」右侧的 `▾` 可直接选类型 |
| Markdown | 编辑 + 实时预览，支持粘贴图片、拖入图片文件 |
| 待办清单 | `- [ ]` 在预览里是可点的方框，点一下就打勾（直接写回正文） |
| 图库 | 批量添加图片、拖拽调整顺序、双击看大图 |
| 整理 | 全库搜索、置顶、8 档灰阶颜色标记、归档、回收站（可清空）、跨主题移动 |
| 拖动 | 把笔记卡片拖到左侧任一主题上，直接移动过去；`Ctrl`/`Shift` 多选后可批量置顶、归档、删除、移动 |
| 提醒 | 编辑器右上角「提醒」可设到点提醒（一小时后 / 今天 20:00 / 明天 9:00 / 自定义），到点从托盘弹出；卡片与顶部按钮会标出提醒时间 |
| 主题 | 新建 / 改名 / 删除 / 拖拽排序；删主题时里面的笔记一起进回收站；归档主题在侧栏灰显 |
| 导入导出 | 与 Timo 官方 ZIP 结构兼容，可往返 |
| 自动保存 | 停顿 0.7 秒写盘，关窗时再存一次 |
| 应用锁 | 数据菜单里设置启动密码（PBKDF2 哈希存在 `Data/settings.json`），下次启动需输入 |

常用快捷键：`Ctrl+N` 新建笔记、`Ctrl+Shift+N` 新建主题、`Ctrl+F` 搜索、`Ctrl+S` 保存、`Ctrl+E` 切换编辑/分屏/预览。

### 界面

三栏布局，左栏主题与导航，中栏笔记卡片，右栏按类型切换的编辑器：

![归档主题视图](docs/screenshot-archived.png)

## 已知说明

- 密码以明文保存在 `library.json`（与 Timo 导出的 `accounts.csv` 一致）。程序不加密、不联网，别把数据目录发给别人。
- 应用锁只拦在本机打开程序的人，`Data/` 里的内容本身没有加密；忘记密码无法找回（数据还在，删掉 `settings.json` 的 `lock` 即可解除）。
- 手机端的云同步、桌面小组件没有移植；提醒是本地功能，Timo 导出包不带提醒字段，所以**导出回手机时提醒会丢**，其余内容不受影响。
- 首次导入 1000 条笔记约需 5 秒。
- 如果把程序放在 U 盘里用，`Data/` 会跟着 U 盘走；U 盘拔掉前先退出程序。

## 从源码运行

```bat
pip install PyQt5 markdown
python run.py
```

打便携版（主程序 + 自解压安装包）：

```bat
python tools/make-portable.py
```

产物：

- `dist/Timo For Windows/Timo For Windows.exe` —— 解压后的程序本体
- `dist/Timo For Windows 安装包.exe` —— 用来分发的单文件安装包

## 开发

- 分支模型：`snapshot` 是日常工作分支，`master` 只接受 `git merge --ff-only snapshot`，发版时打 tag 并发布 Release。
- 每次改动追加一条到 `PENDING-CHANGES.md`，发版时汇总进 `CHANGELOG.md`。

## 许可

[MIT](LICENSE)
