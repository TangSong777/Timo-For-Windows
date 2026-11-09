"""列表排序：最近更新 / 最近创建 / 标题。"""
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library, parse_iso, to_iso
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

shutil.rmtree("worklib_sort", ignore_errors=True)
lib = Library("worklib_sort").load()
t = lib.add_topic("排序")
ids = {}
for name in ("丙", "甲", "乙"):
    n = lib.add_note(t.id, "note", content=f"{name}的正文")
    ids[name] = n.id
    time.sleep(0.02)
# 手动把 updated_at 打乱成 甲最新、乙居中、丙最旧；created_at 保持丙甲乙
lib.notes[ids["甲"]].updated_at = "2026-11-06T12:00:00.000Z"
lib.notes[ids["乙"]].updated_at = "2026-11-06T10:00:00.000Z"
lib.notes[ids["丙"]].updated_at = "2026-11-06T08:00:00.000Z"
lib.save()

win = MainWindow(lib)
win.select_nav("all")
ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


def titles():
    out = []
    for i in range(win.note_list.count()):
        nid = win.note_list.item(i).data(256)
        out.append(lib.notes[nid].display_title(lib.content(nid)))
    return out


check("默认按更新时间", titles() == ["甲的正文", "乙的正文", "丙的正文"])
win.set_sort("created")
check("按创建时间（新的在前）", titles() == ["乙的正文", "甲的正文", "丙的正文"])
win.set_sort("title")
check("按标题", titles() == ["丙的正文", "乙的正文", "甲的正文"])
check("菜单勾选跟随", [a.data() for a in win.sort_menu.actions() if a.isChecked()] == ["title"])
check("设置已保存", win.settings.get("sort_mode") == "title")

# 重开窗口保持
win2 = MainWindow(lib)
check("重开保持排序", win2.sort_mode == "title")
check("重开列表顺序", titles() == ["丙的正文", "乙的正文", "甲的正文"])

# 置顶仍在最前
lib.toggle_pin(ids["丙"])
win._reload_notes()
check("置顶优先", titles()[0] == "丙的正文")

# 主题视图也遵循
win.view = ("topic", t.id)
win._reload_notes()
check("主题内排序一致", titles() == ["丙的正文", "乙的正文", "甲的正文"])

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
