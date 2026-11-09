# -*- coding: utf-8 -*-
"""主题锁定：防手滑改名/删除。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_lt")
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
t = lib.add_topic("锁住的主题")
lib.add_note(t.id, "note")
lib.save()
check("默认不锁", t.locked is False)

w = MainWindow(lib)
topic = w.lib.topics[t.id]
w.toggle_topic_lock(topic)
check("锁定生效", topic.locked is True)
check("落盘", Library(ROOT).load().topics[t.id].locked is True)
check("侧栏仍显示该主题", w.topic_list.count() == 1)

w.toggle_topic_lock(topic)
check("解除锁定", topic.locked is False)
check("解除也落盘", Library(ROOT).load().topics[t.id].locked is False)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
