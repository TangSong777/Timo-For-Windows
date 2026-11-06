"""把 ZIP / 文件夹拖到主窗口即可导入。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtCore import QMimeData, QPoint, QUrl, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QApplication

from timodesk.exporter import export_zip
from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

for d in ("worklib_drop_src", "worklib_drop"):
    shutil.rmtree(d, ignore_errors=True)

src = Library("worklib_drop_src").load()
t = src.add_topic("拖拽")
src.add_note(t.id, "note", content="拖进来的笔记")
src.add_note(t.id, "note", content="第二条")
src.save()
zip_path, _ = export_zip(src, "worklib_drop_src/out.zip")

lib = Library("worklib_drop").load()
win = MainWindow(lib)
win.show()

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


def mime_for(path):
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(str(path))])
    return md


# 1. 可拖拽判定
check("zip 可拖", win._droppable(str(zip_path)))
check("目录可拖", win._droppable("worklib_drop_src"))
check("txt 不可拖", not win._droppable("timodesk/app.py"))

# 2. dragEnter 接受 zip
md1 = mime_for(zip_path)
ev = QDragEnterEvent(QPoint(40, 40), Qt.CopyAction, md1, Qt.LeftButton, Qt.NoModifier)
QApplication.sendEvent(win, ev)
check("zip 被接受", ev.isAccepted())

# 3. 非 zip 不接受
md2 = mime_for("timodesk/app.py")
ev2 = QDragEnterEvent(QPoint(40, 40), Qt.CopyAction, md2, Qt.LeftButton, Qt.NoModifier)
QApplication.sendEvent(win, ev2)
check("普通文件不被接受", not ev2.isAccepted())

# 4. drop 触发导入（拦截 _do_import 避免弹窗）
called = {}
win._do_import = lambda p: called.setdefault("path", p)
md3 = mime_for(zip_path)
ev3 = QDropEvent(QPoint(40, 40), Qt.CopyAction, md3, Qt.LeftButton, Qt.NoModifier)
QApplication.sendEvent(win, ev3)
check("drop 触发导入", called.get("path") and called["path"].endswith("out.zip"))

# 5. 真正导入一次验证数据
win._do_import = lambda p: called.setdefault("real", p)
from timodesk.importer import import_export

r = import_export(zip_path, lib, mode="replace")
win.refresh_topics()
win._reload_notes()
check("导入 2 条", r.notes == 2 and len(lib.notes) == 2)
check("界面列表已刷新", win.note_list.count() == 2)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
