"""把本地库导出成 Timo「可读数据导出」ZIP，结构与官方导出一致，便于备份/迁移/对照。"""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from pathlib import Path

from .store import Library, Note, TYPE_CODE, TYPE_LABELS, now_iso

ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]')
STATE_DIR = {"active": "active", "archived": "archived", "trash": "trash"}
TYPE_FILE = {"note": "笔记", "article": "标题", "gallery": "图库", "link": "链接", "date": "日子", "account": "账号"}


def short_id(s: str) -> str:
    s = (s or "").replace("@", "")
    s = re.sub(r"[^0-9a-zA-Z]", "", s)
    return s[-8:] or "00000000"


def safe_name(s: str, fallback: str = "未命名") -> str:
    s = ILLEGAL.sub("_", (s or "").strip())
    s = s.strip(" .")
    return s[:60] or fallback


def md_rel_to_export(text: str) -> str:
    """attachments/x → ../../../attachments/x（与官方导出的相对路径一致）。"""
    return re.sub(r"!\[([^\]]*)\]\(attachments/([^)\s]+)\)", r"![\1](../../../attachments/\2)", text)


def note_markdown(n: Note, content: str) -> str:
    if n.type == "article":
        return f"# {n.title or ''}\n\n{md_rel_to_export(content)}".rstrip() + "\n"
    if n.type == "gallery":
        lines = ["# 图库", ""]
        for rel in n.images:
            lines.append(f"![]({'../../../' + rel if rel.startswith('attachments/') else rel})")
            lines.append("")
        if n.description:
            lines.append(md_rel_to_export(n.description))
        return "\n".join(lines).rstrip() + "\n"
    if n.type == "link":
        return f"# 链接\n\n[{n.url or ''}]({n.url or ''})\n\n{md_rel_to_export(content)}".rstrip() + "\n"
    if n.type == "date":
        d = n.date or {}
        t = "每年" if d.get("type") == 1 else "固定日期"
        lunar = "是" if d.get("isLunar") else "否"
        lines = [f"# {n.title or ''}", "", f"- 日期类型：{t}", f"- 农历：{lunar}"]
        if d.get("type") != 1:
            lines.append(f"- 年：{d.get('year')}")
        lines += [f"- 月：{d.get('month')}", f"- 日：{d.get('dayOfMonth')}"]
        return "\n".join(lines) + "\n"
    if n.type == "account":
        return f"# {n.title or ''}\n\n- 账号：{n.account}\n- 密码：{n.password}\n- 备注：{n.remark}\n"
    return md_rel_to_export(content)


def _headings(text: str) -> list[dict]:
    return [
        {"level": len(m.group(1)), "text": m.group(2).strip()}
        for m in re.finditer(r"^(#{1,6})\s+(.+)$", text or "", re.M)
    ]


def _md_images(text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\((attachments/[^)\s]+)\)", text or "")


