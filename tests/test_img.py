"""图库图片的复制与另存为。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss
from PIL import Image

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

shutil.rmtree("worklib_img", ignore_errors=True)
lib = Library("worklib_img").load()
t = lib.add_topic("图")
src = Path("worklib_img/real.png")
Image.new("RGB", (40, 30), (30, 30, 30)).save(src)
rel = lib.import_attachment(src)
g = lib.add_note(t.id, "gallery", "")
g.images = [rel]
lib.save()

win = MainWindow(lib)
win.editor.set_note(g)
ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


wall = win.editor.wall
check("图片墙有 1 张", wall.count() == 1)
item = wall.item(0)
check("item 拿到绝对路径", Path(item.data(256)).exists())

# 复制图片
win.editor._copy_image(item)
img = QApplication.clipboard().image()
check("剪贴板有图", not img.isNull() and img.width() == 40)

# 另存为（直接走 shutil 分支，绕过对话框）
dst = Path("worklib_img/saved.png")
shutil.copy2(item.data(256), dst)
check("另存文件存在", dst.exists() and dst.stat().st_size > 0)
check("另存内容一致", dst.read_bytes() == Path(item.data(256)).read_bytes())

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
