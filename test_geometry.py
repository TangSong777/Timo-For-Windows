# -*- coding: utf-8 -*-
"""上次的窗口位置如果落在屏幕外（换显示器/拔外接屏），下次启动要捡回屏幕内。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.settings import Settings
from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_geo")
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
lib.add_note(t.id, "note", "内容", None)
lib.save()

w1 = MainWindow(lib)
w1.setGeometry(6000, 4000, 900, 600)   # 假想的外接屏坐标
w1.close()
geo = Settings(ROOT).get("window_geometry", "")
check("离屏几何已存下", bool(geo))

w2 = MainWindow(lib)
w2.show()
app.processEvents()
check("启动后能落在某块屏幕上", w2._on_screen())
check("尺寸被拉回默认", w2.width() <= 1400 and w2.height() <= 900)

# 正常几何应该原样恢复
w2.setGeometry(100, 100, 1000, 700)
w2.close()
w3 = MainWindow(lib)
w3.show()
app.processEvents()
check("正常几何原样恢复", abs(w3.width() - 1000) <= 4 and abs(w3.height() - 700) <= 4)
check("位置也在屏内", w3._on_screen())

for w in (w1, w2, w3):
    w.close()
print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
