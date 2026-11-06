"""窗口尺寸记忆。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())
root = Path("worklib_win")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t = lib.add_topic("窗口")
lib.add_note(t.id, "note", content="hi")
lib.save()

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


check("初始没有记录", lib.root.joinpath("settings.json").exists() is False)

w1 = MainWindow(lib)
w1.resize(1120, 720)
w1.move(90, 60)
w1._save_geometry()
check("settings.json 已写", lib.root.joinpath("settings.json").exists())
raw = lib.root.joinpath("settings.json").read_text(encoding="utf-8")
check("含 window_geometry", "window_geometry" in raw)

w2 = MainWindow(lib)
check("恢复宽度", w2.width() == 1120)
check("恢复高度", w2.height() == 720)
check("位置也恢复", (w2.x(), w2.y()) == (90, 60))

# 关闭时自动保存
w2.resize(1000, 640)
w2._quitting = True
w2.close()
w3 = MainWindow(lib)
check("关闭后自动保存尺寸", (w3.width(), w3.height()) == (1000, 640))

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
