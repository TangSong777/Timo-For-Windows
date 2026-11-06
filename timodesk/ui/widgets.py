"""自绘列表控件：主题条目与笔记卡片。"""
from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

from .theme import C


def human_time(iso: str | None) -> str:
    """把 ISO 时间转成「今天 14:03 / 昨天 / 3 天前 / 2024-05-01」。"""
    if not iso:
        return ""
    try:
        txt = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(txt).astimezone()
    except Exception:
        return iso[:10]
    now = datetime.now().astimezone()
    d = (now.date() - dt.date()).days
    if d == 0:
        return dt.strftime("今天 %H:%M")
    if d == 1:
        return dt.strftime("昨天 %H:%M")
    if d < 7:
        return f"{d} 天前"
    if dt.year == now.year:
        return dt.strftime("%m-%d")
    return dt.strftime("%Y-%m-%d")


def _wrap_lines(text: str, fm: QFontMetrics, width: int, max_lines: int) -> list[str]:
    """按像素宽度折行，返回至多 max_lines 行。"""
    text = " ".join(text.split())
    if not text:
        return []
    lines: list[str] = []
    rest = text
    while rest and len(lines) < max_lines:
        lo, hi = 0, len(rest)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if fm.horizontalAdvance(rest[:mid]) <= width:
                lo = mid
            else:
                hi = mid - 1
        if lo == 0:
            lo = 1
        lines.append(rest[:lo])
        rest = rest[lo:]
    if rest and lines:
        last = lines[-1]
        while last and fm.horizontalAdvance(last + "…") > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


class NoteCardDelegate(QStyledItemDelegate):
    """笔记列表卡片：类型 + 摘要 + 时间 + 颜色条 + 置顶。"""

    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.lib = lib

    def sizeHint(self, option, index) -> QSize:
        return QSize(280, 98)

    def paint(self, painter: QPainter, option, index):
        note = self.lib.notes.get(index.data(Qt.UserRole))
        if not note:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        r = option.rect.adjusted(6, 3, -6, -3)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        bg = QColor("#ececec" if selected else (C["card_hover"] if hovered else C["card"]))
        painter.setBrush(bg)
        painter.setPen(QPen(QColor("#d9d9d9" if selected else C["line_soft"]), 1))
        painter.drawRoundedRect(r, 10, 10)

        if note.color:
            bar = QRect(r.left(), r.top() + 10, 3, r.height() - 20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(note.color))
            painter.drawRoundedRect(bar, 1.5, 1.5)

        left = r.left() + (16 if note.color else 13)
        width = r.width() - (left - r.left()) - 13

        content = self.lib.content(note.id)
        title = note.display_title(content)

        f_title = QFont(option.font)
        f_title.setPixelSize(14)
        f_title.setWeight(QFont.DemiBold)
        painter.setFont(f_title)
        painter.setPen(QColor(C["ink"]))
        fm = QFontMetrics(f_title)
        pin = "  置顶" if note.pinned_at else ""
        t = fm.elidedText(title + pin, Qt.ElideRight, width)
        painter.drawText(QRect(left, r.top() + 8, width, 20), Qt.AlignLeft | Qt.AlignVCenter, t)

        body = content if note.type not in ("gallery", "link", "account", "date") else ""
        if note.type == "link":
            body = (note.url or "") + ("  " + note.description if note.description else "")
        elif note.type == "account":
            body = note.account + (" · " + note.remark if note.remark else "")
        elif note.type == "date" and note.date:
            body = _date_text(note.date)
        elif note.type == "gallery":
            body = f"{len(note.images)} 张图片" + (("  " + note.description) if note.description else "")

        f_body = QFont(option.font)
        f_body.setPixelSize(12)
        painter.setFont(f_body)
        painter.setPen(QColor(C["muted"]))
        fm2 = QFontMetrics(f_body)
        if body.strip() == title.strip():
            body = "\n".join(body.splitlines()[1:])
        lines = _wrap_lines(body, fm2, width, 2)
        y = r.top() + 30
        for ln in lines:
            painter.drawText(QRect(left, y, width, 18), Qt.AlignLeft | Qt.AlignVCenter, ln)
            y += 17
        if not lines:
            painter.setPen(QColor(C["faint"]))
            painter.drawText(QRect(left, y, width, 18), Qt.AlignLeft | Qt.AlignVCenter, "（空白）")

        painter.setPen(QColor(C["faint"]))
        f_meta = QFont(option.font)
        f_meta.setPixelSize(10)
        painter.setFont(f_meta)
        meta = f"{_TYPE_MARK.get(note.type, '')} · {human_time(note.updated_at or note.created_at)}"
        painter.drawText(QRect(left, r.bottom() - 21, width, 16), Qt.AlignLeft | Qt.AlignVCenter, meta)
        painter.restore()


_TYPE_MARK = {
    "note": "便签",
    "article": "文章",
    "gallery": "图库",
    "link": "链接",
    "date": "日子",
    "account": "账号",
}


def _date_text(d: dict) -> str:
    t = d.get("type", 0)
    lunar = "农历" if d.get("isLunar") else "公历"
    if t == 0:
        return f"{d.get('year')}年{d.get('month')}月{d.get('dayOfMonth')}日 · {lunar}"
    if t == 1:
        return f"每年 {d.get('month')}月{d.get('dayOfMonth')}日 · {lunar}"
    return f"{d.get('month')}月{d.get('dayOfMonth')}日"


class TopicDelegate(QStyledItemDelegate):
    """主题条目：名称 + 计数 + 选中态。"""

    def __init__(self, lib, parent=None):
        super().__init__(parent)
        self.lib = lib

    def sizeHint(self, option, index) -> QSize:
        return QSize(180, 34)

    def paint(self, painter: QPainter, option, index):
        topic = index.data(Qt.UserRole)
        if not topic:
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = option.rect.adjusted(4, 1, -6, -1)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        if selected or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(C["green_soft"] if selected else C["card"]))
            painter.drawRoundedRect(r, 8, 8)

        cnt = self.lib.note_counts().get(topic.id, 0)

        archived = getattr(topic, "state", "active") == "archived"
        name_font = QFont(option.font)
        name_font.setPixelSize(13)
        name_font.setWeight(QFont.DemiBold if selected else QFont.Normal)
        painter.setFont(name_font)
        painter.setPen(QColor(C["green_dark"] if selected else (C["faint"] if archived else C["ink"])))
        fm = QFontMetrics(name_font)
        name = fm.elidedText(topic.name, Qt.ElideRight, r.width() - 46)
        painter.drawText(QRect(r.left() + 10, r.top(), r.width() - 46, r.height()), Qt.AlignLeft | Qt.AlignVCenter, name)

        if cnt:
            meta = QFont(option.font)
            meta.setPixelSize(10)
            painter.setFont(meta)
            painter.setPen(QColor(C["green"] if selected else C["faint"]))
            painter.drawText(QRect(r.right() - 40, r.top(), 34, r.height()), Qt.AlignRight | Qt.AlignVCenter, str(cnt))
        painter.restore()