def _links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]*\]\((https?://[^)\s]+)\)", text or "")


def _readme(counts: dict) -> str:
    return (
        "Timo 桌面版 · 本地数据导出\n\n"
        "此 ZIP 未加密，包含笔记正文与附件，请妥善保管。\n"
        "content 目录是可直接阅读的 Markdown / CSV 文件，data 目录是机器可读 JSON。\n\n"
        f"导出内容：{counts['topics']} 个主题、{counts['documents']} 条笔记、{counts['attachments']} 个附件\n"
        f"生成时间：{now_iso()}\n"
    )


def export_zip(lib: Library, out: str | Path) -> tuple[Path, dict]:
    """导出为 Timo 兼容 ZIP，返回 (路径, 统计)。"""
    out = Path(out)
    if out.suffix.lower() != ".zip":
        out = out.with_suffix(".zip")

    topics_json = []
    for t in sorted(lib.topics.values(), key=lambda x: (x.order, x.created_at)):
        topics_json.append(
            {
                "id": t.id,
                "name": t.name,
                "locked": bool(t.locked),
                "mode": t.mode or "white",
                "state": t.state,
                "createdAt": t.created_at,
                "updatedAt": t.updated_at,
                "deletedAt": t.deleted_at,
                "archivedAt": t.archived_at,
            }
        )
    topic_names = {t["id"]: t["name"] for t in topics_json}

    # 先生成所有文件内容，保证 readablePath 与实际写入完全一致
    files: dict[str, str] = {}
    used: set[str] = set()
    docs_json = []
    accounts_rows = []

    for n in lib.notes.values():
        state = STATE_DIR.get(n.state, "active")
        tname = safe_name(topic_names.get(n.topic_id, ""), "未分类")
        sub = f"{tname}__{short_id(n.topic_id)}"
        title = n.title or ""
        if n.type in ("article", "date"):
            fname = f"{safe_name(title, TYPE_LABELS[n.type])}__{short_id(n.id)}.md"
        else:
            fname = f"{TYPE_FILE.get(n.type, '笔记')}__{short_id(n.id)}.md"
        rel = f"content/{state}/{sub}/{fname}"
        k = rel.lower()
        i = 1
        while k in used:
            rel = f"content/{state}/{sub}/{Path(fname).stem}-{i}.md"
            k = rel.lower()
            i += 1
        used.add(k)

        content = lib.content(n.id)
        files[rel] = note_markdown(n, content)

        ext: dict = {}
        if n.type == "gallery":
            ext["images"] = [f"timo://file-store/{Path(r).name}" for r in n.images]
        elif n.type == "link":
            ext["url"] = n.url or ""
        elif n.type == "account":
            ext.update({"account": n.account, "description": n.remark, "token": ""})
        elif n.type == "date":
            d = n.date or {}
            ext = {
                "dayOfMonth": d.get("dayOfMonth", 1),
                "dayOfWeek": d.get("dayOfWeek", -1),
                "isLunar": bool(d.get("isLunar")),
                "month": d.get("month", 1),
                "type": d.get("type", 0),
                "year": d.get("year"),
            }
        else:
            ext = {
                "charsCount": len(content.strip()),
                "headings": _headings(content),
                "images": [f"timo://file-store/{Path(r).name}" for r in _md_images(content)],
                "links": _links(content),
                "paragraphsCount": len([p for p in content.split("\n\n") if p.strip()]),
            }
            if n.type == "article" and n.title:
                ext["summary"] = next((ln for ln in content.splitlines() if ln.strip()), "")[:120]
                ext["title"] = n.title

        raw_content = content
        if n.type in ("gallery", "link", "date", "account") and not content:
            raw_content = n.description
        raw = {
            "typeCode": TYPE_CODE.get(n.type, 0),
            "title": n.title,
            "content": raw_content,
            "extension": json.dumps(ext, ensure_ascii=False, separators=(",", ":")),
            "dataVersion": 3,
        }

        normalized: dict = {}
        if n.type == "note":
            normalized = {"content": content}
        elif n.type == "article":
            normalized = {"title": n.title, "content": content}
        elif n.type == "gallery":
            normalized = {"description": n.description, "images": ext.get("images", [])}
        elif n.type == "link":
            normalized = {"url": n.url or "", "description": n.description or content}
        elif n.type == "date":
            normalized = {"title": n.title, "date": ext, "description": n.description or content}
        elif n.type == "account":
            normalized = {"title": n.title, "account": n.account, "password": n.password, "remark": n.remark}
            accounts_rows.append(
                {
                    "id": n.id,
                    "topic_id": n.topic_id,
                    "title": n.title or "",
                    "account": n.account,
                    "password": n.password,
                    "remark": n.remark,
                    "created_at": n.created_at,
                    "updated_at": n.updated_at,
                }
            )

        docs_json.append(
            {
                "id": n.id,
                "topicId": n.topic_id,
                "type": n.type,
                "state": state,
                "readablePath": rel,
                "color": n.color,
                "createdAt": n.created_at,
                "updatedAt": n.updated_at,
                "deletedAt": n.deleted_at,
                "archivedAt": n.archived_at,
                "pinnedAt": n.pinned_at,
                "normalized": normalized,
                "raw": raw,
            }
        )

    attachments_meta = []
    att_dir = lib.attachments_dir
    if att_dir.exists():
        for f in sorted(att_dir.iterdir()):
            if f.is_file():
                attachments_meta.append(
                    {
                        "uri": f"timo://file-store/{f.name}",
                        "path": f"attachments/{f.name}",
                        "originalName": f.name,
                        "suffix": f.suffix.lstrip("."),
                        "size": f.stat().st_size,
                    }
                )

    counts = {
        "topics": len(topics_json),
        "documents": len(docs_json),
        "accounts": len(accounts_rows),
        "attachments": len(attachments_meta),
        "missingAttachments": 0,
    }
    manifest = {
        "schemaVersion": 1,
        "scope": "local_export",
        "status": "complete",
        "exportedAt": now_iso(),
        "app": {"versionName": "Timo Desktop 1.0", "versionCode": 1},
        "counts": counts,
        "topicOrder": [t["id"] for t in topics_json],
        "warnings": [],
        "attachments": attachments_meta,
    }

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", _readme(counts))
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        z.writestr(
            "data/topics.json",
            json.dumps(
                {"schemaVersion": 1, "topicOrder": [t["id"] for t in topics_json], "topics": topics_json},
                ensure_ascii=False,
                indent=2,
            ),
        )
        z.writestr("data/documents.json", json.dumps({"schemaVersion": 1, "documents": docs_json}, ensure_ascii=False, indent=2))
        if accounts_rows:
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(accounts_rows[0].keys()), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(accounts_rows)
            z.writestr("content/accounts.csv", "\ufeff" + buf.getvalue())
        for rel, text in files.items():
            z.writestr(rel, text)
        if att_dir.exists():
            for f in att_dir.iterdir():
                if f.is_file():
                    z.write(f, f"attachments/{f.name}")
    return out, counts
