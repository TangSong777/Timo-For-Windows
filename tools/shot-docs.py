"""生成 README 用的界面截图（需要本机有示例数据）。"""
import sys
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, ".")
from timodesk.store import Library
from timodesk.ui.theme import app_qss
from timodesk.ui.main_window import MainWindow

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setStyleSheet(app_qss())
lib = Library(r"D:/桌面/Timo For Windows/Data").load()
w = MainWindow(lib)
w.resize(1280, 830)
w.show()

TARGET = "d072305b-afd5-4cb2-9363-901070a7e551"


def pick():
    w.select_nav("all")
    for i in range(w.note_list.count()):
        if w.note_list.item(i).data(Qt.UserRole) == TARGET:
            w.note_list.setCurrentRow(i)
            break


def archived():
    w.select_nav("archived")


def top():
    w.note_list.scrollToTop()
    w.note_list.verticalScrollBar().setValue(0)


QTimer.singleShot(500, pick)
QTimer.singleShot(1300, top)
QTimer.singleShot(1600, lambda: w.grab().save("docs/screenshot-main.png"))
QTimer.singleShot(1800, archived)
QTimer.singleShot(2400, top)
QTimer.singleShot(2700, lambda: w.grab().save("docs/screenshot-archived.png"))
QTimer.singleShot(2900, app.quit)
app.exec_()
print("saved")
