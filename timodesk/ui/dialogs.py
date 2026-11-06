"""自绘对话框：消息、确认、进度。全部无边框，与主窗口风格一致。"""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from .theme import C
from .title_bar import FramelessDialog

_BTN_QSS = f"""
QPushButton#Primary {{
    background: {C['ink']}; color: {C['on_ink']}; border: none;
    border-radius: 8px; padding: 9px 22px; font-size: 13px;
}}
QPushButton#Primary:hover {{ background: {C['btn_hover']}; }}
QPushButton#Plain {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 8px; padding: 9px 22px; color: {C['ink']}; font-size: 13px;
}}
QPushButton#Plain:hover {{ border-color: {C['ink']}; }}
QPushButton#Link {{
    background: transparent; border: none; color: {C['faint']}; font-size: 12px;
}}
QPushButton#Link:hover {{ color: {C['ink']}; }}
"""


def _button(text: str, name: str = "Plain") -> QPushButton:
    b = QPushButton(text)
    b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(36)
    return b


class MessageDialog(FramelessDialog):
    def __init__(self, parent, title: str, text: str, ok_text="好", cancel_text=None):
        super().__init__(parent, title)
        self.ok = False
        self.setStyleSheet(_BTN_QSS + f"QLabel#MsgText{{color:{C['ink']};font-size:13px;}}")

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(28, 22, 28, 20)
        lay.setSpacing(18)

        lab = QLabel(text, objectName="MsgText")
        lab.setWordWrap(True)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(lab, 0, Qt.AlignTop)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)
        if cancel_text:
            b = _button(cancel_text)
            b.clicked.connect(self.reject)
            row.addWidget(b)
        ok = _button(ok_text, "Primary")
        ok.clicked.connect(self._accept)
        ok.setDefault(True)
        row.addWidget(ok)
        lay.addLayout(row)

        self.setMinimumWidth(420)
        self.adjustSize()
        self.add_edge()

    def _accept(self):
        self.ok = True
        self.accept()


class ProgressDialog(FramelessDialog):
    def __init__(self, parent, title: str, text: str):
        super().__init__(parent, title)
        self._canceled = False
        self.setStyleSheet(_BTN_QSS + f"""
            QLabel#ProgText {{ color: {C['ink']}; font-size: 13px; }}
            QProgressBar {{ background: {C['line_soft']}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {C['ink']}; border-radius: 3px; }}
        """)

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(28, 22, 28, 20)
        lay.setSpacing(14)

        self.label = QLabel(text, objectName="ProgText")
        self.label.setWordWrap(True)
        lay.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setRange(0, 100)
        lay.addWidget(self.bar)

        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_cancel = _button("取消", "Link")
        self.btn_cancel.setMinimumHeight(26)
        self.btn_cancel.clicked.connect(self._cancel)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.setFixedWidth(460)
        self.add_edge()

    def _cancel(self):
        self._canceled = True
        self.label.setText("正在取消…")

    def was_canceled(self) -> bool:
        return self._canceled

    def set_progress(self, done: int, total: int, text: str | None = None):
        self.bar.setMaximum(max(1, total))
        self.bar.setValue(done)
        if text:
            self.label.setText(text)


def info(parent, title: str, text: str, ok_text="好") -> None:
    MessageDialog(parent, title, text, ok_text).exec_()


def confirm(parent, title: str, text: str, ok_text="继续", cancel_text="取消") -> bool:
    d = MessageDialog(parent, title, text, ok_text, cancel_text)
    d.exec_()
    return d.ok


def error(parent, title: str, text: str) -> None:
    MessageDialog(parent, title, text, "好").exec_()


class ReminderDialog(FramelessDialog):
    """设置提醒时间：快捷按钮 + 日期 + 时间。"""

    def __init__(self, parent, when=None, has_reminder: bool = False):
        from datetime import datetime, timedelta

        super().__init__(parent, "设置提醒")
        self.setStyleSheet(_BTN_QSS)
        from PyQt5.QtCore import QDate, QTime
        from PyQt5.QtWidgets import QDateEdit, QHBoxLayout, QLabel, QPushButton, QTimeEdit

        base = when or (datetime.now() + timedelta(hours=1))
        self.cleared = False
        self.result_when: datetime | None = None

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(14)

        tip = QLabel("到时间后会从右下角弹出提醒。")
        tip.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(tip)

        quick = QHBoxLayout()
        quick.setSpacing(8)
        now = datetime.now()
        for label, target in (
            ("一小时后", now + timedelta(hours=1)),
            ("今天 20:00", now.replace(hour=20, minute=0, second=0, microsecond=0)),
            ("明天 9:00", (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)),
        ):
            b = QPushButton(label)
            b.setObjectName("Plain")
            b.clicked.connect(lambda _=False, t=target: self._set(t))
            quick.addWidget(b)
        quick.addStretch(1)
        lay.addLayout(quick)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        self.date.setDate(QDate(base.year, base.month, base.day))
        self.time = QTimeEdit()
        self.time.setDisplayFormat("HH:mm")
        self.time.setTime(QTime(base.hour, base.minute))
        row.addWidget(self.date, 2)
        row.addWidget(self.time, 1)
        row.addStretch(1)
        lay.addLayout(row)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        if has_reminder:
            b_clear = QPushButton("删除提醒")
            b_clear.setObjectName("Link")
            b_clear.clicked.connect(self._clear)
            btns.addWidget(b_clear)
        btns.addStretch(1)
        b_cancel = QPushButton("取消")
        b_cancel.setObjectName("Plain")
        b_cancel.clicked.connect(self.reject)
        b_ok = QPushButton("确定")
        b_ok.setObjectName("Primary")
        b_ok.clicked.connect(self._accept)
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        lay.addLayout(btns)
        lay.addStretch(1)

        self.setMinimumWidth(420)
        self.adjustSize()
        self.add_edge()

    def _set(self, dt):
        from PyQt5.QtCore import QDate, QTime

        self.date.setDate(QDate(dt.year, dt.month, dt.day))
        self.time.setTime(QTime(dt.hour, dt.minute))

    def _accept(self):
        from datetime import datetime

        d = self.date.date()
        t = self.time.time()
        self.result_when = datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())
        self.accept()

    def _clear(self):
        self.cleared = True
        self.result_when = None
        self.accept()


