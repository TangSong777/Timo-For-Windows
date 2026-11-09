# -*- coding: utf-8 -*-
"""已删除主题：找回（连带笔记）/ 彻底删除。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library

ROOT = Path("worklib_tt")
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
t = lib.add_topic("要删的主题")
n1 = lib.add_note(t.id, "note", title="先单独删的")
n2 = lib.add_note(t.id, "note", title="跟着主题删的")
lib.set_content(n1.id, "a")
lib.set_content(n2.id, "b")
lib.save()

lib.delete_note(n1.id)          # 单独进回收站
lib.delete_topic(t.id)          # 主题 + 剩下的笔记一起进回收站
lib.save()

check("主题在回收站列表", [x.id for x in lib.trashed_topics()] == [t.id])
check("主题有删除时间", bool(lib.topics[t.id].deleted_at))
check("笔记都在回收站", lib.notes[n1.id].state == "trash" and lib.notes[n2.id].state == "trash")
check("先删的笔记保留原时间", lib.notes[n1.id].deleted_at != lib.notes[n2.id].deleted_at)

back = lib.restore_topic(t.id)
check("恢复主题", lib.topics[t.id].state == "active")
check("带回 1 条（跟着主题删的那条）", back == 1)
check("跟着删的已恢复", lib.notes[n2.id].state == "active")
check("单独删的仍在回收站", lib.notes[n1.id].state == "trash")
check("主题计数正确", lib.topic_note_count(t.id, "active") == 1)

lib.delete_topic(t.id)
lib.save()
gone = lib.purge_topic(t.id)
check("彻底删除返回笔记数", gone == 2)
check("主题没了", t.id not in lib.topics)
check("笔记没了", n1.id not in lib.notes and n2.id not in lib.notes)

lib2 = Library(ROOT).load()
check("重载后一致", t.id not in lib2.topics and not lib2.notes)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
