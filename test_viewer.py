"""大图查看器：适应窗口、滚轮缩放、切换。"""
import sys

sys.path.insert(0, ".")
from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QApplication

from timodesk.ui.editor import ImageViewer
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


def wheel(dy=120):
    return QWheelEvent(
        QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, dy),
        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
    )


v = ImageViewer(["assets/timo-icon.png", "assets/timo-icon.png"], 0)
v.resize(900, 640)
v.show()
app.processEvents()

check("适应窗口不放大", v.label.pixmap().width() <= 192)
check("计数正确", v.counter.text().startswith("1 / 2"))

v.wheelEvent(wheel(120))
check("滚轮放大", v.zoom > 1.0)
check("放大后不再适应", v.label.pixmap().width() > 192)

v.wheelEvent(wheel(-120))
check("滚轮缩小回到适应", v.zoom <= 0 or v.zoom < 1.25)

v.mouseDoubleClickEvent(wheel())
check("双击回到适应", v.zoom <= 0)
v.mouseDoubleClickEvent(wheel())
check("再双击切到 100%", abs(v.zoom - 1.0) < 1e-6)

v._step(1)
check("切到第二张", v.idx == 1)
v._step(1)
check("循环回第一张", v.idx == 0)

bad = ImageViewer(["_not_a_file.png"], 0)
bad.show()
app.processEvents()
check("坏图不崩", bad.counter.text().startswith("1 / 1"))

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
