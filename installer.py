"""Timo For Windows 便携版安装器。

双击后选一个位置，把内置的 payload.zip 解开到 `<位置>/Timo For Windows/`，
启动主程序，然后删掉自己。全程无控制台窗口。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from timodesk.ui.dialogs import _BTN_QSS, confirm, error
from timodesk.ui.title_bar import FramelessDialog, _base_dir, app_icon

MAIN_EXE = "Timo For Windows.exe"
FOLDER_NAME = "Timo For Windows"
CREATE_NO_WINDOW = 0x08000000


def payload_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    p = base / "payload.zip"
    if not p.exists():
        p = Path(__file__).resolve().parent / "build" / "payload.zip"
    return p


def default_target() -> Path:
    return _base_dir() / FOLDER_NAME


def _is_safe(target: Path, name: str) -> bool:
    try:
        dest = (target / name).resolve()
        return str(dest).startswith(str(target.resolve()))
    except Exception:  # noqa: BLE001
        return False


class InstallThread(QThread):
    progressed = pyqtSignal(int, int, str)
    failed = pyqtSignal(str)

    def __init__(self, zip_path: Path, target: Path):
        super().__init__()
        self.zip_path = zip_path
        self.target = target

    def run(self):  # noqa: D401
        try:
            with zipfile.ZipFile(self.zip_path) as zf:
                items = zf.infolist()
                total = len(items)
                for n, info in enumerate(items, 1):
                    if not _is_safe(self.target, info.filename):
                        continue
                    dest = self.target / info.filename
                    if info.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(info) as src, open(dest, "wb") as out:
                            shutil.copyfileobj(src, out)
                    self.progressed.emit(n, total, info.filename)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class SetupDialog(FramelessDialog):
    def __init__(self):
        super().__init__(None, "安装 Timo For Windows")
        self.setWindowTitle("安装 Timo For Windows")
        self.setFixedSize(580, 380)
        self._thread = None
        self._installed_to: Path | None = None

        self.setStyleSheet(
            _BTN_QSS
            + """
            #DialogBody { background:#ffffff; }
            QLabel#Big { font-size:26px; color:#1f1f1f; font-weight:600; }
            QLabel#Hint { color:#6b6b6b; font-size:13px; }
            QLineEdit#PathBox {
                border:1px solid #e4e4e4; border-radius:8px; padding:9px 11px;
                font-size:13px; background:#ffffff;
            }
            QLineEdit#PathBox:focus { border-color:#1f1f1f; }
            QProgressBar { border:none; background:#f0f0f0; border-radius:3px; }
            QProgressBar::chunk { background:#1f1f1f; border-radius:3px; }
            """
        )

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(34, 26, 34, 26)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Timo For Windows", objectName="Big"))
        hint = QLabel(
            "绿色版，不用安装、不写注册表。解压到下面的文件夹就能用，\n"
            "笔记和图片都保存在这个文件夹的 Data 目录里，整个文件夹可以拷走。"
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addSpacing(8)

        lay.addWidget(QLabel("安装到", objectName="Hint"))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.path_box = QLineEdit(str(default_target()), objectName="PathBox")
        row.addWidget(self.path_box, 1)
        btn_pick = QPushButton("更改…", objectName="Plain")
        btn_pick.clicked.connect(self._pick_dir)
        row.addWidget(btn_pick)
        lay.addLayout(row)
        lay.addSpacing(6)

        self.bar = QProgressBar()
        self.bar.setFixedHeight(6)
        self.bar.setTextVisible(False)
        self.bar.hide()
        lay.addWidget(self.bar)

        self.status = QLabel("", objectName="Hint")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        lay.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_cancel = QPushButton("取消", objectName="Plain")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        self.btn_ok = QPushButton("解压到这里", objectName="Primary")
        self.btn_ok.clicked.connect(self._start)
        btns.addWidget(self.btn_ok)
        lay.addLayout(btns)

        self.setWindowIcon(app_icon())
        self.add_edge()

    # ---------------- 交互 ----------------
    def _pick_dir(self):
        p = QFileDialog.getExistingDirectory(
            self, "选择安装位置", str(_base_dir())
        )
        if p:
            self.path_box.setText(str(Path(p) / FOLDER_NAME))

    def _start(self):
        target = Path(self.path_box.text().strip() or str(default_target()))
        exe = target / MAIN_EXE
        if exe.exists():
            if not confirm(
                self,
                "已存在",
                f"这个文件夹里已经有 {MAIN_EXE}：\n{target}\n\n继续会覆盖旧文件（笔记数据不会动）。",
                ok_text="覆盖",
                cancel_text="换个位置",
            ):
                return
        zip_path = payload_path()
        if not zip_path.exists():
            error(self, "安装包损坏", f"找不到内置的 payload.zip：{zip_path}")
            return

        self.btn_ok.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.path_box.setEnabled(False)
        self.bar.show()
        self.status.setText("正在解压…")

        self._thread = InstallThread(zip_path, target)
        self._thread.progressed.connect(self._on_progress)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(lambda: self._on_done(target))
        self._thread.start()

    def _on_progress(self, done: int, total: int, name: str):
        self.bar.setMaximum(max(total, 1))
        self.bar.setValue(done)
        short = name if len(name) <= 46 else "…" + name[-45:]
        self.status.setText(f"正在解压 {done}/{total}　{short}")

    def _on_failed(self, msg: str):
        self.bar.hide()
        self.btn_ok.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.path_box.setEnabled(True)
        self.status.setText("")
        error(self, "解压失败", msg)

    def _on_done(self, target: Path):
        exe = target / MAIN_EXE
        if not exe.exists():
            self._on_failed(f"解压完成，但没有找到 {MAIN_EXE}。")
            return
        self.status.setText("解压完成，正在启动…")
        try:
            # 让主程序稍后删掉安装包自己（主程序有完整 Python，能处理中文路径）
            subprocess.Popen([str(exe), "--delete", sys.executable], cwd=str(target))
        except Exception as e:  # noqa: BLE001
            error(self, "启动失败", f"程序已经解压好了，但没能启动：{e}\n\n请手动双击：{exe}")
            return
        self._installed_to = target
        self.accept()


def silent_install(target: Path) -> int:
    """无界面解压（测试 / 批量部署用）：installer.exe --silent <目录>"""
    zp = payload_path()
    if not zp.exists():
        return 1
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp) as zf:
        for info in zf.infolist():
            if not _is_safe(target, info.filename):
                continue
            dest = target / info.filename
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    return 0 if (target / MAIN_EXE).exists() else 1


def main() -> int:
    argv = sys.argv[1:]
    if "--silent" in argv:
        i = argv.index("--silent")
        target = Path(argv[i + 1]) if i + 1 < len(argv) else default_target()
        return silent_install(target)

    if "--auto" in argv:
        i = argv.index("--auto")
        target = Path(argv[i + 1]) if i + 1 < len(argv) else default_target()
        if silent_install(target) != 0:
            return 1
        subprocess.Popen(
            [str(target / MAIN_EXE), "--delete", sys.executable],
            cwd=str(target),
        )
        return 0

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("Timo For Windows Setup")
    app.setApplicationDisplayName("")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setWindowIcon(app_icon())
    dlg = SetupDialog()
    dlg.exec_()
    return 0


if __name__ == "__main__":
    sys.exit(main())
