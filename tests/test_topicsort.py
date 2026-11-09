# -*- coding: utf-8 -*-
"""主题列表按名称 / 笔记数 / 更新时间排序。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_ts")
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
tb = lib.add_topic("B主题")
ta = lib.add_topic("A主题")
tc = lib.add_topic("C主题")
for _ in range(2):
    lib.add_note(tb.id, "note", "b", None)
lib.add_note(ta.id, "note", "a", None)
for _ in range(3):
    lib.add_note(tc.id, "note", "c", None)
lib.save()

w = MainWindow(lib)


def names():
    return [w.topic_list.item(i).data(Qt.UserRole).name for i in range(w.topic_list.count())]


check("初始 3 个", len(names()) == 3)

w.sort_topics("name")
check("按名称", names() == ["A主题", "B主题", "C主题"])

w.sort_topics("count")
check("按笔记数（多的在前）", names() == ["C主题", "B主题", "A主题"])

# 顺序写进 library.json
lib2 = Library(ROOT).load()
check("持久化", [t.name for t in lib2.sorted_topics()] == ["C主题", "B主题", "A主题"])

# 单个主题时不折腾
lib3 = Library(ROOT / "one").load()
lib3.add_topic("唯一")
lib3.save()
w3 = MainWindow(lib3)
w3.sort_topics("name")
check("单主题不出错", w3.topic_list.count() == 1)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
