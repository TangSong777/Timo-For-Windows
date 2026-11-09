# -*- coding: utf-8 -*-
"""搜索时列表卡片把命中词刷出来。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import C
from timodesk.ui.widgets import NoteCardDelegate, _draw_line

ROOT = Path("worklib_ch")
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
n = lib.add_note(t.id, "note")
lib.set_content(n.id, "今天看到一只孤独的猫\n\n希望它能找到家")
lib.save()

w = MainWindow(lib)
d = w.note_list.itemDelegate()
check("delegate 有 term", hasattr(d, "term"))
check("初始 term 为空", d.term == "")

w.search.setText("孤独")
w._apply_search()
check("搜索后 term 同步", d.term == "孤独")

# 命中词的宽度计算：能画出来就说明分段逻辑没崩
pm = QPixmap(400, 100)
pm.fill()
p = QPainter(pm)
f = QFont(app.font())
f.setPixelSize(12)
fm = QFontMetrics(f)
p.setFont(f)
_draw_line(p, w.note_list.viewport().rect().adjusted(0, 0, 260, 0), "今天看到一只孤独的猫", "孤独", fm)
p.end()
check("命中行能绘制", not pm.isNull())

# 逐段宽度应当等于整行宽度（不多不少）
line = "今天看到一只孤独的猫"
i = line.find("孤独")
segs = (line[:i], line[i:i + 2], line[i + 2:])
check("分段宽度自洽", abs(sum(fm.width(s) for s in segs) - fm.width(line)) <= 1)

w._clear_search()
w._reload_notes()
check("清空搜索后 term 复位", d.term == "")

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
