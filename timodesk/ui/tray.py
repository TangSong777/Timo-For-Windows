"""系统托盘：点图标打开窗口，右键菜单退出。"""
from __future__ import annotations

import subprocess
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon

from .title_bar import _base_dir, app_icon


class TrayIcon(QSystemTrayIcon):
    """托盘图标：左键/双击唤出主窗口，右键菜单退出。"""

    def __init__(self, window, parent=None):
        super().__init__(self._pick_icon(), parent)
        self.window = window
        self.setToolTip("Timo For Windows · 本地笔记")

        menu = QMenu()
        act_show = QAction("打开 Timo For Windows", menu)
        act_show.triggered.connect(self.show_window)
        menu.addAction(act_show)

        act_new = QAction("新建笔记", menu)
        act_new.triggered.connect(self.new_note)
        menu.addAction(act_new)
        menu.addSeparator()

        act_data = QAction("打开数据文件夹", menu)
        act_data.triggered.connect(self.open_data_dir)
        menu.addAction(act_data)
        menu.addSeparator()

        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self.quit_app)
        menu.addAction(act_quit)

        self.setContextMenu(menu)
        self._menu = menu  # 防止被回收
        self.activated.connect(self._on_activated)

    # ---------------- 图标 ----------------
    @staticmethod
    def _pick_icon() -> QIcon:
        for name in ("timo-tray.ico", "timo-icon.png"):
            p = _base_dir() / "assets" / name
            if p.exists():
                return QIcon(str(p))
        return app_icon()

    # ---------------- 行为 ----------------
    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    def show_window(self):
        w = self.window
        if w is None:
            return
        if w.isMinimized():
            w.showNormal()
        w.show()
        w.raise_()
        w.activateWindow()

    def new_note(self):
        self.show_window()
        QApplication.processEvents()
        w = self.window
        if w is not None and hasattr(w, "new_note"):
            w.new_note()

    def open_data_dir(self):
        w = self.window
        if w is None:
            return
        path = str(w.lib.root)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", path])
        else:  # pragma: no cover
            subprocess.Popen(["xdg-open", path])

    def quit_app(self):
        w = self.window
        if w is not None:
            w._quitting = True
            try:
                w.save_now()
                w.lib.save()
            except Exception:  # noqa: BLE001
                pass
        self.hide()
        QApplication.quit()
