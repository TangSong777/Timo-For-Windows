"""Timo 桌面版的数据层。

设计原则
--------
* **Markdown 是正文的唯一真相**：每条笔记的正文存放在 ``notes/<id>.md``，
  用户随时可以用任何编辑器打开、备份、git 管理。
* 元数据集中在一个 ``library.json`` 里（原子写入），启动时整体载入内存。
  1000~10000 条笔记的规模下，内存过滤搜索足够快，也不引入数据库依赖。
* 笔记 id 沿用 Timo 导出的原始 id，保证「导入 → 导出」可逆。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
# 笔记类型：与 Timo 导出的 type 名称一致
INBOX_TOPIC = "（未分类）"

NOTE_TYPES = ("note", "article", "gallery", "link", "date", "account")
TYPE_LABELS = {
    "note": "笔记",
    "article": "文章",
    "gallery": "图库",
    "link": "链接",
    "date": "日子",
    "account": "账号",
}
# typeCode ↔ 类型名（来自 Timo 导出数据）
TYPE_CODE = {"note": 0, "account": 1, "link": 2, "gallery": 3, "article": 4, "date": 6}

# 笔记状态
STATES = ("active", "archived", "trash")
STATE_LABELS = {"active": "笔记", "archived": "归档", "trash": "回收站"}


def now_iso() -> str:
    """与 Timo 一致的 UTC ISO 时间（毫秒 + Z）。"""
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f".{int(t * 1000) % 1000:03d}Z"


def to_iso(dt) -> str:
    """本地 datetime → Timo 风格 UTC ISO（毫秒 + Z）。"""
    from datetime import timezone

    if dt.tzinfo is None:
        dt = dt.astimezone()
    u = dt.astimezone(timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S") + f".{u.microsecond // 1000:03d}Z"


def from_iso(s: str | None):
    """ISO 时间 → 本地 datetime（无值返回 None）。"""
    from datetime import datetime

    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


def parse_iso(s: str | None) -> float:
    """把 ISO 时间转成时间戳，用于排序；坏值返回 0。"""
    if not s:
        return 0.0
    try:
        from datetime import datetime

        txt = s.replace("Z", "+00:00")
        # 兼容没有毫秒/时区的写法
        return datetime.fromisoformat(txt).timestamp()
    except Exception:
        return 0.0


@dataclass
class Topic:
    id: str
    name: str
    mode: str = "white"
    locked: bool = False
    state: str = "active"
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str | None = None
    archived_at: str | None = None
    order: float = 0.0

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Note:
    id: str
    topic_id: str
    type: str = "note"
    state: str = "active"
    title: str | None = None
    color: str | None = None
    created_at: str = ""
    updated_at: str = ""
    deleted_at: str | None = None
    archived_at: str | None = None
    pinned_at: str | None = None
    # 类型附加字段
    url: str | None = None
    description: str = ""
    images: list[str] = field(default_factory=list)
    account: str = ""
    password: str = ""
    remark: str = ""
    date: dict | None = None
    tags: list[str] = field(default_factory=list)
    order: float = 0.0
    # 本地提醒（Timo 导出包不含此字段，导出时会丢失）
    remind_at: str | None = None

    def to_json(self) -> dict:
        return asdict(self)

    # 稳定排序键：置顶优先，其次 pinned/updated 时间
    def sort_key(self, mode: str = "updated", content: str = "") -> tuple:
        pin = 0 if self.pinned_at else 1
        if mode == "created":
            return (pin, -parse_iso(self.created_at))
        if mode == "title":
            title = self.display_title(content)
            return (pin, title.lower())
        return (pin, -parse_iso(self.updated_at or self.created_at))

    def display_title(self, content: str = "", topic_name: str = "") -> str:
        """列表里显示的标题：有标题用标题，否则取正文首行。"""
        if self.title and self.title.strip():
            return self.title.strip()
        first = next((ln.strip() for ln in (content or "").splitlines() if ln.strip()), "")
        if first:
            return first[:80]
        if self.type == "gallery":
            return f"图库（{len(self.images)} 张）"
        if self.type == "account":
            return self.account or "账号"
        return "（空白笔记）"


class Library:
    """一个本地库：目录 + library.json + notes/ + attachments/。"""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)
        self.topics: dict[str, Topic] = {}
        self.notes: dict[str, Note] = {}
        self._content: dict[str, str] = {}
        self._dirty = False

    # ---------- 路径 ----------
    @property
    def json_path(self) -> Path:
        return self.root / "library.json"

    @property
    def notes_dir(self) -> Path:
        return self.root / "notes"

    @property
    def attachments_dir(self) -> Path:
        return self.root / "attachments"

    def note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.md"

    def attachment_path(self, name: str) -> Path:
        return self.attachments_dir / name

    # ---------- 读写 ----------
    def exists(self) -> bool:
        return self.json_path.exists()

    def load(self) -> "Library":
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        if not self.json_path.exists():
            return self
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.topics = {t["id"]: Topic(**t) for t in data.get("topics", [])}
        self.notes = {n["id"]: Note(**n) for n in data.get("notes", [])}
        for n in self.notes.values():
            p = self.note_path(n.id)
            self._content[n.id] = p.read_text(encoding="utf-8") if p.exists() else ""
        return self

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "app": "Timo Desktop",
            "savedAt": now_iso(),
            "topics": [
                self.topics[k].to_json()
                for k in sorted(self.topics, key=lambda k: (self.topics[k].order, self.topics[k].created_at))
            ],
            "notes": [n.to_json() for n in self.notes.values()],
        }
        tmp = self.json_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        # Windows 上杀毒/索引服务偶尔会短暂占用目标文件，重试几次再放弃
        for attempt in range(6):
            try:
                os.replace(tmp, self.json_path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))

    # ---------- 查询 ----------
    def content(self, note_id: str) -> str:
        if note_id not in self._content:
            p = self.note_path(note_id)
            self._content[note_id] = p.read_text(encoding="utf-8") if p.exists() else ""
        return self._content[note_id]

    def set_content(self, note_id: str, text: str) -> None:
        self._content[note_id] = text
        p = self.note_path(note_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, p)

    def sorted_topics(self, state: str = "active") -> list[Topic]:
        ts = [t for t in self.topics.values() if t.state == state]
        ts.sort(key=lambda t: (t.order, t.created_at))
        return ts

    def topic_notes(self, topic_id: str | None, state: str = "active", order: str = "updated") -> list[Note]:
        out = [n for n in self.notes.values() if n.state == state and (topic_id is None or n.topic_id == topic_id)]
        if order == "title":
            out.sort(key=lambda n: n.sort_key(order, self._content.get(n.id, "")))
        else:
            out.sort(key=lambda n: n.sort_key(order))
        return out

    def note_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self.notes.values():
            if n.state == "active":
                counts[n.topic_id] = counts.get(n.topic_id, 0) + 1
        return counts

    def sorted_notes(self, state: str = "active", topic_id: str | None = None, order: str = "updated") -> list[Note]:
        out = [n for n in self.notes.values() if n.state == state and (topic_id is None or n.topic_id == topic_id)]
        if order == "title":
            out.sort(key=lambda n: n.sort_key(order, self._content.get(n.id, "")))
        else:
            out.sort(key=lambda n: n.sort_key(order))
        return out

    def search(self, query: str, state: str = "active", pool: list[Note] | None = None) -> list[Note]:
        q = (query or "").strip().lower()
        if not q:
            return []
        terms = [t for t in re.split(r"\s+", q) if t]
        hits = []
        for n in pool if pool is not None else self.notes.values():
            if pool is None and n.state != state:
                continue
            hay = " ".join(
                [
                    n.title or "",
                    n.description or "",
                    n.url or "",
                    n.account or "",
                    n.remark or "",
                    " ".join(n.tags),
                    self.content(n.id),
                ]
            ).lower()
            if all(t in hay for t in terms):
                hits.append(n)
        hits.sort(key=lambda n: -parse_iso(n.updated_at or n.created_at))
        return hits

    # ---------- 变更 ----------
    def new_id(self) -> str:
        return str(uuid.uuid4())

    def add_topic(self, name: str) -> Topic:
        order = max([t.order for t in self.topics.values()], default=0.0) + 1.0
        t = Topic(id=self.new_id(), name=name.strip() or "未命名主题", created_at=now_iso(), updated_at=now_iso(), order=order)
        self.topics[t.id] = t
        self.save()
        return t

    def rename_topic(self, topic_id: str, name: str) -> None:
        t = self.topics.get(topic_id)
        if not t:
            return
        t.name = name.strip() or t.name
        t.updated_at = now_iso()
        self.save()

    def delete_topic(self, topic_id: str, hard: bool = False) -> None:
        if hard:
            for n in [n for n in self.notes.values() if n.topic_id == topic_id]:
                self.delete_note(n.id, hard=True)
            self.topics.pop(topic_id, None)
        else:
            t = self.topics.get(topic_id)
            if t:
                t.state = "trash"
                # 和手机版一致：删主题时，主题里还在用的笔记一起进回收站
                ts = now_iso()
                for n in self.notes.values():
                    if n.topic_id == topic_id and n.state == "active":
                        n.state = "trash"
                        n.deleted_at = ts
        self.save()

    def reorder_topics(self, ordered_ids: list[str]) -> None:
        for i, tid in enumerate(ordered_ids):
            if tid in self.topics:
                self.topics[tid].order = float(i)
        self.save()

    def add_note(self, topic_id: str, type: str = "note", content: str = "", title: str | None = None) -> Note:
        order = max([n.order for n in self.notes.values() if n.topic_id == topic_id], default=0.0) + 1.0
        ts = now_iso()
        n = Note(
            id=self.new_id(),
            topic_id=topic_id,
            type=type,
            state="active",
            title=title,
            created_at=ts,
            updated_at=ts,
            order=order,
        )
        self.notes[n.id] = n
        self.set_content(n.id, content)
        self._touch_topic(topic_id)
        self.save()
        return n

    def update_note(self, note: Note) -> None:
        self.notes[note.id] = note
        note.updated_at = now_iso()
        self._touch_topic(note.topic_id)
        self.save()

    def _touch_topic(self, topic_id: str) -> None:
        t = self.topics.get(topic_id)
        if t:
            t.updated_at = now_iso()

    def purge_trash(self, days: int = 30) -> int:
        """彻底删掉回收站里躺了超过 days 天的笔记；days<=0 表示不清理。"""
        if days <= 0:
            return 0
        cutoff = time.time() - days * 86400
        gone = [
            n.id
            for n in list(self.notes.values())
            if n.state == "trash" and 0 < parse_iso(n.deleted_at or n.updated_at) < cutoff
        ]
        for nid in gone:
            self.delete_note(nid, hard=True)
        if gone:
            self.save()
        return len(gone)

    def delete_note(self, note_id: str, hard: bool = False) -> None:
        n = self.notes.get(note_id)
        if not n:
            return
        if hard:
            self.notes.pop(note_id, None)
            self._content.pop(note_id, None)
            p = self.note_path(note_id)
            if p.exists():
                p.unlink()
        else:
            n.state = "trash"
            n.deleted_at = now_iso()
        self.save()

    def inbox_topic_id(self) -> str:
        """找（或建）一个用来收留「主题已被删掉」的笔记的占位主题。"""
        for t in self.sorted_topics():
            if t.name == INBOX_TOPIC:
                return t.id
        t = self.add_topic(INBOX_TOPIC)
        self.save()
        return t.id

    def restore_note(self, note_id: str) -> None:
        n = self.notes.get(note_id)
        if not n:
            return
        t = self.topics.get(n.topic_id)
        if not t or t.state != "active":
            # 原主题已经删了，恢复时落到「（未分类）」，不要变成孤儿笔记
            n.topic_id = self.inbox_topic_id()
        n.state = "active"
        n.deleted_at = None
        n.archived_at = None
        self.save()

    def archive_note(self, note_id: str, archived: bool = True) -> None:
        n = self.notes.get(note_id)
        if not n:
            return
        n.state = "archived" if archived else "active"
        n.archived_at = now_iso() if archived else None
        self.save()

    def move_note(self, note_id: str, topic_id: str) -> None:
        n = self.notes.get(note_id)
        if n and topic_id in self.topics:
            n.topic_id = topic_id
            n.updated_at = now_iso()
            self.save()

    def move_notes(self, note_ids, topic_id: str) -> int:
        """批量移动到主题，返回实际移动的条数（只存一次盘）。"""
        if topic_id not in self.topics:
            return 0
        moved = 0
        for nid in note_ids:
            n = self.notes.get(nid)
            if n and n.topic_id != topic_id:
                n.topic_id = topic_id
                n.updated_at = now_iso()
                moved += 1
        if moved:
            self.save()
        return moved

    def toggle_pin(self, note_id: str) -> None:
        n = self.notes.get(note_id)
        if not n:
            return
        n.pinned_at = None if n.pinned_at else now_iso()
        self.save()

    def set_reminder(self, note_id: str, when_iso: str | None) -> None:
        """设置/清除笔记提醒。when_iso 为 None 表示清除。"""
        n = self.notes.get(note_id)
        if not n:
            return
        n.remind_at = when_iso
        self.save()

    def due_reminders(self, now: float | None = None) -> list[Note]:
        """取出已到时间、还没提醒过的笔记，并把 remind_at 清空（只提醒一次）。"""
        now = time.time() if now is None else now
        out = []
        for n in self.notes.values():
            if n.state != "active" or not n.remind_at:
                continue
            if parse_iso(n.remind_at) <= now:
                out.append(n)
                n.remind_at = None
        if out:
            self.save()
        return out

    def upcoming_reminders(self, limit: int = 200) -> list[Note]:
        now = time.time()
        items = [n for n in self.notes.values() if n.state == "active" and n.remind_at and parse_iso(n.remind_at) > now]
        items.sort(key=lambda n: parse_iso(n.remind_at))
        return items[:limit]

    def toggle_color(self, note_id: str, color: str | None) -> None:
        n = self.notes.get(note_id)
        if n:
            n.color = color
            self.save()

    def touch(self, note_id: str) -> None:
        """更新笔记的修改时间。"""
        n = self.notes.get(note_id)
        if n:
            n.updated_at = now_iso()
            self._touch_topic(n.topic_id)

    @property
    def meta_path(self) -> Path:
        return self.json_path

    # ---------- 附件 ----------
    def import_attachment(self, src: str | os.PathLike) -> str:
        """把外部文件复制进 attachments/，返回应用内相对路径。"""
        src = Path(src)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d%H%M%S")
        name = f"{stamp}__{src.name}"
        dst = self.attachment_path(name)
        i = 1
        while dst.exists():
            dst = self.attachment_path(f"{stamp}__{i}__{src.name}")
            i += 1
        shutil.copy2(src, dst)
        return f"attachments/{dst.name}"

    def attachment_abspath(self, rel: str) -> Path:
        rel = rel.replace("\\", "/")
        if rel.startswith("attachments/"):
            return self.root / rel
        return self.attachments_dir / Path(rel).name
