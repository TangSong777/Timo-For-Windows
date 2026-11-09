# -*- coding: utf-8 -*-
"""未捕获异常要写进 Data/error.log。"""
import os
import shutil
import sys
from pathlib import Path

os.environ["TIMO_NO_DIALOG"] = "1"   # 测试里不弹框

from timodesk.app import _install_excepthook

ROOT = Path("worklib_eh")
shutil.rmtree(ROOT, ignore_errors=True)
ROOT.mkdir(parents=True)
_install_excepthook(ROOT)

ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


try:
    raise ValueError("测试用的错误")
except ValueError:
    sys.excepthook(*sys.exc_info())

log = ROOT / "error.log"
check("日志文件已创建", log.exists())
txt = log.read_text(encoding="utf-8") if log.exists() else ""
check("包含错误信息", "测试用的错误" in txt)
check("包含堆栈", "ValueError" in txt and "Traceback" in txt)

# 第二次仍然追加，不覆盖
try:
    raise RuntimeError("第二条")
except RuntimeError:
    sys.excepthook(*sys.exc_info())
txt2 = log.read_text(encoding="utf-8")
check("追加而不是覆盖", "测试用的错误" in txt2 and "第二条" in txt2)

print(f"\ntotal: {ok} / {ok + fail}")
sys.exit(0 if fail == 0 else 1)
