# -*- coding: utf-8 -*-
"""全部视图里新建笔记，落到上次用过的主题。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_lt_topic")
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
a = lib.add_topic("第一个")
b = lib.add_topic("常用")
lib.save()

w = MainWindow(lib)
w.view = ("all", None)
w.new_note("note")
first = w.lib.sorted_notes("active", a.id)
check("首次落到第一个主题", len(first) == 1)
check("记住 last_topic_id", w.settings.get("last_topic_id") == a.id)

# 去「常用」主题建一条，之后在全部视图新建应落到它
w.view = ("topic", b.id)
w.new_note("note")
check("主题内新建落到该主题", len(w.lib.sorted_notes("active", b.id)) == 1)
check("记录更新", w.settings.get("last_topic_id") == b.id)

w.view = ("all", None)
before = len(w.lib.sorted_notes("active", b.id))
w.new_note("note")
check("全部视图新建落到上次主题", len(w.lib.sorted_notes("active", b.id)) == before + 1)

# 上次主题被删掉后回退到第一个
w.lib.delete_topic(b.id)
w.lib.save()
w.view = ("all", None)
w.new_note("note")
check("主题删了也能新建", len([n for n in w.lib.notes.values() if n.state == "active"]) == 2)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
