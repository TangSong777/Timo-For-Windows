# -*- coding: utf-8 -*-
"""写盘失败时不应崩，要提示且状态变「未保存」。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_sf")
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
t = lib.add_topic("测试")
n = lib.add_note(t.id, "note")
lib.set_content(n.id, "初始")
lib.save()
w = MainWindow(lib)
w.editor.set_note(lib.notes[n.id])

w._pending_save = (n.id, "改过的内容", None)
w.lib.save = lambda: (_ for _ in ()).throw(OSError("disk full"))
w._flush_save()
check("不崩", True)
check("状态是未保存", w.editor.save_state.text() == "未保存")
check("内存里是新内容", lib.content(n.id) == "改过的内容")
check("只提示一次", w._save_error_shown is True)

# 恢复正常后应能再保存
w._pending_save = (n.id, "恢复后的内容", None)
w.lib.save = lambda: None
w._flush_save()
check("恢复后状态已保存", w.editor.save_state.text() == "已保存")

w.close()
print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
