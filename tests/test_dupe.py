# -*- coding: utf-8 -*-
"""去重：找正文相同的笔记、批量移到回收站。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.dialogs import DuplicatesDialog

ROOT = Path("worklib_dupe")
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
t2 = lib.add_topic("另一个")

a = lib.add_note(t.id, "note", "重复的内容\n第二行", None)
b = lib.add_note(t2.id, "note", "重复的内容\n第二行", None)
c = lib.add_note(t.id, "note", "重复的内容\n\n\n第二行   ", None)  # 空白差异，算重复
d = lib.add_note(t.id, "note", "完全不同的内容", None)
e = lib.add_note(t.id, "note", "", None)  # 空正文不参与
f = lib.add_note(t.id, "note", "", None)  # 空正文不参与
g = lib.add_note(t.id, "note", "重复的内容\n第二行", None)
lib.delete_note(g.id)  # 回收站里的不参与
lib.save()

groups = lib.duplicate_groups()
check("找到 1 组重复", len(groups) == 1)
check("该组 3 条", len(groups[0]) == 3 if groups else False)
check("组内按创建时间升序", [n.id for n in groups[0]] == [a.id, b.id, c.id] if groups else False)
check("不同内容不重复", all(d.id not in [n.id for n in gr] for gr in groups))
check("空正文不参与", all(e.id not in [n.id for n in gr] and f.id not in [n.id for n in gr] for gr in groups))
check("回收站不参与", all(g.id not in [n.id for n in gr] for gr in groups))

# 对话框：默认勾选除每组第一条外的全部
dlg = DuplicatesDialog(None, lib, groups)
checks = [dlg.tree.topLevelItem(0).child(i).checkState(0) for i in range(dlg.tree.topLevelItem(0).childCount())]
check("对话框默认保留第一条", checks[0] == Qt.Unchecked and all(s == Qt.Checked for s in checks[1:]))
dlg._accept()
to_del = dlg.to_delete()
check("对话框拿到 2 条待删", len(to_del) == 2)
dlg.deleteLater()

n = lib.delete_notes(to_del)
lib.save()
check("批量删除返回 2", n == 2)
check("删除后不再有重复", len(lib.duplicate_groups()) == 0)
check("删掉的是后两条", to_del == [b.id, c.id])
check("第一条还在", lib.notes[a.id].state == "active")
check("被删的进了回收站", lib.notes[b.id].state == "trash" and lib.notes[c.id].state == "trash")

print(f"\ntotal: {ok} / {ok + fail}")
shutil.rmtree(ROOT, ignore_errors=True)
sys.exit(0 if fail == 0 else 1)
