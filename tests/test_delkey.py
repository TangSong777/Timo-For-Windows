"""列表上按 Delete：移到回收站。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
import timodesk.ui.dialogs as D

app = QApplication(sys.argv)
root = Path("worklib_delkey")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t = lib.add_topic("删除测试")
n1 = lib.add_note(t.id, "note", content="第一条", title="一")
n2 = lib.add_note(t.id, "note", content="第二条", title="二")
lib.save()

w = MainWindow(lib)
w.resize(1280, 830)
w.show()
app.processEvents()

ok = 0
total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


D.confirm = lambda *a, **k: True
w._on_notes_delete_key([n1.id])
app.processEvents()
check("单条移到回收站", lib.notes[n1.id].state == "trash")
check("已落盘", Library(root).load().notes[n1.id].state == "trash")
check("另一条不受影响", lib.notes[n2.id].state == "active")

# 取消确认
calls = []
D.confirm = lambda *a, **k: (calls.append(1), False)[1]
w._on_notes_delete_key([n2.id])
check("取消时不删", lib.notes[n2.id].state == "active")

# 回收站里的笔记不在这里处理
D.confirm = lambda *a, **k: (calls.append(2), True)[1]
w._on_notes_delete_key([n1.id])
check("回收站里的笔记保持 trash", lib.notes[n1.id].state == "trash")
check("回收站笔记不弹确认", len(calls) == 1)

# 真实按键走 NoteList.keyPressEvent
D.confirm = lambda *a, **k: True
w.view = ("topic", t.id)
w._reload_notes()
w.note_list.setCurrentRow(0)
app.processEvents()
ev = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
w.note_list.keyPressEvent(ev)
app.processEvents()
check("按 Delete 键也能删", all(n.state == "trash" for n in lib.notes.values()))

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
