#!/usr/bin/env python
"""所有自绘对话框都能构造并显示（防止某个弹窗一打开就崩）。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui import dialogs as D
from timodesk.ui.theme import app_qss

app = QApplication([])
app.setStyleSheet(app_qss())
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


root = Path("worklib_dlg")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
tid = lib.add_topic("测试").id
n = lib.add_note(tid, "note", "正文", None)
lib.set_reminder(n.id, "2099-01-01T00:00:00Z")

cases = [
    ("消息框", lambda: D.MessageDialog(None, "标题", "正文内容", "好")),
    ("确认框", lambda: D.MessageDialog(None, "确认", "删除？", "删除", "取消")),
    ("进度框", lambda: D.ProgressDialog(None, "导入", "正在导入…")),
    ("提醒框(ISO)", lambda: D.ReminderDialog(None, n.remind_at)),
    ("提醒框(空)", lambda: D.ReminderDialog(None, None)),
    ("备份框", lambda: D.BackupDialog(None, lib)),
    ("导入模式框", lambda: D.ImportModeDialog(None, 1005)),
    ("关于框", lambda: D.AboutDialog(None, lib, "0.4.0")),
    ("输入框", lambda: D.InputDialog(None, "新建主题", "名称")),
]

for name, fn in cases:
    try:
        w = fn()
        w.show()
        app.processEvents()
        w.close()
        app.processEvents()
        check(name, True)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL {name}: {exc}")
        total += 1

# 对话框都继承自 FramelessDialog（无系统标题栏）
from timodesk.ui.title_bar import FramelessDialog

check("消息框是自绘", isinstance(D.MessageDialog(None, "t", "x"), FramelessDialog))
check("提醒框是自绘", isinstance(D.ReminderDialog(None, None), FramelessDialog))
check("关于框是自绘", isinstance(D.AboutDialog(None, lib, "0.4.0"), FramelessDialog))

print(f"\ntotal: {ok} / {total}")
sys.exit(0 if ok == total else 1)
