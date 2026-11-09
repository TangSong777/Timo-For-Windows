#!/usr/bin/env python
"""搜索后切换视图：搜索应被清掉，列表回到该视图的完整内容。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

app = QApplication([])
ok = 0
total = 0


def check(name, cond):
    global ok, total
    total += 1
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name}")


root = Path("worklib_sv")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t1 = lib.add_topic("甲").id
t2 = lib.add_topic("乙").id
a = lib.add_note(t1, "note", "孤独的旅人", None)
b = lib.add_note(t1, "note", "普通内容", None)
c = lib.add_note(t2, "note", "另一条孤独", None)
lib.archive_note(b.id)
lib.save()

w = MainWindow(lib)
app.processEvents()

# 搜索
w.search.setText("孤独")
w._apply_search()
app.processEvents()
check("搜索命中 2 条", w.note_list.count() == 2)
check("标题显示搜索词", "搜索" in w.header_label.text())

# 切到归档
w.select_nav("archived")
app.processEvents()
check("切视图后搜索框清空", w.search.text() == "")
check("切视图后标题不再显示搜索", "搜索" not in w.header_label.text())
check("归档视图只剩 1 条", w.note_list.count() == 1)

# 搜索后点主题
w.search.setText("孤独")
w._apply_search()
app.processEvents()
check("再次搜索 2 条", w.note_list.count() == 2)
row = next(i for i in range(w.topic_list.count()) if w.topic_list.item(i).data(0x0100).id == t2)
w.topic_list.setCurrentRow(row)
app.processEvents()
check("点主题后搜索清空", w.search.text() == "")
check("主题视图 1 条", w.note_list.count() == 1)

# Esc 清空搜索并把焦点给列表
w.search.setText("普通")
w._apply_search()
app.processEvents()
w._clear_search(focus=True)
app.processEvents()
check("Esc 清空搜索", w.search.text() == "" and w.note_list.count() >= 1)

print(f"\ntotal: {ok} / {total}")
sys.exit(0 if ok == total else 1)
