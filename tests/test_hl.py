"""搜索高亮：预览里用 ExtraSelection 刷底色。"""
import shutil
import sys

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


shutil.rmtree("worklib_hl", ignore_errors=True)
lib = Library("worklib_hl").load()
t = lib.add_topic("高亮")
n = lib.add_note(t.id, "note", content="今天拿到了奖学金。\n\n奖学金很好。\n\n- [ ] 领奖学金")
lib.save()

win = MainWindow(lib)
win.show()
win.editor.set_note(n)
win.search.setText("奖学金")
win._apply_search()
app.processEvents()

sels = win.editor.preview.extraSelections()
check("三处命中都选中", len(sels) == 3)
check("选中文本正确", all(s.cursor.selectedText() == "奖学金" for s in sels))
from timodesk.ui.theme import C
check("底色跟随主题", sels[0].format.background().color().name() == C["hl_bg"])
check("预览文本完整", "奖学金很好" in win.editor.preview.toPlainText())

win.editor.set_highlight("")
app.processEvents()
check("清除后没有选区", win.editor.preview.extraSelections() == [])

# 多词
win.editor.set_highlight("奖学金 领")
app.processEvents()
check("多词分别标记", len(win.editor.preview.extraSelections()) == 4)

# 搜索后自动选中第一条
win.search.setText("奖学金")
win._apply_search()
app.processEvents()
check("搜索后选中第一条", win.note_list.currentRow() == 0 and win.note_list.count() == 1)

# 标签/链接不被破坏
img = win.editor.preview.document().toHtml()
check("文档仍是 HTML", img.startswith("<!DOCTYPE HTML") or "<html" in img.lower())

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
