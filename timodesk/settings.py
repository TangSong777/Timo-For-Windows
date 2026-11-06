"""本地设置（窗口位置、排序方式、回收站天数等），保存在数据目录的 settings.json。"""
from __future__ import annotations

import json
import os
from pathlib import Path


class Settings:
    """数据目录里的 settings.json：纯本地的小配置，不存密码。"""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "settings.json"
        self.data: dict = {}
        self.load()

    def load(self) -> "Settings":
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}
        return self

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    # ---------------- 通用 ----------------
    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    def drop(self, key: str) -> None:
        if key in self.data:
            self.data.pop(key, None)
            self.save()
