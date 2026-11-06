# -*- coding: utf-8 -*-
"""图库笔记在列表卡片里显示封面缩略图。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.widgets import NoteCardDelegate

ROOT = Path("worklib_ct")
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
t = lib.add_topic("主题")

# 造一张真图片
img = ROOT / "a.png"
pm = QPixmap(120, 80)
pm.fill(Qt.red)
pm.save(str(img), "PNG")
rel = lib.import_attachment(str(img))

g = lib.add_note(t.id, "gallery")
g.images = [rel]
lib.update_note(g)
n = lib.add_note(t.id, "note")
lib.set_content(n.id, "普通笔记")
lib.save()

d = NoteCardDelegate(lib)
cover = d._cover(g)
check("图库有封面", cover is not None and not cover.isNull())
check("封面 54x54", cover.width() == 54 and cover.height() == 54)
again = d._cover(g)
check("第二次命中缓存", again is cover)
check("普通笔记没有封面", d._cover(n) is None)

empty = lib.add_note(t.id, "gallery")
lib.save()
check("空图库没有封面", d._cover(empty) is None)

g.images = ["attachments/not-exists.png"]
lib.update_note(g)
check("缺图不抛异常", d._cover(g) is None)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
