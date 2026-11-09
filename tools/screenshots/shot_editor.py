import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from timodesk.store import Library
from timodesk.ui.theme import app_qss
from timodesk.ui.main_window import MainWindow

QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv)
app.setStyle("Fusion")
app.setStyleSheet(app_qss())
lib = Library("testlib").load()
w = MainWindow(lib)
w.resize(1280, 830)
w.show()

QTimer.singleShot(500, lambda: w.note_list.setCurrentRow(2))
QTimer.singleShot(1400, lambda: w.grab().save("shot_editor.png"))
QTimer.singleShot(1500, app.quit)
app.exec_()
print("saved")
