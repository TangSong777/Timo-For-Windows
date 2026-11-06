"""打便携版：主程序 → payload.zip → 单文件安装器。

用法：
    python tools/make-portable.py            # 全部重打
    python tools/make-portable.py --skip-main  # 复用 dist/Timo For Windows
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_DIR = DIST / "Timo For Windows"
PAYLOAD = BUILD / "payload.zip"
SETUP_NAME = "Timo For Windows 安装包"

EXCLUDES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "flask",
    "scipy",
    "IPython",
    "pytest",
]


def version() -> str:
    ns: dict = {}
    exec((ROOT / "timodesk" / "__init__.py").read_text(encoding="utf-8"), ns)  # noqa: S102
    return ns.get("__version__", "0.0.0")


def pyinstaller(*args: str) -> None:
    env = dict(os.environ)
    user_site = Path(os.environ.get("APPDATA", "")) / "Python" / "Python312" / "site-packages"
    if user_site.exists():
        env["PYTHONPATH"] = str(user_site) + (
            os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
        )
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", *args]
    print("  $", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def build_main() -> None:
    print("[1/3] 打包主程序…")
    args = [
        "--windowed",
        "--name",
        "Timo For Windows",
        "--icon",
        "assets/timo-icon.ico",
        "--add-data",
        "assets;assets",
    ]
    for m in EXCLUDES:
        args += ["--exclude-module", m]
    args.append("run.py")
    pyinstaller(*args)
    if not (APP_DIR / "Timo For Windows.exe").exists():
        raise SystemExit("主程序没有打出来：" + str(APP_DIR))


def build_payload() -> None:
    print("[2/3] 压缩 payload…")
    BUILD.mkdir(parents=True, exist_ok=True)
    if PAYLOAD.exists():
        PAYLOAD.unlink()
    files = sorted(p for p in APP_DIR.rglob("*") if p.is_file())
    with zipfile.ZipFile(PAYLOAD, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr(zipfile.ZipInfo("Data/"), "")
        for p in files:
            zf.write(p, p.relative_to(APP_DIR).as_posix())
    mb = PAYLOAD.stat().st_size / 1024 / 1024
    print(f"      {PAYLOAD.name}  {mb:.1f} MB  ({len(files)} 个文件)")


def build_setup() -> None:
    print("[3/3] 打包安装器…")
    args = [
        "--onefile",
        "--windowed",
        "--name",
        SETUP_NAME,
        "--icon",
        "assets/timo-icon.ico",
        "--add-data",
        f"{PAYLOAD};.",
    ]
    for m in EXCLUDES:
        args += ["--exclude-module", m]
    args.append("installer.py")
    pyinstaller(*args)
    exe = DIST / f"{SETUP_NAME}.exe"
    if not exe.exists():
        raise SystemExit("安装器没有打出来：" + str(exe))
    mb = exe.stat().st_size / 1024 / 1024
    print(f"\n完成：{exe}  ({mb:.1f} MB)   版本 {version()}")


def main() -> int:
    if "--skip-main" not in sys.argv:
        if APP_DIR.exists():
            shutil.rmtree(APP_DIR)
        build_main()
    build_payload()
    build_setup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