class BackupDialog(FramelessDialog):
    """备份列表：立即备份、从备份恢复。"""

    def __init__(self, parent, lib):
        super().__init__(parent, "备份与恢复")
        from PyQt5.QtWidgets import QHBoxLayout, QListWidget, QPushButton

        self.setStyleSheet(_BTN_QSS)
        self.lib = lib
        self.restored = False
        self.setFixedSize(520, 460)

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(12)

        tip = QLabel("每次启动最多每天自动备份一次，只保留最近 7 份。备份包含笔记正文与库结构，不含图片附件。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(tip)

        self.list = QListWidget()
        self.list.setObjectName("BackupList")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setStyleSheet(
            f"QListWidget#BackupList{{background:#fff;border:1px solid {C['card_border']};border-radius:10px;padding:4px;}}"
            f"QListWidget#BackupList::item{{padding:7px 8px;border-radius:6px;}}"
            f"QListWidget#BackupList::item:selected{{background:#f0f0f2;color:{C['ink']};}}"
        )
        lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        row.setSpacing(8)
        fixed = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        b_now = QPushButton("立即备份")
        b_now.setSizePolicy(fixed)
        b_now.setObjectName("Plain")
        b_now.clicked.connect(self._make_now)
        row.addWidget(b_now)
        self.b_restore = QPushButton("恢复所选")
        self.b_restore.setSizePolicy(fixed)
        self.b_restore.setObjectName("Primary")
        self.b_restore.clicked.connect(self._restore)
        row.addWidget(self.b_restore)
        row.addStretch(1)
        b_open = QPushButton("打开文件夹")
        b_open.setSizePolicy(fixed)
        b_open.setMaximumWidth(92)
        b_open.setObjectName("Link")
        b_open.clicked.connect(self._open_dir)
        row.addWidget(b_open)
        b_close = _button("关闭", "Plain")
        b_close.clicked.connect(self.accept)
        row.addWidget(b_close)
        lay.addLayout(row)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(self.status)
        self._reload()

    def _reload(self):
        from PyQt5.QtWidgets import QListWidgetItem

        from .. import backup

        self.list.clear()
        items = backup.list_all(self.lib.root)
        for it in items:
            size = it["size"] / 1024
            label = it["name"].replace("timo-backup-", "").replace(".zip", "")
            text = f"{label}    ·    {it['mtime']:%m-%d %H:%M}    ·    {size:.0f} KB"
            row = QListWidgetItem(text)
            row.setData(0x0100, str(it["path"]))
            self.list.addItem(row)
        if items:
            self.list.setCurrentRow(0)
        self.b_restore.setEnabled(bool(items))
        self.status.setText(f"共 {len(items)} 份备份。" if items else "还没有备份。")

    def _make_now(self):
        from .. import backup

        try:
            p = backup.create(self.lib)
        except Exception as e:
            self.status.setText(f"备份失败：{e}")
            return
        self._reload()
        self.status.setText(f"已备份到 {p.name}")

    def _restore(self):
        from .. import backup

        item = self.list.currentItem()
        if item is None:
            return
        path = item.data(0x0100)
        if not confirm(self, "恢复备份", "当前库会被这份备份覆盖（覆盖前会先备份一次现状）。\n确定继续吗？", "恢复"):
            return
        try:
            backup.restore(self.lib, path)
        except Exception as e:
            error(self, "恢复失败", str(e))
            return
        self.restored = True
        self.accept()

    def _open_dir(self):
        from .. import backup
        import os

        d = backup.backup_dir(self.lib.root)
        try:
            os.startfile(str(d))
        except Exception:
            pass


class ImportModeDialog(FramelessDialog):
    """已有数据时选择：合并（只加新的）或替换（清空后导入）。"""

    def __init__(self, parent, note_count: int):
        super().__init__(parent, "导入 Timo 数据")
        from PyQt5.QtWidgets import QHBoxLayout

        self.setStyleSheet(_BTN_QSS)
        self.mode: str | None = None
        self.setFixedSize(460, 232)

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(30, 22, 30, 22)
        lay.setSpacing(10)

        t = QLabel("当前库里有 %d 条笔记" % note_count)
        t.setStyleSheet(f"font-size:15px;font-weight:600;color:{C['ink']};")
        lay.addWidget(t)

        d1 = QLabel("合并导入：保留现在的笔记，只把包里没有的新笔记加进来。")
        d1.setWordWrap(True)
        d1.setStyleSheet(f"color:{C['ink_soft']};font-size:12px;")
        lay.addWidget(d1)

        d2 = QLabel("替换导入：清空当前库，用包里的内容整体替换（动手前会先备份一份）。")
        d2.setWordWrap(True)
        d2.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(d2)

        lay.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(8)
        b_cancel = _button("取消", "Link")
        b_cancel.clicked.connect(self.reject)
        row.addWidget(b_cancel)
        row.addStretch(1)
        b_replace = _button("替换导入", "Plain")
        b_replace.clicked.connect(lambda: self._pick("replace"))
        row.addWidget(b_replace)
        b_merge = _button("合并导入", "Primary")
        b_merge.clicked.connect(lambda: self._pick("merge"))
        row.addWidget(b_merge)
        lay.addLayout(row)

    def _pick(self, mode: str):
        self.mode = mode
        self.accept()


class AboutDialog(FramelessDialog):
    """关于：版本、数据统计、快捷键。"""

    SHORTCUTS = [
        ("Ctrl+N", "新建笔记"),
        ("Ctrl+Shift+N", "新建主题"),
        ("Ctrl+F", "搜索全部笔记（光标在正文里则在本篇内查找）"),
        ("Ctrl+S", "立即保存"),
        ("Ctrl+E", "编辑 / 分屏 / 预览切换"),
        ("Ctrl+B / I / K", "粗体、斜体、插入链接"),
        ("Ctrl+Shift+T", "待办清单"),
        ("Esc", "关闭查找条"),
        ("双击标题栏", "最大化 / 还原"),
    ]

    def __init__(self, parent, lib, version: str):
        super().__init__(parent, "关于")
        from PyQt5.QtWidgets import QHBoxLayout

        self.setStyleSheet(_BTN_QSS)
        self.setFixedSize(520, 540)

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(32, 24, 32, 22)
        lay.setSpacing(10)

        title = QLabel("Timo For Windows")
        title.setStyleSheet(f"font-size:19px;font-weight:600;color:{C['ink']};")
        lay.addWidget(title)

        sub = QLabel(f"版本 {version} · Windows 本地笔记，数据只在自己电脑上")
        sub.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(sub)

        notes = [n for n in lib.notes.values() if n.state != "trash"]
        topics = [t for t in lib.topics.values() if t.state != "trash"]
        chars = sum(len(lib.content(n.id)) for n in notes)
        att = len([p for p in lib.attachments_dir.glob("*") if p.is_file()]) if lib.attachments_dir.exists() else 0

        stat = QLabel(f"{len(topics)} 个主题 · {len(notes)} 条笔记 · {att} 个附件 · 约 {chars:,} 字")
        stat.setStyleSheet(
            f"background:#fafafb;border:1px solid {C['card_border']};border-radius:10px;"
            f"padding:11px 14px;color:{C['ink']};font-size:13px;"
        )
        lay.addWidget(stat)

        lab = QLabel("快捷键")
        lab.setStyleSheet(f"color:{C['muted']};font-size:11px;margin-top:6px;")
        lay.addWidget(lab)
        for key, desc in self.SHORTCUTS:
            row = QHBoxLayout()
            row.setSpacing(10)
            k = QLabel(key)
            k.setFixedWidth(120)
            k.setStyleSheet(
                f"color:{C['ink']};font-size:12px;font-family:'Consolas','Microsoft YaHei UI';"
                f"background:{C['input_bg']};border-radius:6px;padding:3px 8px;"
            )
            row.addWidget(k)
            d = QLabel(desc)
            d.setStyleSheet(f"color:{C['ink_soft']};font-size:12px;")
            row.addWidget(d, 1)
            lay.addLayout(row)

        lay.addStretch(1)
        bottom = QHBoxLayout()
        path = QLabel(f"数据目录：{Path(lib.root).resolve()}")
        path.setStyleSheet(f"color:{C['faint']};font-size:11px;")
        path.setToolTip(str(lib.root))
        path.setMinimumWidth(10)
        bottom.addWidget(path, 1)
        btn = _button("好", "Primary")
        btn.clicked.connect(self.accept)
        bottom.addWidget(btn)
        lay.addLayout(bottom)
