"""导入时自动去重：包里自带重复、以及重复导入同一个包。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.exporter import export_zip
from timodesk.importer import import_export
from timodesk.store import Library

app = QApplication(sys.argv)

for d in ("worklib_dd_a", "worklib_dd_b", "worklib_dd_c", "worklib_dd_e"):
    shutil.rmtree(d, ignore_errors=True)

# 源库：两条一模一样的便签（模拟包里有错），外加不同类型但字段不同的笔记
a = Library("worklib_dd_a").load()
t = a.add_topic("工作")
a.add_note(t.id, "note", content="一模一样的内容")
a.add_note(t.id, "note", content="一模一样的内容")
a.add_note(t.id, "note", content="另一条")
g1 = a.add_note(t.id, "gallery", content="")
g2 = a.add_note(t.id, "gallery", content="")
a.notes[g1.id].images = ["attachments/a.png"]
a.notes[g2.id].images = ["attachments/b.png"]
l1 = a.add_note(t.id, "link", content="说明")
l2 = a.add_note(t.id, "link", content="说明")
a.notes[l1.id].url = "https://a.example"
a.notes[l2.id].url = "https://b.example"
a.save()
zip_path, _ = export_zip(a, "worklib_dd_a/out.zip")

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. 替换导入：包内重复只留一条
b = Library("worklib_dd_b").load()
r = import_export(zip_path, b, mode="replace")
same = [n for n in b.notes.values() if b.content(n.id) == "一模一样的内容"]
check("包内重复去掉 1 条", r.deduped == 1)
check("实际入库 6 条", len(b.notes) == 6)
check("内容相同的只剩 1 条", len(same) == 1)
check("图库两条都在", sum(1 for n in b.notes.values() if n.type == "gallery") == 2)
check("链接两条都在", sum(1 for n in b.notes.values() if n.type == "link") == 2)
check("提示里写了去重条数", "重复" in r.summary())

# 2. 同一个包再按替换导入：结果一样，不会越导越多
r2 = import_export(zip_path, b, mode="replace")
check("重复导入仍是 6 条", len(b.notes) == 6)
check("重复导入仍报去重 1 条", r2.deduped == 1)

# 3. 库里已有同内容（id 不同）时，合并导入要跳过
c = Library("worklib_dd_c").load()
tc = c.add_topic("工作")
c.add_note(tc.id, "note", content="一模一样的内容")
c.save()
r3 = import_export(zip_path, c, mode="merge")
check("合并：同内容的 2 条都跳过", r3.deduped == 2)
check("合并后同内容只有 1 条", sum(1 for n in c.notes.values()
                                 if c.content(n.id) == "一模一样的内容") == 1)
check("合并新增其它 5 条", r3.notes == 5)
check("库里共 6 条", len(c.notes) == 6)

# 4. 关掉去重时行为回到旧样（给需要完整往返的场合留口子）
d = Library("worklib_dd_b").load()
r4 = import_export(zip_path, d, mode="replace", dedupe=False)
check("dedupe=False 时保留包内重复", r4.deduped == 0 and len(d.notes) == 7)

# 5. 库里那条已经进了回收站，也不该再造一份出来
e = Library("worklib_dd_e").load()
te = e.add_topic("工作")
ne = e.add_note(te.id, "note", content="一模一样的内容")
ne.state = "trash"
e.save()
r5 = import_export(zip_path, e, mode="merge")
check("回收站里的同内容也算重复", r5.deduped == 2 and r5.notes == 5)
check("回收站里仍只有那 1 条", len(e.notes) == 6)

print(f"\n{ok}/{total} 通过")
sys.exit(0 if ok == total else 1)
