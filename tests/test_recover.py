# -*- coding: utf-8 -*-
"""library.json 损坏时不崩、能留档、能用备份恢复。"""
import json
import shutil
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk import backup
from timodesk.app import recover_library
from timodesk.store import Library

ROOT = Path("worklib_rc")
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
t = lib.add_topic("测试主题")
n = lib.add_note(t.id, "note", title="坏档前的笔记")
lib.set_content(n.id, "内容还在吗")
lib.save()
arch = backup.create(lib)
check("备份已生成", arch.exists())

# 写坏索引
lib.json_path.write_text("{ 这不是 json", encoding="utf-8")

# 1) 读坏档：不抛异常、留档、空库
lib2 = Library(ROOT).load()
check("读坏档不崩", lib2 is not None)
check("load_error 有值", bool(lib2.load_error))
check("空库启动", len(lib2.notes) == 0)
broken = list(ROOT.glob("library.json.broken-*"))
check("坏档已留档", len(broken) == 1)

# 2) 用最近备份恢复
recovered = recover_library(lib2, notify=False)
check("恢复成功", recovered)
check("笔记回来了", len(lib2.notes) == 1)
check("正文回来了", lib2.content(next(iter(lib2.notes))) == "内容还在吗")
check("主题回来了", len(lib2.topics) == 1)
check("load_error 已清", not lib2.load_error)

# 3) 备份 zip 里没有 library.json 时不崩，返回 False
shutil.rmtree(ROOT / "backup", ignore_errors=True)
(ROOT / "backup").mkdir(parents=True, exist_ok=True)
bad = ROOT / "backup" / "timo-backup-19700101-000000.zip"
import zipfile
with zipfile.ZipFile(bad, "w") as z:
    z.writestr("README.txt", "not a backup")
lib3 = Library(ROOT).load()
lib3.json_path.write_text("{{{", encoding="utf-8")
res = recover_library(lib3, notify=False)
check("坏备份不崩", res is False)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
