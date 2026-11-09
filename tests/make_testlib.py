"""生成测试用的真实数据样本 `testlib/`。

用法（在仓库根目录）：
    python tests/make_testlib.py [Timo 导出包.zip]

不给参数时用会话里那份导出包；找不到就跳过，不影响其他测试。
`testlib/` 不入库（见 .gitignore），需要时再生一次。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from timodesk.importer import import_export  # noqa: E402
from timodesk.store import Library  # noqa: E402

DEFAULT_ZIP = r"E:\下载\Timo_Export_20261106_163520.zip"


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ZIP)
    if not src.exists():
        print(f"找不到导出包：{src}")
        print("跳过（依赖 testlib 的测试会自动跳过）")
        return 0
    lib = Library(Path("testlib"))
    lib.load()
    report = import_export(src, lib, mode="replace")
    lib.save()
    print(report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
