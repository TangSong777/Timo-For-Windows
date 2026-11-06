"""Timo 桌面版启动入口。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .importer import import_export
from .store import Library
from .ui.main_window import MainWindow
from .ui.theme import app_qss
from .ui.title_bar import FramelessDialog
from .ui.dialogs import ProgressDialog, error, info
from .ui.tray import TrayIcon

from . import __version__

APP_NAME = "Timo For Windows"
APP_VERSION = __version__


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """便携优先：程序目录/Data；不可写时退到用户目录。"""
    d = Path(os.environ.get("TIMO_DATA_DIR") or (base_dir() / "Data"))
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return d
    except Exception:
        alt = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TimoDesktop"
        alt.mkdir(parents=True, exist_ok=True)
        return alt


def _install_excepthook(root: Path) -> None:
    """windowed 模式没有控制台，未捕获异常写进 Data/error.log。"""
    log = root / "error.log"

    def hook(tp, val, tb):
        import traceback
        from datetime import datetime

        text = "".join(traceback.format_exception(tp, val, tb))
        try:
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}")
        except Exception:  # noqa: BLE001
            pass
        sys.__excepthook__(tp, val, tb)

    sys.excepthook = hook


def _schedule_delete(paths: list[str]) -> None:
    """安装器把删除自己的活儿交给主程序：等安装包退出后再删掉它。"""
    if not paths:
        return
    import threading
    import time

    def work(p: Path) -> None:
        for _ in range(60):
            try:
                if not p.exists():
                    return
                p.unlink()
                return
            except OSError:
                time.sleep(0.5)

    for item in paths:
        threading.Thread(target=work, args=(Path(item),), daemon=True).start()


class WelcomeDialog(FramelessDialog):
    """首次启动：导入 Timo 导出包，或从空库开始。"""

    def __init__(self, parent=None):
        super().__init__(parent, "欢迎使用 Timo 桌面版")
        self.choice = "cancel"
        self.path: str | None = None
        self.setWindowTitle("欢迎使用 Timo 桌面版")
        self.setFixedSize(560, 462)
        self.setStyleSheet(
            f"""
            #DialogBody {{ background:#ffffff; }}
            QLabel#Big {{ font-size:30px; color:#1f1f1f; font-weight:600; }}
            QLabel#Sub {{ color:#737373; font-size:13px; }}
            QPushButton#Primary {{
                background:#1f1f1f; color:white; border:none; border-radius:10px;
                padding:12px 18px; font-size:14px; font-weight:600;
            }}
            QPushButton#Primary:hover {{ background:#000000; }}
            QPushButton#Plain {{
                background:#ffffff; border:1px solid #e4e4e4; border-radius:10px;
                padding:12px 18px; font-size:13px; color:#1f1f1f;
            }}
            QPushButton#Plain:hover {{ border-color:#1f1f1f; }}
            """
        )
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(40, 28, 40, 30)
        lay.setSpacing(10)
        title = QLabel("Timo", objectName="Big")
        lay.addWidget(title)
        sub = QLabel("本地笔记 · Windows 桌面版", objectName="Sub")
        lay.addWidget(sub)
        lay.addSpacing(14)
        desc = QLabel(
            "数据完全保存在这台电脑上，不需要账号，也不会联网。\n"
            "如果你用过手机上的 Timo，可以直接导入它的「可读数据导出」ZIP，\n"
            "主题、笔记、图片和账号都会原样搬过来。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#4a4a4a;font-size:13px;line-height:1.8;")
        lay.addWidget(desc)
        lay.addStretch(1)

        btn_import = QPushButton("导入 Timo 导出包（.zip）", objectName="Primary")
        btn_import.clicked.connect(self._pick_zip)
        lay.addWidget(btn_import)

        row = QHBoxLayout()
        btn_new = QPushButton("从空白开始", objectName="Plain")
        btn_new.clicked.connect(self._new_empty)
        row.addWidget(btn_new)
        btn_folder = QPushButton("导入解压后的文件夹", objectName="Plain")
        btn_folder.clicked.connect(self._pick_folder)
        row.addWidget(btn_folder)
        lay.addLayout(row)

        quit_row = QHBoxLayout()
        quit_row.addStretch(1)
        b = QPushButton("退出")
        b.setFlat(True)
        b.setStyleSheet("color:#a3a3a3;border:none;")
        b.clicked.connect(self.reject)
        quit_row.addWidget(b)
        lay.addLayout(quit_row)

        ico = base_dir() / "assets" / "timo-icon.png"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))
        self.add_edge()

    def _pick_zip(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择 Timo 导出包", "", "Timo 导出 (*.zip);;所有文件 (*)")
        if p:
            self.choice, self.path = "import", p
            self.accept()

    def _pick_folder(self):
        p = QFileDialog.getExistingDirectory(self, "选择包含 manifest.json 的文件夹")
        if p:
            self.choice, self.path = "import", p
            self.accept()

    def _new_empty(self):
        self.choice = "empty"
        self.accept()


def _import_with_progress(lib: Library, path: str) -> bool:
    pr = ProgressDialog(None, "导入 Timo 数据", "正在导入，请稍候…")
    pr.show()
    QApplication.processEvents()

    def pg(done, total):
        pr.set_progress(done, total)
        QApplication.processEvents()

    try:
        report = import_export(path, lib, progress=pg)
        lib.save()
        pr.close()
        info(
            None,
            "导入完成",
            f"主题 {report.topics} 个、笔记 {report.notes} 条、附件 {report.attachments} 个。",
        )
    except Exception as e:  # noqa: BLE001
        pr.close()
        error(None, "导入失败", str(e))
        return False
    return True


def run():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("")
    app.setOrganizationName("TimoDesktop")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(app_qss())

    ico = base_dir() / "assets" / "timo-icon.png"
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))

    root = data_dir()
    _install_excepthook(root)

    args = list(sys.argv[1:])
    delete_targets: list[str] = []
    if "--delete" in args:
        i = args.index("--delete")
        if i + 1 < len(args):
            delete_targets.append(args[i + 1])
            del args[i : i + 2]
    # 尽早开始，避免被欢迎对话框等模态窗口挡住
    _schedule_delete(delete_targets)

    lib = Library(root).load()

    cli = next((a for a in args if a and Path(a).exists()), "")
    if cli:
        if not _import_with_progress(lib, cli):
            return 1
    elif not lib.notes and not lib.topics:
        dlg = WelcomeDialog()
        if dlg.exec_() != QDialog.Accepted:
            return 0
        if dlg.choice == "import" and dlg.path:
            if not _import_with_progress(lib, dlg.path):
                return 1

    win = MainWindow(lib)
    tray = TrayIcon(win)
    win.tray = tray
    tray.show()
    app.setQuitOnLastWindowClosed(False)
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(run())
