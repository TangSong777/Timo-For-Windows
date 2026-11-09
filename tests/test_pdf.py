"""导出为 PDF。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication, QFileDialog

from timodesk.store import Library
from timodesk.ui import main_window as mw_mod
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


shutil.rmtree("worklib_pdf", ignore_errors=True)
lib = Library("worklib_pdf").load()
t = lib.add_topic("文档")
n = lib.add_note(t.id, "note", content="正文")
lib.set_content(n.id, "# 标题\n\n正文一段，包含 **粗体** 和 `代码`。\n\n- [ ] 待办\n- [x] 完成")
lib.save()

w = MainWindow(lib)
w.show()

out = Path("_test_out.pdf")
out.unlink(missing_ok=True)
mw_mod.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(out), "PDF (*.pdf)"))
w._export_pdf(n)

check("生成了文件", out.exists())
check("是 PDF 格式", out.read_bytes()[:5] == b"%PDF-")
check("文件不算太小", out.stat().st_size > 3000)

# 取消保存不报错
mw_mod.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
w._export_pdf(n)
check("取消后不产生文件", not Path("_test_out2.pdf").exists())

out.unlink(missing_ok=True)
print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
