# -*- coding: utf-8 -*-
"""搜索结果的顺序要跟随当前的排序方式。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_ss")
shutil.rmtree(ROOT, ignore_errors=True)
app = QApplication.instance() or QApplication(sys.argv)

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


lib = Library(ROOT).load()
t = lib.add_topic("测试")
for title in ("C 笔记", "A 笔记", "B 笔记"):
    lib.add_note(t.id, "article", "都有孤独这个词", title)
lib.save()

w = MainWindow(lib)
w.search.setText("孤独")
w._apply_search()

titles = [w.lib.notes[w.note_list.item(i).data(Qt.UserRole)].title for i in range(w.note_list.count())]
check("默认按更新时间", len(titles) == 3)

w.set_sort("title")
w.search.setText("孤独")
w._apply_search()
titles = [w.lib.notes[w.note_list.item(i).data(Qt.UserRole)].title for i in range(w.note_list.count())]
check("按标题排序生效", titles == ["A 笔记", "B 笔记", "C 笔记"])

w.set_sort("updated")
w.search.setText("孤独")
w._apply_search()
check("切回更新时间", w.note_list.count() == 3)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
