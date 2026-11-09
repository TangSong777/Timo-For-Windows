# -*- coding: utf-8 -*-
"""主题重名检查（回收站里的不算，重命名自己不算）。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_tn")
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
a = lib.add_topic("日记")
b = lib.add_topic("工作")
dead = lib.add_topic("删掉的")
lib.delete_topic(dead.id)
lib.save()

w = MainWindow(lib)
check("已有名字算占用", w._topic_name_taken("日记"))
check("新名字不占用", not w._topic_name_taken("读书"))
check("忽略首尾空格", w._topic_name_taken("  日记 "))
check("回收站里的不算", not w._topic_name_taken("删掉的"))
check("重命名自己不算占用", not w._topic_name_taken("日记", exclude_id=a.id))
check("重命名成别人仍占用", w._topic_name_taken("工作", exclude_id=a.id))

# 直接改库（UI 层已拦，这里只确认数据层不会拦，避免以后误判）
lib.rename_topic(a.id, "日常")
check("改名生效", lib.topics[a.id].name == "日常")

w.close()
print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
