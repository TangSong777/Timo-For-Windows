"""生成发版资产：便携安装包 + SHA256SUMS.txt。

用法：
    python tools/make-release.py 0.2.0

前置：先跑 `python tools/make-portable.py` 打出 `dist/Timo For Windows 安装包.exe`。

产物（dist/release/<版本>/）：
    TimoForWindows-<版本>.exe   ← 资产名用 ASCII，避免 GitHub 把中文替换成点
    SHA256SUMS.txt
"""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "Timo For Windows 安装包.exe"


def asset_name(version: str) -> str:
    return f"TimoForWindows-{version}.exe"


def project_version() -> str:
    ns: dict = {}
    exec((ROOT / "timodesk" / "__init__.py").read_text(encoding="utf-8"), ns)  # noqa: S102
    return ns.get("__version__", "0.0.0")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print("用法: python tools/make-release.py <版本号，如 0.2.1>")
        return 2
    version = sys.argv[1].lstrip("v")
    if version != project_version():
        print(f"版本号不一致：参数 {version}，timodesk/__init__.py 是 {project_version()}")
        return 1
    if not SRC.exists():
        print(f"找不到安装包：{SRC}\n先运行 python tools/make-portable.py")
        return 1

    out_dir = ROOT / "dist" / "release" / version
    out_dir.mkdir(parents=True, exist_ok=True)
    asset = asset_name(version)
    target = out_dir / asset
    if target.exists():
        target.unlink()
    shutil.copy2(SRC, target)

    digest = sha256(target)
    (out_dir / "SHA256SUMS.txt").write_text(
        f"{digest}  {asset}\n", encoding="utf-8", newline="\n"
    )
    print(f"{target}  {target.stat().st_size / 1048576:.1f} MB")
    print(f"SHA256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
