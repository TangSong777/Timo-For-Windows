# -*- coding: utf-8 -*-
"""某条笔记的 md 编码坏了/缺失时，整库仍能打开。"""
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library

ROOT = Path("worklib_bf")
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
t = lib.add_topic("测试")
a = lib.add_note(t.id, "note", title="正常")
b = lib.add_note(t.id, "note", title="坏编码")
c = lib.add_note(t.id, "note", title="文件丢失")
lib.set_content(a.id, "正常内容")
lib.set_content(b.id, "坏内容")
lib.set_content(c.id, "要删掉的内容")
lib.save()

# 把 b 写成 GBK，把 c 的 md 删掉
lib.note_path(b.id).write_bytes("坏内容——这是 GBK".encode("gbk"))
lib.note_path(c.id).unlink()

lib2 = Library(ROOT).load()
check("整库还能打开", len(lib2.notes) == 3)
check("正常笔记内容正常", lib2.content(a.id) == "正常内容")
check("坏编码笔记有内容", len(lib2.content(b.id)) > 0)
check("坏文件被记下", len(lib2.bad_files) == 2)
check("丢失文件的笔记为空", lib2.content(c.id) == "")

# 再存一次不应把坏内容写回去覆盖
lib2.save()
lib3 = Library(ROOT).load()
check("重载一致", lib3.content(a.id) == "正常内容")

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
