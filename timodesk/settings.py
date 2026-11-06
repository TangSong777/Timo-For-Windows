"""本地设置（应用锁等），保存在数据目录的 settings.json。"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

ITERATIONS = 200_000


class Settings:
    """数据目录里的 settings.json：目前只放应用锁。"""

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

    # ---------------- 应用锁 ----------------
    @property
    def lock(self) -> dict | None:
        v = self.data.get("lock")
        return v if isinstance(v, dict) and v.get("hash") else None

    def lock_enabled(self) -> bool:
        return self.lock is not None

    def set_password(self, password: str) -> None:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), ITERATIONS)
        self.data["lock"] = {"salt": salt, "hash": digest.hex(), "iterations": ITERATIONS}
        self.save()

    def check_password(self, password: str) -> bool:
        lock = self.lock
        if not lock:
            return True
        try:
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), lock["salt"].encode(), int(lock.get("iterations", ITERATIONS))
            )
        except Exception:
            return False
        return secrets.compare_digest(digest.hex(), lock["hash"])

    def clear_password(self) -> None:
        self.data.pop("lock", None)
        self.save()
