# -*- coding: utf-8 -*-
"""Markdown 文件夹导出：反复导出到同一目录时，图片引用要跟着实际文件名走。"""
import re
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.exporter import export_markdown_tree
from timodesk.store import Library

ROOT = Path("worklib_mc")
OUT = Path("worklib_mc_out")
shutil.rmtree(ROOT, ignore_errors=True)
shutil.rmtree(OUT, ignore_errors=True)
app = QApplication.instance() or QApplication(sys.argv)

ok = 0
fail = 0


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
png = ROOT / "pic.png"
png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
rel = lib.import_attachment(str(png))
n = lib.add_note(t.id, "note", title="带图")
lib.set_content(n.id, f"看这张图\n\n![]({rel})\n")
lib.save()

c1 = export_markdown_tree(lib, OUT)
md1 = next(OUT.glob("主题/*.md")).read_text(encoding="utf-8")
refs1 = re.findall(r"\]\(\.\./(attachments/[^)\s]+)\)", md1)
check("第一次导出有图片引用", len(refs1) == 1)
check("第一次引用文件存在", (OUT / refs1[0]).exists())
check("第一次复制了 1 张", c1["attachments"] == 1)

# 再导一次到同一目录：同名文件已存在，应该改成 -2 并同步改正文
c2 = export_markdown_tree(lib, OUT)
md2 = next(OUT.glob("主题/*.md")).read_text(encoding="utf-8")
refs2 = re.findall(r"\]\(\.\./(attachments/[^)\s]+)\)", md2)
check("第二次导出仍有引用", len(refs2) == 1)
check("第二次引用文件存在", (OUT / refs2[0]).exists())
check("第二次换了文件名", refs2[0] != refs1[0])
check("第二次复制了 1 张", c2["attachments"] == 1)
check("旧文件还在", (OUT / refs1[0]).exists())

# 引用一张根本不存在的图：保留引用，但计入 missing 并在 README 说明
n2 = lib.add_note(t.id, "note", title="缺图")
lib.set_content(n2.id, "![](attachments/not-there.png)\n")
lib.save()
c3 = export_markdown_tree(lib, OUT)
check("缺失图片计入 missing", c3["missing"] == 1)
readme = (OUT / "README.md").read_text(encoding="utf-8")
check("README 说明缺失", "在原数据里就缺失" in readme)
md3 = (OUT / "主题" / "缺图.md").read_text(encoding="utf-8")
check("缺失引用仍保留", "../attachments/not-there.png" in md3)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
