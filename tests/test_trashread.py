# -*- coding: utf-8 -*-
"""回收站里的笔记只读，恢复后才能编辑。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.editor import NoteEditor

ROOT = Path("worklib_tr")
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
n1 = lib.add_note(t.id, "note", "正常笔记", None)
n2 = lib.add_note(t.id, "article", "回收站笔记正文", "回收站笔记")
lib.delete_note(n2.id)
n3 = lib.add_note(t.id, "note", "归档笔记", None)
lib.archive_note(n3.id)
lib.save()

ed = NoteEditor(lib)

ed.set_note(lib.notes[n1.id])
check("正常笔记可编辑", not ed.edit.isReadOnly())

ed.set_note(lib.notes[n3.id])
check("归档笔记可编辑", not ed.edit.isReadOnly())

ed.set_note(lib.notes[n2.id])
check("回收站正文只读", ed.edit.isReadOnly())
check("回收站标题只读", ed.title_edit.isReadOnly())
check("状态提示只读", "只读" in ed.save_state.text())

# 恢复正常后重新打开 → 可编辑
lib.restore_note(n2.id)
lib.save()
ed.set_note(lib.notes[n2.id])
check("恢复后可编辑", not ed.edit.isReadOnly())
check("状态提示清空", ed.save_state.text() == "")

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
