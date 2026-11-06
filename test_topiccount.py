# -*- coding: utf-8 -*-
"""侧栏主题计数：归档主题要数它自己的归档笔记。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_tc")
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
a = lib.add_topic("正常主题")
lib.add_note(a.id, "note")
lib.add_note(a.id, "note")

b = lib.add_topic("归档主题")
n1 = lib.add_note(b.id, "note")
n2 = lib.add_note(b.id, "note")
lib.archive_note(n1.id)
lib.archive_note(n2.id)
b.state = "archived"
lib.save()

check("active 计数", lib.note_counts("active").get(a.id) == 2)
check("archived 计数", lib.note_counts("archived").get(b.id) == 2)
check("默认仍数 active", lib.note_counts().get(b.id, 0) == 0)

w = MainWindow(lib)
d = w.topic_list.itemDelegate()
check("delegate 拿到计数", d.counts.get(a.id) == 2 and d.counts.get(b.id) == 2)

# tooltip 与列表项一致
tips = []
for i in range(w.topic_list.count()):
    it = w.topic_list.item(i)
    tips.append(it.toolTip())
check("归档主题 tooltip 有条数", any("归档主题 · 2 条" in t for t in tips))

# 归档一条正常主题的笔记后，计数应下降
w.lib.archive_note(w.lib.sorted_notes("active", a.id)[0].id)
w.lib.save()
w.refresh_topics()
check("归档后计数下降", w.topic_list.itemDelegate().counts.get(a.id) == 1)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
