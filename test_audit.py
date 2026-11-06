# -*- coding: utf-8 -*-
"""数据体检：正文缺失、引用缺图、多余附件。"""
import shutil
import sys
from pathlib import Path

from timodesk.store import Library

ROOT = Path("worklib_ad")
shutil.rmtree(ROOT, ignore_errors=True)

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
t = lib.add_topic("测试")
n1 = lib.add_note(t.id, "note", "正常内容", None)
n2 = lib.add_note(t.id, "article", "正文", "第二篇")
img = ROOT / "attachments" / "a.png"
img.parent.mkdir(parents=True, exist_ok=True)
img.write_bytes(b"x")
n3 = lib.add_note(t.id, "gallery", "说明\n![](attachments/a.png)", None)
n3.images = ["attachments/a.png"]
lib.save()

r = lib.audit()
check("正常时无问题", not r["missing_md"] and not r["missing_attachments"] and not r["unused_attachments"])
check("计数正确", r["notes"] == 3 and r["attachments"] == 1)

(ROOT / "notes" / f"{n2.id}.md").unlink()
img.unlink()
orphan = ROOT / "attachments" / "b.png"
orphan.write_bytes(b"y")

r2 = lib.audit()
check("发现正文缺失", len(r2["missing_md"]) == 1 and r2["missing_md"][0][0] == n2.id)
check("发现引用缺图", "a.png" in r2["missing_attachments"])
check("发现多余附件", "b.png" in r2["unused_attachments"])
check("附件计数含孤儿", r2["attachments"] == 1)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
