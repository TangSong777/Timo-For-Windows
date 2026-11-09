"""拖入 .md / .txt 文件 → 新建笔记。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

app = QApplication(sys.argv)
root = Path("worklib_dragtext")
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t = lib.add_topic("导入测试")
lib.save()

w = MainWindow(lib)
w.resize(1280, 830)
w.show()
app.processEvents()

ok = 0
total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


tmp = Path("tmp_dragtext")
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir()

md = tmp / "会议记录.md"
md.write_text("# 周会纪要\n\n- 事项一\n- 事项二\n", encoding="utf-8")
w.view = ("topic", t.id)
w._import_text_file(str(md))
app.processEvents()

titles = [n.display_title(lib.content(n.id)) for n in lib.notes.values()]
check("新建了一条笔记", len(lib.notes) == 1)
check("标题取自 # 行", titles[0] == "周会纪要")
check("类型是文章", next(iter(lib.notes.values())).type == "article")
nid = next(iter(lib.notes))
check("正文不含标题行", "周会纪要" not in lib.content(nid))
check("正文保留了列表", "事项一" in lib.content(nid))
check("落进了当前主题", next(iter(lib.notes.values())).topic_id == t.id)
check("已落盘", len(Library(root).load().notes) == 1)

txt = tmp / "随手记.txt"
txt.write_text("没有标题的纯文本\n第二行", encoding="utf-8")
w._import_text_file(str(txt))
app.processEvents()
check("第二篇用文件名作标题", any(n.title == "随手记" for n in lib.notes.values()))
check("两篇都在", len(lib.notes) == 2)

gbk = tmp / "gbk.txt"
gbk.write_bytes("国标编码的文本".encode("gbk"))
w._import_text_file(str(gbk))
app.processEvents()
check("GBK 也能读", any("国标编码" in lib.content(n.id) for n in lib.notes.values()))

check("_droppable 认 md", MainWindow._droppable(str(md)))
check("_droppable 认 txt", MainWindow._droppable(str(txt)))
check("_droppable 仍认 zip", MainWindow._droppable("x.zip"))
check("_droppable 不认 exe", not MainWindow._droppable("x.exe"))

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
