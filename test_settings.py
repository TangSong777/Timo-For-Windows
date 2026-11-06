# -*- coding: utf-8 -*-
"""偏好设置对话框：读初值、写入、排序联动。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.settings import Settings
from timodesk.store import Library
from timodesk.ui.dialogs import SettingsDialog
from timodesk.ui.main_window import MainWindow

ROOT = Path("worklib_set")
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
st = Settings(ROOT)

dlg = SettingsDialog(None, st, "dark", "title")
check("继承无边框对话框", type(dlg).__mro__[1].__name__ == "FramelessDialog")
check("读取外观初值", dlg.cmb_theme.currentData() == "dark")
check("读取排序初值", dlg.cmb_sort.currentData() == "title")
check("回收站默认 0", dlg.spin_trash.value() == 0)

dlg.spin_trash.setValue(45)
dlg.cmb_theme.setCurrentIndex(dlg.cmb_theme.findData("light"))
dlg.cmb_sort.setCurrentIndex(dlg.cmb_sort.findData("created"))
dlg.apply()
check("写入回收站天数", st.get("trash_days") == 45)
check("写入外观", st.get("theme_mode") == "light")
check("写入排序", st.get("sort_mode") == "created")
check("标记主题变更", dlg.theme_changed is True)

st.set("theme_mode", "light")
dlg2 = SettingsDialog(None, st, "light", "created")
dlg2.cmb_theme.setCurrentIndex(dlg2.cmb_theme.findData("light"))
check("没改主题不算变更", dlg2.theme_changed is False)

w = MainWindow(lib)
w.settings.set("sort_mode", "updated")
check("主窗口能打开设置", hasattr(w, "open_settings"))

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
