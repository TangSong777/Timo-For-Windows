#!/usr/bin/env python
"""图片墙拖动排序：顺序写回笔记，且 QListWidgetItem 里的路径不能丢。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
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


root = Path("worklib_wallorder")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
tid = lib.add_topic("图库测试").id
note = lib.add_note(tid, "gallery", "", None)

tmp = Path("tmp_wall"); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
rels = []
for i, name in enumerate(("a", "b", "c")):
    f = tmp / f"{name}.png"
    pm = QPixmap(60, 60)
    pm.fill([Qt.black, Qt.gray, Qt.lightGray][i])
    pm.save(str(f))
    rels.append(lib.import_attachment(f))
note.images = list(rels)
lib.save()

w = MainWindow(lib)
w._reload_notes(select_id=note.id)
app.processEvents()

wall = w.editor.wall
check("图片墙条目数", wall.count() == 3)
check("条目带路径", all(wall.item(i).data(Qt.UserRole) for i in range(3)))

# 把第一张拖到末尾空白
wall._drag_row = 0
wall._move_row(FakeEvent(wall.viewport().rect().bottomLeft()))
check("界面顺序变化", [wall.item(i).data(Qt.UserRole) for i in range(3)] ==
      [str(lib.attachment_abspath(rels[1])), str(lib.attachment_abspath(rels[2])), str(lib.attachment_abspath(rels[0]))])
check("拖动后路径未丢", all(wall.item(i).data(Qt.UserRole) for i in range(3)))

reloaded = Library(root).load()
check("顺序已写回笔记", reloaded.notes[note.id].images == [rels[1], rels[2], rels[0]])

# 重开窗口顺序一致
w2 = MainWindow(reloaded)
w2._reload_notes(select_id=note.id)
app.processEvents()
order2 = [w2.editor.wall.item(i).data(Qt.UserRole) for i in range(3)]
check("重开后顺序一致", order2[0] == str(lib.attachment_abspath(rels[1])))

print(f"\ntotal: {ok} / {total}")
sys.exit(0 if ok == total else 1)
