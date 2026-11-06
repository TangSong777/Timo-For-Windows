# -*- coding: utf-8 -*-
"""笔记拖到归档主题时跟着归档，拖回正常主题时恢复。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library

ROOT = Path("worklib_ms")
shutil.rmtree(ROOT, ignore_errors=True)
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
normal = lib.add_topic("正常")
arch = lib.add_topic("归档主题")
lib.archive_topic(arch.id) if hasattr(lib, "archive_topic") else setattr(arch, "state", "archived")
lib.save()

n = lib.add_note(normal.id, "note", title="要拖的")
lib.set_content(n.id, "内容")
lib.save()
check("初始 active", lib.notes[n.id].state == "active")

lib.move_notes([n.id], arch.id)
check("拖到归档主题后变 archived", lib.notes[n.id].state == "archived")
check("归属正确", lib.notes[n.id].topic_id == arch.id)
check("主题视图能看到", [x.id for x in lib.topic_notes(arch.id, "archived")] == [n.id])
check("active 视图看不到", n.id not in [x.id for x in lib.topic_notes(arch.id, "active")])

lib.move_notes([n.id], normal.id)
check("拖回正常主题恢复 active", lib.notes[n.id].state == "active")
check("archived_at 清空", lib.notes[n.id].archived_at is None)

# 重载后一致
lib2 = Library(ROOT).load()
check("重载后状态一致", lib2.notes[n.id].state == "active")

# 移动到不存在的主题不做事
check("无效主题返回 0", lib.move_notes([n.id], "不存在") == 0)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
