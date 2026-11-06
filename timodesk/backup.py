"""本地快照：把 library.json 与 notes/*.md 打包成 zip，出问题时可回退。"""

from __future__ import annotations

import shutil
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

KEEP = 7
PREFIX = "timo-backup-"


def backup_dir(root: Path) -> Path:
    d = Path(root) / "backup"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create(lib, stamp: str | None = None) -> Path:
    """导出当前元数据与正文，返回备份文件路径。"""
    from .store import Library  # 避免循环导入

    assert isinstance(lib, Library)
    lib.save()
    name = PREFIX + (stamp or datetime.now().strftime("%Y%m%d-%H%M%S")) + ".zip"
    out = backup_dir(lib.root) / name
    notes = lib.root / "notes"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(lib.json_path, "library.json")
        if notes.exists():
            for p in sorted(notes.glob("*.md")):
                z.write(p, "notes/" + p.name)
    prune(lib.root)
    return out


def list_all(root: Path) -> list[dict]:
    d = Path(root) / "backup"
    if not d.exists():
        return []
    items = []
    for p in sorted(d.glob(PREFIX + "*.zip"), reverse=True):
        st = p.stat()
        items.append(
            {
                "path": p,
                "name": p.name,
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime),
            }
        )
    return items


def prune(root: Path, keep: int = KEEP) -> int:
    items = list_all(root)
    removed = 0
    for it in items[keep:]:
        try:
            it["path"].unlink()
            removed += 1
        except OSError:
            pass
    return removed


def due(lib, hours: int = 20) -> bool:
    """距最近一次备份超过 hours 小时（或从未备份）就算到期。"""
    items = list_all(lib.root)
    if not items:
        return True
    return (time.time() - items[0]["mtime"].timestamp()) > hours * 3600


def restore(lib, src: Path) -> None:
    """用备份覆盖当前库；覆盖前先给现状也留一份。"""
    create(lib, stamp=datetime.now().strftime("%Y%m%d-%H%M%S") + "-before-restore")
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                name = info.filename
                if name.startswith("/") or ".." in Path(name).parts:
                    continue
                z.extract(info, td)
        tmp = Path(td)
        libjson = tmp / "library.json"
        if not libjson.exists():
            raise ValueError("备份里没有 library.json")
        notes = lib.root / "notes"
        if notes.exists():
            shutil.rmtree(notes)
        notes.mkdir(parents=True, exist_ok=True)
        src_notes = tmp / "notes"
        if src_notes.exists():
            for p in src_notes.glob("*.md"):
                shutil.copy2(p, notes / p.name)
        shutil.copy2(libjson, lib.json_path)
    lib.load()
