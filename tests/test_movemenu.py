# -*- coding: utf-8 -*-
"""右键「移动到主题」要能看到归档主题（拖拽本来就能拖进去）。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_mm")
shutil.rmtree(ROOT, ignore_errors=True)
app = QApplication.instance() or QApplication(sys.argv)

ok = 0
fail = 0


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
b = lib.add_topic("老主题")
b.state = "archived"
c = lib.add_topic("删掉的主题")
c.state = "trash"
n = lib.add_note(a.id, "note", title="笔记")
lib.save()

w = MainWindow(lib)
targets = w._move_targets()
ids = [t.id for t in targets]
check("包含正常主题", a.id in ids)
check("包含归档主题", b.id in ids)
check("不含回收站主题", c.id not in ids)
check("归档主题带标注", "（已归档）" in w._move_label(b))
check("正常主题无标注", w._move_label(a) == "正常主题")
w.close()

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
