# -*- coding: utf-8 -*-
"""合并导入时，另一个库里同名但不同 id 的主题自动加序号。"""
import shutil
import sys
from pathlib import Path

from timodesk.exporter import export_zip
from timodesk.importer import import_export
from timodesk.store import Library

ROOT = Path("worklib_mn")
for d in ("a", "b", "c"):
    shutil.rmtree(ROOT / d, ignore_errors=True)

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


# A：工作
a = Library(ROOT / "a").load()
ta = a.add_topic("工作")
a.add_note(ta.id, "note", "A 的笔记", None)
a.save()
zip_path, _ = export_zip(a, ROOT / "a.zip")

# B：已有同名主题（不同 id）
b = Library(ROOT / "b").load()
tb = b.add_topic("工作")
b.add_note(tb.id, "note", "B 的笔记", None)
b.save()

rep = import_export(zip_path, b, mode="merge")
b2 = Library(ROOT / "b").load()
names = sorted(t.name for t in b2.topics.values() if t.state != "trash")
check("两个主题都在", len(names) == 2)
check("同名自动加序号", "工作（2）" in names)
check("报告记了改名数", rep.renamed == 1)
check("提示里说明改名", "自动加序号" in rep.summary())

# 再导一次（同 id 跳过，不会再改名）
rep2 = import_export(zip_path, b2, mode="merge")
check("重复导入不再改名", rep2.renamed == 0)
check("主题数不变", len([t for t in b2.topics.values() if t.state != "trash"]) == 2)

# C：库里名字已被「工作（2）」占了，再加一个 → 工作（3）
c = Library(ROOT / "c").load()
c.add_topic("工作")
c.add_topic("工作（2）")
c.save()
import_export(zip_path, c, mode="merge")
c2 = Library(ROOT / "c").load()
names = sorted(t.name for t in c2.topics.values() if t.state != "trash")
check("跳过已占用的序号", "工作（3）" in names)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
