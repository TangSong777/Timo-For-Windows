"""Timo 桌面版启动入口。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .importer import import_export
from .store import Library
from .ui.main_window import MainWindow
from .ui.theme import app_qss

from . import __version__

APP_NAME = "Timo Desktop"
APP_VERSION = __version__


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """便携优先：程序目录/data；不可写时退到用户目录。"""
    d = Path(os.environ.get("TIMO_DATA_DIR") or (base_dir() / "data"))
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


class WelcomeDialog(QDialog):
    """首次启动：导入 Timo 导出包，或从空库开始。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.choice = "cancel"
        self.path: str | None = None
        self.setWindowTitle("欢迎使用 Timo 桌面版")
        self.setFixedSize(560, 420)
        self.setStyleSheet(
            f"""
            QDialog {{ background:#ffffff; }}
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
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 36, 40, 30)
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
    pr = QProgressDialog("正在导入，请稍候…", None, 0, 100)
    pr.setWindowTitle("导入 Timo 数据")
    pr.setWindowModality(Qt.WindowModal)
    pr.setMinimumDuration(0)
    pr.show()

    def pg(done, total):
        pr.setMaximum(total)
        pr.setValue(done)
        QApplication.processEvents()

    try:
        report = import_export(path, lib, progress=pg)
        lib.save()
        QMessageBox.information(
            None,
            "导入完成",
            f"主题 {report.topics} 个、笔记 {report.notes} 条、附件 {report.attachments} 个。",
        )
    except Exception as e:  # noqa: BLE001
        pr.close()
        QMessageBox.critical(None, "导入失败", str(e))
        return False
    pr.close()
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
    lib = Library(root).load()

    cli = next((a for a in sys.argv[1:] if a and Path(a).exists()), "")
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
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(run())
