"""跑 tests/ 下全部 test_*.py。

用法（在仓库根目录）：
    python tests/run_all.py

每个脚本都是独立进程，工作目录固定为仓库根，并把仓库根放进 PYTHONPATH，
这样测试里 `import timodesk` 才能找到包。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    files = sorted(ROOT.glob("tests/test_*.py"))
    if not files:
        print("没找到测试脚本")
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    bad: list[str] = []
    for f in files:
        try:
            r = subprocess.run(
                [sys.executable, str(f)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            rc, out = r.returncode, r.stdout or ""
        except subprocess.TimeoutExpired:
            rc, out = 99, "超时"
        tail = [line.strip() for line in out.strip().splitlines() if line.strip()]
        last = tail[-1] if tail else "（无输出）"
        ok = rc == 0 and "FAIL" not in last
        print(f"{'OK ' if ok else 'BAD'} {f.name:<26} {last}")
        if not ok:
            bad.append(f.name)
    print(f"\n{len(files) - len(bad)}/{len(files)} 通过" + (f"；失败：{', '.join(bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
