"""拖动笔记到主题：信号通路与移动结果。"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

app = QApplication(sys.argv)
root = Path("worklib_drag")
lib = Library(root).load()
if not lib.topics:
    a = lib.add_topic("甲")
    b = lib.add_topic("乙")
    lib.add_note(a.id, "note", content="要移动的笔记", title="移动测试")
    lib.save()
tops = lib.sorted_topics()
a, b = tops[0], tops[1]
nid = next(n.id for n in lib.notes.values() if n.topic_id == a.id and n.state == "active")

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


# 1. 信号连接
check("noteDropped 已连接", w.topic_list.receivers(w.topic_list.noteDropped) > 0)

# 2. 直接发信号（等价于 drop）
w.topic_list.noteDropped.emit(nid, b.id)
app.processEvents()
check("笔记已移动到新主题", lib.notes[nid].topic_id == b.id)
check("library.json 已落盘", Library(root).load().notes[nid].topic_id == b.id)

# 3. 主题计数更新
counts = lib.note_counts()
check("目标主题计数 = 1", counts.get(b.id, 0) == 1)

# 4. 同主题再拖一次：无变化
w.topic_list.noteDropped.emit(nid, b.id)
app.processEvents()
check("重复拖到同一主题不报错", lib.notes[nid].topic_id == b.id)

# 5. MIME 类型常量
from timodesk.ui.widgets import NoteList
check("MIME 常量", NoteList.MIME == "application/x-timo-note")

# 6. 真实 dropEvent：用 QDropEvent 走一遍 TopicList.dropEvent
from PyQt5.QtCore import QMimeData, QPointF, Qt
from PyQt5.QtGui import QDropEvent

target_row = None
for i in range(w.topic_list.count()):
    t = w.topic_list.item(i).data(Qt.UserRole)
    if t.id == a.id:
        target_row = i
        break
mime = QMimeData()
mime.setData(NoteList.MIME, nid.encode("utf-8"))
rect = w.topic_list.visualItemRect(w.topic_list.item(target_row))
ev = QDropEvent(QPointF(rect.center()), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
w.topic_list.dropEvent(ev)
app.processEvents()
check("dropEvent 解析 MIME 并移动回甲", lib.notes[nid].topic_id == a.id)

# 7. 从当前主题视图移走后列表刷新
w.view = ("topic", a.id)
w._reload_notes()
check("主题视图列表包含该笔记", w.note_list.count() == 1)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
