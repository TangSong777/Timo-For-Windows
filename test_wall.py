"""图片墙：拖入文件、Ctrl+V 粘贴、Delete 删除。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtGui import QColor, QImage
from PyQt5.QtWidgets import QApplication

from timodesk.render import render
from timodesk.store import Library
from timodesk.ui.editor import ImageWall
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


shutil.rmtree("worklib_wall", ignore_errors=True)
base = Path("worklib_wall")
lib = Library(str(base)).load()
t = lib.add_topic("图")
g = lib.add_note(t.id, "gallery")
lib.save()

# 造两张图
srcs = []
for i, color in enumerate([(230, 120, 120), (120, 160, 230)]):
    p = Path(f"_tmp_wall_{i}.png")
    img = QImage(80 + i * 20, 60, QImage.Format_RGB32)
    img.fill(QColor(*color))
    img.save(str(p))
    srcs.append(str(p))

from timodesk.ui.editor import NoteEditor

ed = NoteEditor(lib)
ed.resize(900, 700)
ed.show()
ed.set_note(g)
app.processEvents()

check("墙是 ImageWall", isinstance(ed.wall, ImageWall))
check("初始没有图片", len(g.images) == 0)

# 拖入
ed._add_images_from_files(srcs)
app.processEvents()
check("拖入后两张", len(g.images) == 2)
check("墙显示两张", ed.wall.count() == 2)
check("顺序与拖入一致", len(g.images) == 2)

# 粘贴
img = QImage(100, 100, QImage.Format_RGB32)
img.fill(QColor(80, 80, 80))
app.clipboard().setImage(img)
ed._paste_wall_image()
app.processEvents()
check("粘贴后三张", len(g.images) == 3)
check("粘贴的图存在", lib.attachment_abspath(g.images[-1]).exists())

# 删除第一张
ed.wall.item(0).setSelected(True)
first = g.images[0]
ed._remove_selected_images()
app.processEvents()
check("删除后剩两张", len(g.images) == 2)
check("删的是第一张", first not in g.images)
check("墙上也少一张", ed.wall.count() == 2)

# 重载后仍在
lib2 = Library(str(base)).load()
check("重载仍是两张", len(lib2.notes[g.id].images) == 2)

# 空剪贴板
app.clipboard().clear()
before = len(g.images)
ed._paste_wall_image()
app.processEvents()
check("空剪贴板不增图", len(g.images) == before)

for p in srcs:
    Path(p).unlink(missing_ok=True)
for p in base.glob("attachments/*"):
    p.unlink(missing_ok=True)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
