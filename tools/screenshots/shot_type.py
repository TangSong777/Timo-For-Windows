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

TARGETS = {
    "gallery": "3bf16cef-ff63-40f6-a111-212a5da076de",
    "account": "620bb4d3c0b9d9699f552157@10",
    "date": "f4b26348-1a58-4ce4-b804-527f28c37a0e",
    "date2": "521203fd-35d7-4972-9d06-816764aad460",
}

w = MainWindow(lib)
w.resize(1280, 830)
w.show()

which = sys.argv[1] if len(sys.argv) > 1 else "gallery"
nid = TARGETS[which]
note = lib.notes[nid]
topic = note.topic_id


def show_target():
    # 切到该笔记所属主题
    w.view = ("topic", topic)
    from PyQt5.QtCore import Qt
    for i in range(w.topic_list.count()):
        t = w.topic_list.item(i).data(Qt.UserRole)
        if t is not None and t.id == topic:
            w.topic_list.blockSignals(True)
            w.topic_list.setCurrentRow(i)
            w.topic_list.blockSignals(False)
            break
    w._reload_notes(select_id=nid)


QTimer.singleShot(400, show_target)
QTimer.singleShot(1500, lambda: w.grab().save(f"shot_{which}.png"))
QTimer.singleShot(1600, app.quit)
app.exec_()
print("saved")
