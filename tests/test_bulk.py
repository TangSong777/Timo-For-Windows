"""多选批量操作与右键菜单健壮性。"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

app = QApplication(sys.argv)
root = Path("worklib_bulk")
lib = Library(root).load()
if not lib.topics:
    a = lib.add_topic("批量甲")
    b = lib.add_topic("批量乙")
    for i in range(5):
        lib.add_note(a.id, "note", content=f"第{i}条", title=f"T{i}")
    lib.save()
tops = lib.sorted_topics()
a, b = tops[0], tops[1]
ids = [n.id for n in lib.sorted_notes(topic_id=a.id)]

w = MainWindow(lib)
w.resize(1280, 830)
w.show()
app.processEvents()

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. 批量置顶
w._bulk_apply(ids[:3], "pin")
check("三条已置顶", all(lib.notes[i].pinned_at for i in ids[:3]))
check("其余未置顶", all(not lib.notes[i].pinned_at for i in ids[3:]))
order = lib.sorted_notes(topic_id=a.id)
check("置顶排在最前", all(n.pinned_at for n in order[:3]) and all(not n.pinned_at for n in order[3:]))

# 2. 批量移动到另一主题
w._bulk_apply(ids[:2], "move", b.id)
check("两条移动到乙", all(lib.notes[i].topic_id == b.id for i in ids[:2]))
check("库已落盘", all(Library(root).load().notes[i].topic_id == b.id for i in ids[:2]))

# 3. 批量归档
w._bulk_apply(ids[2:4], "archive")
check("两条已归档", all(lib.notes[i].state == "archived" for i in ids[2:4]))

# 4. 批量删除到回收站 + 恢复
w._bulk_apply(ids[2:4], "delete")
check("两条在回收站", all(lib.notes[i].state == "trash" for i in ids[2:4]))
w.view = ("trash", None)
w._bulk_apply(ids[2:4], "restore")
check("两条已恢复", all(lib.notes[i].state != "trash" for i in ids[2:4]))

# 5. 多选模式
check("列表支持多选", w.note_list.selectionMode() == w.note_list.ExtendedSelection)

# 6. 单条右键菜单不再因 a_del/a_restore 未定义而崩溃：直接检查源码路径
import inspect

src = inspect.getsource(MainWindow._note_menu)
check("a_del/a_restore 已初始化", "a_del = a_restore = None" in src)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
