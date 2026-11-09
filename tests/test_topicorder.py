#!/usr/bin/env python
"""主题拖动排序：顺序要能保存，item 里的 Topic 对象不能丢。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtCore import Qt
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


class FakeEvent:
    def __init__(self, pos):
        self._p = pos

    def pos(self):
        return self._p


def names(tl):
    return [tl.item(i).data(Qt.UserRole).name for i in range(tl.count())]


root = Path("worklib_torder")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
for nm in ("甲", "乙", "丙"):
    lib.add_topic(nm)
lib.save()

w = MainWindow(lib)
tl = w.topic_list
check("初始顺序", names(tl) == ["甲", "乙", "丙"])

# 把第 1 个拖到列表末尾的空白处
tl._drag_row = 0
blank = tl.viewport().rect().bottomLeft()
tl._move_row(FakeEvent(blank))
check("拖动后界面顺序", names(tl) == ["乙", "丙", "甲"])
check("拖动后 Topic 对象还在", all(tl.item(i).data(Qt.UserRole) is not None for i in range(3)))

w._on_topics_reordered()
reloaded = Library(root).load()
order = [t.name for t in sorted(reloaded.topics.values(), key=lambda t: t.order)]
check("顺序已持久化", order == ["乙", "丙", "甲"])

# 重开窗口顺序一致
w2 = MainWindow(reloaded)
check("重开窗口顺序", names(w2.topic_list) == ["乙", "丙", "甲"])

# 拖到最前
tl._drag_row = 2
tl._move_row(FakeEvent(tl.visualItemRect(tl.item(0)).topLeft()))
check("拖到最前", names(tl) == ["甲", "乙", "丙"])
w._on_topics_reordered()
order2 = [t.name for t in sorted(Library(root).load().topics.values(), key=lambda t: t.order)]
check("拖到最前已保存", order2 == ["甲", "乙", "丙"])

# 原地放下不改变顺序、不报错
before = names(tl)
tl._drag_row = 1
tl._move_row(FakeEvent(tl.visualItemRect(tl.item(1)).center()))
check("原地放下无变化", names(tl) == before)

print(f"\ntotal: {ok} / {total}")
sys.exit(0 if ok == total else 1)
