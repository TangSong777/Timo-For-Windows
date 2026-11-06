"""复制/导出 Markdown。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.exporter import note_markdown
from timodesk.store import Library
from timodesk.ui.main_window import MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

shutil.rmtree("worklib_md", ignore_errors=True)
lib = Library("worklib_md").load()
t = lib.add_topic("导出")
n = lib.add_note(t.id, "note", content="# 标题\n\n正文 **加粗**\n- [ ] 待办")
img = Path("worklib_md/src.png")
img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
rel = lib.import_attachment(img)
g = lib.add_note(t.id, "gallery", "")
g.images = [rel]
lib.save()

win = MainWindow(lib)
ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


md = note_markdown(n, lib.content(n.id))
check("便签正文进 Markdown", "正文 **加粗**" in md)
check("待办保留原文", "- [ ] 待办" in md)

QApplication.clipboard().setText(md)
check("剪贴板写入", "正文" in QApplication.clipboard().text())

# 直接调导出（绕过文件对话框）
out = Path("worklib_md/out/笔记.md")
out.parent.mkdir(parents=True, exist_ok=True)
gmd = note_markdown(g, "").replace("../../../attachments/", "attachments/")
out.write_text(gmd, encoding="utf-8")
import re
rels = sorted(set(re.findall(r"\]\((attachments/[^)\s]+)\)", gmd)))
check("图库 md 引用附件", bool(rels))
src = lib.attachment_abspath(rels[0].split("/", 1)[1])
check("附件可解析到文件", Path(src).exists())
dst = out.parent / rels[0]
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
check("图片已复制", dst.exists())

# 中文标题的安全文件名
safe = re.sub(r'[\\/:*?"<>|]', "_", '给 Eons/信: 2026?').strip()[:60]
check("非法字符被替换", "/" not in safe and ":" not in safe)

# 状态栏提示
win._toast("测试")
check("状态栏临时可见", not win.statusBar().isHidden())

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
