# -*- coding: utf-8 -*-
"""卡片摘要的多词高亮：位置计算与重叠合并。"""
import sys

from timodesk.ui.widgets import _spans

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


check("单个词", _spans("今天很孤独", ["孤独"]) == [(3, 5)])
check("两个词", _spans("孤独的夜晚", ["孤独", "夜晚"]) == [(0, 2), (3, 5)])
check("重复出现", _spans("abc abc", ["abc"]) == [(0, 3), (4, 7)])
check("大小写", _spans("Hello WORLD", ["hello", "world"]) == [(0, 5), (6, 11)])
check("重叠合并", _spans("abcd", ["abc", "bcd"]) == [(0, 4)])
check("无命中", _spans("今天很好", ["孤独"]) == [])
check("空词忽略", _spans("abc", ["", " "]) == [])
check("中文多词", _spans("夜晚的孤独与思念", ["孤独", "夜晚"]) == [(0, 2), (3, 5)])

# 真实搜索：多词 AND
import shutil
from pathlib import Path

from timodesk.store import Library

ROOT = Path("worklib_mh")
shutil.rmtree(ROOT, ignore_errors=True)
lib = Library(ROOT).load()
t = lib.add_topic("测试")
lib.add_note(t.id, "note", "孤独的夜晚，风很大", None)
lib.add_note(t.id, "note", "孤独的白天", None)
lib.add_note(t.id, "note", "热闹的夜晚", None)
lib.save()
hits = lib.search("孤独 夜晚")
check("多词搜索只命中同时含两词的", len(hits) == 1)
check("命中内容正确", "风很大" in lib.content(hits[0].id))

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
