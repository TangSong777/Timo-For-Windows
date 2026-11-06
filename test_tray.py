"""验证托盘行为：关闭收进托盘、点托盘再唤出。"""
import sys
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss
from timodesk.ui.tray import TrayIcon

ROOT = Path(__file__).resolve().parent
app = QApplication(sys.argv)
app.setStyleSheet(app_qss())
app.setQuitOnLastWindowClosed(False)

lib = Library(ROOT / "testlib").load()
win = MainWindow(lib)
tray = TrayIcon(win)
win.tray = tray
tray.show()
app.setQuitOnLastWindowClosed(False)
win.show()

result = {}


def step1():
    result["tray_available"] = QSystemTrayIcon.isSystemTrayAvailable()
    result["tray_visible"] = tray.isVisible()
    result["win_visible_before"] = win.isVisible()
    win.close()
    app.processEvents()


def step2():
    result["win_visible_after_close"] = win.isVisible()
    result["hint_shown"] = win._tray_hinted
    tray.show_window()
    app.processEvents()
    result["win_visible_after_tray"] = win.isVisible()
    win.raise_()
    win.activateWindow()
    app.processEvents()


def step3():
    win.grab().save(str(ROOT / "shot_tray.png"))
    result["title"] = win.windowTitle()
    print(result)
    win._quitting = True
    win.close()
    app.quit()


QTimer.singleShot(700, step1)
QTimer.singleShot(1500, step2)
QTimer.singleShot(2300, step3)
sys.exit(app.exec_())
