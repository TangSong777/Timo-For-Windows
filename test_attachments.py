# -*- coding: utf-8 -*-
"""清理未被引用的附件。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library

ROOT = Path("worklib_at")
shutil.rmtree(ROOT, ignore_errors=True)
app = QApplication.instance() or QApplication(sys.argv)

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


lib = Library(ROOT).load()
t = lib.add_topic("主题")

p1 = ROOT / "used.png"; p1.write_bytes(b"a" * 10)
p2 = ROOT / "orphan.png"; p2.write_bytes(b"b" * 20)
p3 = ROOT / "gallery.png"; p3.write_bytes(b"c" * 30)
rel1 = lib.import_attachment(str(p1))
rel2 = lib.import_attachment(str(p2))
rel3 = lib.import_attachment(str(p3))

n = lib.add_note(t.id, "note")
lib.set_content(n.id, f"![](  {rel1}  )\n")
g = lib.add_note(t.id, "gallery")
g.images = [rel3]
lib.update_note(g)
lib.save()

unused = lib.unused_attachments()
check("只认出一个孤立附件", len(unused) == 1)
check("孤立的是 orphan", unused[0].endswith("orphan.png"))
check("正文引用的不算", not any(x.endswith("used.png") for x in unused))
check("图库引用的不算", not any(x.endswith("gallery.png") for x in unused))

n2 = lib.add_note(t.id, "note")
lib.set_content(n2.id, f"<img src=\"{rel2}\">\n")
lib.save()
check("HTML 里的引用也算", lib.unused_attachments() == [])

lib.set_content(n2.id, "删掉图片\n")
lib.save()
unused2 = lib.unused_attachments()
check("删掉引用后又变成孤立", len(unused2) == 1)

removed = lib.purge_attachments(unused2)
check("删除返回数量", removed == 1)
left = [p.name for p in lib.attachments_dir.iterdir()]
check("目录只剩 2 个", len(left) == 2)
check("孤立文件没了", not any("orphan" in x for x in left))
check("再查为空", lib.unused_attachments() == [])

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
