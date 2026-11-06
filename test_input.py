#!/usr/bin/env python
"""新建/重命名主题用的是自绘对话框，不是系统 QInputDialog。"""
import sys

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication, QLabel

from timodesk.ui.dialogs import InputDialog

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


dlg = InputDialog(None, "新建主题", "主题名称", placeholder="比如：日记")
check("初始 value 为空", dlg.value is None)
title = dlg._bar.findChild(QLabel, "DialogTitle")
check("标题显示", title is not None and title.text() == "新建主题")
check("占位文字", dlg.edit.placeholderText() == "比如：日记")

dlg.edit.setText("读书笔记")
dlg._ok()
check("确定后 value", dlg.value == "读书笔记")
check("对话框已关闭", not dlg.isVisible())

d2 = InputDialog(None, "重命名主题", "主题名称", text="旧名字")
check("预填", d2.edit.text() == "旧名字")
d2.edit.setText("   ")
d2._ok()
check("空白不提交", d2.value is None)
check("空白时不接受对话框", d2.result() == 0)

d3 = InputDialog(None, "新建主题", "主题名称")
d3.edit.setText("回车提交")
d3.edit.returnPressed.emit()
check("回车提交", d3.value == "回车提交")

d4 = InputDialog(None, "新建主题", "主题名称")
d4.edit.setText("要取消")
d4.reject()
check("取消不写值", d4.value is None)

# --- 主窗口接线：新建主题 / 空库直接新建笔记 ---
import shutil
from pathlib import Path as _P

import timodesk.ui.dialogs as D
from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

root = _P("worklib_input")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
w = MainWindow(lib)


class _FakeInput:
    def __init__(self, *a, **k):
        self.value = "自动主题"

    def exec_(self):
        return 1


D.InputDialog = _FakeInput
w.new_topic()
check("new_topic 用了对话框结果", [t.name for t in lib.topics.values()] == ["自动主题"])

# 空库（无主题）时新建笔记：走 new_topic 兜底
root2 = _P("worklib_input2")
shutil.rmtree(root2, ignore_errors=True)
lib2 = Library(root2).load()
w2 = MainWindow(lib2)
D.InputDialog = _FakeInput
w2.new_note("note")
check("空库新建主题", len(lib2.topics) == 1)
check("空库新建笔记", len(lib2.notes) == 1)

src = open("timodesk/ui/main_window.py", encoding="utf-8").read()
check("主窗口不再用 QInputDialog", "QInputDialog" not in src)
check("主窗口用 InputDialog", "InputDialog(" in src)

print(f"\ntotal: {ok} / {total}")
sys.exit(0 if ok == total else 1)
