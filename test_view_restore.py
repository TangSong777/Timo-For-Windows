"""打开时恢复上次的视图与笔记。"""
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


shutil.rmtree("worklib_view", ignore_errors=True)
lib = Library("worklib_view").load()
t1 = lib.add_topic("工作")
t2 = lib.add_topic("生活")
n1 = lib.add_note(t1.id, "note", content="周一")
lib.set_content(n1.id, "周一的会议")
n2 = lib.add_note(t2.id, "note", content="买菜")
lib.set_content(n2.id, "买菜和做饭")
lib.save()

# 第一次：停在「生活」主题、选中「买菜」
w1 = MainWindow(lib)
w1.show()
app.processEvents()
for i in range(w1.topic_list.count()):
    if w1.topic_list.item(i).data(0x0100).name == "生活":
        w1.topic_list.setCurrentRow(i)
        break
app.processEvents()
w1.note_list.setCurrentRow(0)
app.processEvents()
check("第一次选中生活", w1.view[0] == "topic" and w1.view[1] == t2.id)
check("第一次选中买菜", w1.editor.note is not None and w1.editor.note.id == n2.id)
w1._save_view()
w1.hide()

# 第二次：新窗口应回到生活 + 买菜
w2 = MainWindow(lib)
w2.show()
app.processEvents()
check("恢复主题", w2.view == ("topic", t2.id))
check("恢复笔记", w2.editor.note is not None and w2.editor.note.id == n2.id)

# 切到归档视图后再开
w2.select_nav("archived")
app.processEvents()
w2._save_view()
w3 = MainWindow(lib)
check("恢复归档视图", w3.view[0] == "archived")

# 主题被删 → 回退全部
w3.view = ("topic", "不存在的主题")
w3._save_view()
w4 = MainWindow(lib)
check("主题没了回退全部", w4.view[0] == "all")

# last_note 不存在 → 不崩
lib.settings_dummy = None
w4.settings.set("last_note", "no-such-note")
w5 = MainWindow(lib)
check("笔记不存在也不崩", w5.editor.note is None)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
