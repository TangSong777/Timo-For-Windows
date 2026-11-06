"""从 Timo 的「可读数据导出」ZIP 导入到本地库。"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .store import Library, Note, Topic, TYPE_CODE, now_iso

IMG_RE = re.compile(r"!\[([^\]]*)\]\((?:\.\./)+attachments/([^)\s]+)\)")


@dataclass
class ImportReport:
    topics: int = 0
    notes: int = 0
    attachments: int = 0
    missing_attachments: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        s = f"导入完成：{self.topics} 个主题、{self.notes} 条笔记、{self.attachments} 个附件"
        if self.missing_attachments:
            s += f"\n缺失附件 {len(self.missing_attachments)} 个"
        return s


def _fix_zip_name(info: zipfile.ZipInfo) -> str:
    """Windows 下用资源管理器压缩的 zip 可能用 GBK 存文件名。"""
    name = info.filename
    if not (info.flag_bits & 0x800):
        try:
            raw = name.encode("cp437")
            for enc in ("utf-8", "gbk"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
        except UnicodeEncodeError:
            pass
    return name


def extract_export(src: str | os.PathLike, dst: str | os.PathLike) -> Path:
    """把导出 ZIP 解压到 dst（已解压目录则直接返回）。"""
    src = Path(src)
    dst = Path(dst)
    if src.is_dir():
        return src
    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = _fix_zip_name(info).replace("\\", "/")
            # 防 zip 路径穿越
            name = "/".join(p for p in name.split("/") if p not in ("", ".", ".."))
            if not name:
                continue
            out = dst / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as fh, open(out, "wb") as w:
                shutil.copyfileobj(fh, w)
    return dst


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def _norm_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def _strip_leading_title(content: str, title: str | None) -> str:
    """文章正文里通常自带 '# 标题' 行，去掉它避免和标题栏重复。"""
    text = _norm_newlines(content or "")
    if title:
        lines = text.split("\n")
        head = 0
        while head < len(lines) and not lines[head].strip():
            head += 1
        if head < len(lines) and lines[head].strip() == f"# {title}".strip():
            lines = lines[head + 1 :]
            while lines and not lines[0].strip():
                lines.pop(0)
            return "\n".join(lines)
    return text


def _load_account_passwords(root: Path) -> dict[str, dict]:
    """accounts.csv: id,topic_id,title,account,password,remark,created_at,updated_at"""
    p = root / "content" / "accounts.csv"
    out: dict[str, dict] = {}
    if not p.exists():
        return out
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row.get("id", "")] = row
    return out


def import_export(src: str | os.PathLike, lib: Library, progress=None) -> ImportReport:
    """导入 Timo 导出包。会清空 lib 现有内容，然后整体替换。"""
    report = ImportReport()
    tmp = None
    try:
        src_path = Path(src)
        if src_path.is_dir():
            root = src_path
        else:
            tmp = tempfile.mkdtemp(prefix="timo_import_")
            root = extract_export(src_path, tmp)

        data_dir = root / "data"
        topics_raw = json.loads(_read_text(data_dir / "topics.json")) if (data_dir / "topics.json").exists() else {}
        docs_raw = json.loads(_read_text(data_dir / "documents.json")) if (data_dir / "documents.json").exists() else {}
        manifest = json.loads(_read_text(root / "manifest.json")) if (root / "manifest.json").exists() else {}
        passwords = _load_account_passwords(root)

        # 清空目标库
        lib.topics.clear()
        lib.notes.clear()
        lib._content.clear()
        if lib.notes_dir.exists():
            shutil.rmtree(lib.notes_dir)
        lib.notes_dir.mkdir(parents=True, exist_ok=True)
        lib.attachments_dir.mkdir(parents=True, exist_ok=True)

        # 1) 主题
        topic_list = topics_raw.get("topics", [])
        for i, t in enumerate(topic_list):
            lib.topics[t["id"]] = Topic(
                id=t["id"],
                name=t.get("name") or "未命名主题",
                mode=t.get("mode") or "white",
                locked=bool(t.get("locked")),
                state=t.get("state") or "active",
                created_at=t.get("createdAt") or "",
                updated_at=t.get("updatedAt") or "",
                deleted_at=t.get("deletedAt"),
                archived_at=t.get("archivedAt"),
                order=float(i),
            )
        report.topics = len(lib.topics)

        # 2) 附件：uri → 应用内相对路径
        uri_map: dict[str, str] = {}
        att_src = root / "attachments"
        if att_src.exists():
            for f in att_src.iterdir():
                if f.is_file():
                    shutil.copy2(f, lib.attachment_path(f.name))
                    report.attachments += 1
        for a in manifest.get("attachments", []):
            if a.get("uri") and a.get("path"):
                uri_map[a["uri"]] = f"attachments/{Path(a['path']).name}"

        def rewrite_md(text: str) -> tuple[str, int]:
            """把 md 里的 ../../../attachments/x 改成 attachments/x。"""
            missing = 0

            def repl(m: re.Match) -> str:
                nonlocal missing
                alt, name = m.group(1), m.group(2)
                if not lib.attachment_path(name).exists():
                    missing += 1
                    report.missing_attachments.append(name)
                return f"![{alt}](attachments/{name})"

            new = IMG_RE.sub(repl, text)
            return new, missing

        # 3) 逐条笔记
        docs = docs_raw.get("documents", [])
        total = len(docs)
        for idx, d in enumerate(docs):
            raw = d.get("raw") or {}
            ntype = d.get("type") or "note"
            if ntype not in TYPE_CODE:
                report.warnings.append(f"未知类型 {ntype}，按笔记处理：{d.get('id')}")
                ntype = "note"
            title = raw.get("title") or (d.get("normalized") or {}).get("title")
            content = ""
            images: list[str] = []
            url = None
            description = ""
            account = password = remark = ""
            date_info = None

            rp = d.get("readablePath") or ""
            md_path = root / rp if rp else None
            md_text = _read_text(md_path) if md_path and md_path.exists() else ""

            try:
                ext = json.loads(raw.get("extension") or "{}") if raw.get("extension") else {}
            except json.JSONDecodeError:
                ext = {}

            if ntype == "account":
                row = passwords.get(d.get("id", ""), {})
                account = ext.get("account") or (d.get("normalized") or {}).get("account") or ""
                password = row.get("password") or (d.get("normalized") or {}).get("password") or ""
                remark = ext.get("description") or row.get("remark") or ""
                content = _norm_newlines(raw.get("content") or "")
            elif ntype == "link":
                url = ext.get("url") or (d.get("normalized") or {}).get("url") or ""
                description = _norm_newlines(raw.get("content") or "")
                content = ""
            elif ntype == "gallery":
                imgs = ext.get("images") or (d.get("normalized") or {}).get("images") or []
                for u in imgs:
                    if u in uri_map:
                        images.append(uri_map[u])
                    elif u.startswith("timo://"):
                        report.missing_attachments.append(f"{u}（无映射）")
                    else:
                        images.append(u)
                description = _norm_newlines(raw.get("content") or "")
                # 可读 md 里的图片引用也一并收集（兜底）
                for m in IMG_RE.finditer(md_text):
                    rel = f"attachments/{m.group(2)}"
                    if rel not in images:
                        images.append(rel)
                content = ""
            elif ntype == "date":
                date_info = {
                    "type": ext.get("type", 0),
                    "year": ext.get("year"),
                    "month": ext.get("month"),
                    "dayOfMonth": ext.get("dayOfMonth"),
                    "isLunar": bool(ext.get("isLunar")),
                    "dayOfWeek": ext.get("dayOfWeek", -1),
                }
                description = _norm_newlines(raw.get("content") or "")
            elif ntype == "article":
                content = _strip_leading_title(raw.get("content") or "", title)
                content, _ = rewrite_md(content)
            else:  # note
                content = _norm_newlines(raw.get("content") or "")
                if not content and md_text:
                    content = _norm_newlines(md_text)
                content, _ = rewrite_md(content)

            note = Note(
                id=d.get("id") or lib.new_id(),
                topic_id=d.get("topicId") or "",
                type=ntype,
                state=d.get("state") or "active",
                title=title,
                color=d.get("color"),
                created_at=d.get("createdAt") or "",
                updated_at=d.get("updatedAt") or "",
                deleted_at=d.get("deletedAt"),
                archived_at=d.get("archivedAt"),
                pinned_at=d.get("pinnedAt"),
                url=url,
                description=description,
                images=images,
                account=account,
                password=password,
                remark=remark,
                date=date_info,
                order=float(idx),
            )
            # 主题不存在时挂到一个占位主题，避免丢数据
            if note.topic_id not in lib.topics:
                placeholder = "00000000-0000-0000-0000-000000000000"
                if placeholder not in lib.topics:
                    lib.topics[placeholder] = Topic(
                        id=placeholder, name="（未分类）", created_at=now_iso(), updated_at=now_iso(), order=9999
                    )
                note.topic_id = placeholder
            lib.notes[note.id] = note
            lib._content[note.id] = content
            p = lib.note_path(note.id)
            p.write_text(content, encoding="utf-8", newline="\n")
            report.notes += 1
            if progress and (idx % 25 == 0 or idx == total - 1):
                progress(idx + 1, total)

        lib.save()
        return report
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
