"""预览里的待办方框点击后要能回写正文。"""
import io, os, shutil, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("PASS", name)
    else:
        fail += 1
        print("FAIL", name, extra)

def main():
    app = QApplication(sys.argv)
    root = tempfile.mkdtemp(prefix="timo-todo-")
    try:
        lib = Library(root)
        lib.load()
        t = lib.add_topic("杂事")
        n = lib.add_note(t.id, "note", content="- [ ] 买牛奶\n- [x] 喂猫\n\n普通段落")
        lib.save()
        w = MainWindow(lib)
        w.resize(1280, 830)
        w.show()
        w.editor.set_note(lib.notes[n.id])
        app.processEvents()

        body = w.editor.edit.toPlainText()
        check("初始正文", "[ ] 买牛奶" in body and "[x] 喂猫" in body, body)

        w.editor._toggle_todo(0)
        app.processEvents()
        body = w.editor.edit.toPlainText()
        check("第一行已勾选", body.split("\n")[0] == "- [x] 买牛奶", body.split("\n")[0])

        w.editor._toggle_todo(1)
        app.processEvents()
        body = w.editor.edit.toPlainText()
        check("第二行取消勾选", body.split("\n")[1] == "- [ ] 喂猫", body.split("\n")[1])

        # 点击回写后要能存进文件
        w.save_now()
        app.processEvents()
        saved = io.open(os.path.join(root, "notes", n.id + ".md"), encoding="utf-8").read()
        check("已写入文件", "- [x] 买牛奶" in saved and "- [ ] 喂猫" in saved, saved[:60])

        # 模拟预览里点方框（信号通路）
        w.editor._toggle_todo(1)
        app.processEvents()
        from PyQt5.QtCore import QUrl
        w.editor.preview.anchorClicked.emit(QUrl("todo:1"))
        app.processEvents()
        check("点方框回调生效", w.editor.edit.toPlainText().split("\n")[1] == "- [ ] 喂猫", w.editor.edit.toPlainText().split("\n")[1])

        # 预览 HTML 里方框是链接
        html = w.editor.preview.toHtml()
        check("预览里有 todo 链接", "todo:" in html or "☐" in html, html[:80])

        w.close()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"\ntotal: {ok} / {ok + fail}")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
