"""提醒：数据层、时间转换与编辑器按钮状态。"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library, from_iso, to_iso
from timodesk.ui.main_window import MainWindow

app = QApplication(sys.argv)
root = Path("worklib_remind")
lib = Library(root).load()
if not lib.topics:
    t = lib.add_topic("提醒测试")
    n1 = lib.add_note(t.id, "note", content="到点的笔记")
    n2 = lib.add_note(t.id, "note", content="以后的笔记")
    lib.save()
else:
    t = lib.sorted_topics()[0]
    n1, n2 = list(lib.sorted_notes())[:2]

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. 时间转换往返
dt = datetime.now().replace(microsecond=0).astimezone()
back = from_iso(to_iso(dt))
check("to_iso/from_iso 往返", back is not None and abs((back - dt).total_seconds()) < 1)

# 2. 设置提醒
past = to_iso(datetime.now() - timedelta(minutes=1))
future = to_iso(datetime.now() + timedelta(hours=2))
lib.set_reminder(n1.id, past)
lib.set_reminder(n2.id, future)
lib = Library(root).load()
check("提醒已持久化", lib.notes[n1.id].remind_at == past)

# 3. 未到期的不触发
check("upcoming 顺序", [n.id for n in lib.upcoming_reminders()] == [n2.id])

# 4. 到点触发并清空
due = lib.due_reminders()
check("到期列表只有一条", [n.id for n in due] == [n1.id])
check("触发后 remind_at 清空", lib.notes[n1.id].remind_at is None)
check("清空已落盘", Library(root).load().notes[n1.id].remind_at is None)

# 5. 再次调用不会重复提醒
check("不重复触发", lib.due_reminders() == [])

# 6. 主窗口按钮状态
w = MainWindow(lib)
w.resize(1280, 830)
w.show()
app.processEvents()
w.note_list.setCurrentRow(0)
app.processEvents()
note = w.editor.note
check("选中笔记", note is not None)
w.editor.set_note(lib.notes[n2.id])
app.processEvents()
check("提醒按钮显示 ⏰", w.editor.btn_remind.text() == "⏰")

# 7. 无托盘时检查不崩
w.tray = None
w._check_reminders()
check("_check_reminders 不崩", True)

# 8. 清除提醒
w.lib.set_reminder(w.editor.note.id, None)
w.editor._sync_remind()
check("清除后按钮恢复「提醒」", w.editor.btn_remind.text() == "提醒")

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
