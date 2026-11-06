"""编辑器查找条与格式快捷键。"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.editor import NoteEditor
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())
import shutil

root = Path("worklib_find")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t = lib.add_topic("查找")
text = "# 标题\n\n这是第一行 alpha 内容。\n第二行 beta 内容，alpha 又出现一次。\n第三行。\n"
n = lib.add_note(t.id, "article", content=text, title="查找测试")
lib.save()

ed = NoteEditor(lib)
ed.show()
ed.set_note(lib.notes[n.id])

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. 默认隐藏
check("查找条默认隐藏", not ed.find_bar.isVisible())

# 2. 打开
ed.show_find()
app.processEvents()
check("打开后可见", ed.find_bar.isVisible())

# 3. 搜索词计数
ed.find_edit.setText("alpha")
app.processEvents()
check("计数显示 2 处", ed.find_count.text() == "2 处")
check("已选中第一处", "alpha" in ed.edit.textCursor().selectedText())

# 4. 下一个
ed._find_step(forward=True)
app.processEvents()
check("下一处仍选中 alpha", "alpha" in ed.edit.textCursor().selectedText())

# 5. 无匹配
ed.find_edit.setText("不存在的词xyz")
app.processEvents()
check("无匹配提示", ed.find_count.text() == "无匹配")

# 6. Esc 关闭
ed.find_edit.setText("alpha")
QTest.keyClick(ed.find_edit, Qt.Key_Escape)
app.processEvents()
check("Esc 关闭查找条", not ed.find_bar.isVisible())

# 7. Ctrl+B 加粗
ed.edit.setPlainText("你好世界")
ed.edit.selectAll()
ed.edit.setFocus()
QTest.keyClick(ed.edit, Qt.Key_B, Qt.ControlModifier)
app.processEvents()
check("Ctrl+B 包裹粗体", ed.edit.toPlainText() == "**你好世界**")

# 8. Ctrl+Shift+T 待办
ed.edit.setPlainText("买菜")
ed.edit.moveCursor(ed.edit.textCursor().Start)
ed.edit.setFocus()
QTest.keyClick(ed.edit, Qt.Key_T, Qt.ControlModifier | Qt.ShiftModifier)
app.processEvents()
check("Ctrl+Shift+T 加待办", ed.edit.toPlainText().startswith("- [ ] "))

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
