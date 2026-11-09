"""导出为 Markdown 文件夹。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from timodesk.exporter import export_markdown_tree
from timodesk.store import Library

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


shutil.rmtree("worklib_mdtree", ignore_errors=True)
shutil.rmtree("_mdtree_out", ignore_errors=True)
lib = Library("worklib_mdtree").load()
t = lib.add_topic("工作")
t2 = lib.add_topic("生活")
n = lib.add_note(t.id, "note", content="x")
lib.set_content(n.id, "今天开会\n\n- [ ] 待办")
a = lib.add_note(t.id, "article", content="x", title="周报")
lib.set_content(a.id, "第一段\n\n第二段")
g = lib.add_note(t.id, "gallery")
lib.save()
img = lib.import_attachment("assets/timo-icon.png")
g.images = [img]
g.description = "这是说明"
lib.save()
trash = lib.add_note(t2.id, "note", content="x")
lib.set_content(trash.id, "要被删掉的")
lib.delete_note(trash.id)
lib.save()

counts = export_markdown_tree(lib, "_mdtree_out")
root = Path("_mdtree_out")

check("主题数", counts["topics"] == 2)
check("笔记数（跳过回收站）", counts["notes"] == 3)
check("按主题建目录", (root / "工作").is_dir() and (root / "生活").is_dir())
check("有 README", (root / "README.md").exists())

files = sorted(p.name for p in (root / "工作").glob("*.md"))
check("三个文件", len(files) == 3)

note_md = (root / "工作" / "今天开会.md").read_text(encoding="utf-8")
check("有 front matter", note_md.startswith("---\ntitle:"))
check("类型写成中文", "type: 笔记" in note_md)
check("正文保留", "今天开会" in note_md and "- [ ] 待办" in note_md)

art = (root / "工作" / "周报.md").read_text(encoding="utf-8")
check("文章标题不重复", art.count("# 周报") == 1)

gal = next((root / "工作").glob("图库*.md")).read_text(encoding="utf-8")
check("图库用相对路径", "](../attachments/" in gal)
check("图库说明保留", "这是说明" in gal)
check("回收站没导出", not (root / "生活" / "要被删掉的.md").exists())

att = list((root / "attachments").iterdir())
check("图片复制过去了", len(att) == 1 and att[0].stat().st_size > 100)

# 同名主题 → -2
lib.add_topic("工作")
lib.save()
shutil.rmtree("_mdtree_out")
export_markdown_tree(lib, "_mdtree_out")
dirs = [p.name for p in Path("_mdtree_out").iterdir() if p.is_dir() and p.name != "attachments"]
check("同名主题加后缀", "工作-2" in dirs)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
