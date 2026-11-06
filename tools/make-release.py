"""把 PyInstaller 产物打成发布用的 zip，并生成 SHA256SUMS.txt。

用法：
    python tools/make-release.py 0.1.0

产物：
    TimoDesktop-<版本>-win64.zip
    SHA256SUMS.txt
"""
from __future__ import annotations

import hashlib
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "Timo笔记"


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python tools/make-release.py <版本号，如 0.1.0>")
        return 2
    version = sys.argv[1].lstrip("v")
    if not SRC.is_dir():
        print(f"找不到打包产物：{SRC}\n先运行 PyInstaller。")
        return 1

    out = ROOT / f"TimoDesktop-{version}-win64.zip"
    arc_root = f"TimoDesktop-{version}"

    files = [
        (p, os.path.relpath(p, SRC))
        for dp, _, fns in os.walk(SRC)
        for p in (os.path.join(dp, fn) for fn in fns)
    ]
    files.sort(key=lambda x: x[1])

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p, rel in files:
            z.write(p, f"{arc_root}/{rel}".replace("\\", "/"))

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    (ROOT / "SHA256SUMS.txt").write_text(f"{digest}  {out.name}\n", encoding="utf-8", newline="\n")

    print(f"文件数 {len(files)}，大小 {out.stat().st_size / 1048576:.1f} MB")
    print(f"SHA256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
