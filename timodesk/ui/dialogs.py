"""自绘对话框：消息、确认、进度。全部无边框，与主窗口风格一致。"""
from __future__ import annotations

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
    background: {C['ink']}; color: #ffffff; border: none;
    border-radius: 8px; padding: 9px 22px; font-size: 13px;
}}
QPushButton#Primary:hover {{ background: #000000; }}
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

    def __init__(self, parent, when: "datetime | None" = None, has_reminder: bool = False):
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


class UnlockDialog(FramelessDialog):
    """启动时的应用锁：输密码才能进入。"""

    def __init__(self, parent, settings):
        super().__init__(parent, "Timo For Windows")
        from PyQt5.QtWidgets import QLineEdit

        self.settings = settings
        self.setStyleSheet(_BTN_QSS)
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(12)

        title = QLabel("已开启应用锁")
        title.setStyleSheet(f"font-size:16px;font-weight:600;color:{C['ink']};")
        lay.addWidget(title)
        tip = QLabel("输入密码后进入。")
        tip.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(tip)

        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setPlaceholderText("密码")
        self.pwd.setStyleSheet(
            f"QLineEdit{{background:{C['card']};border:1px solid {C['line']};border-radius:8px;"
            f"padding:8px 10px;font-size:14px;}}"
            f"QLineEdit:focus{{border-color:{C['ink']};}}"
        )
        self.pwd.returnPressed.connect(self._try)
        lay.addWidget(self.pwd)

        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{C['ink']};font-size:12px;")
        lay.addWidget(self.err)

        row = QHBoxLayout()
        row.addStretch(1)
        b_quit = QPushButton("退出")
        b_quit.setObjectName("Link")
        b_quit.clicked.connect(self.reject)
        b_ok = QPushButton("解锁")
        b_ok.setObjectName("Primary")
        b_ok.clicked.connect(self._try)
        row.addWidget(b_quit)
        row.addWidget(b_ok)
        lay.addLayout(row)

        self.setFixedWidth(380)
        self.adjustSize()
        self.add_edge()

    def _try(self):
        if self.settings.check_password(self.pwd.text()):
            self.accept()
        else:
            self.err.setText("密码不对，再试一次。")
            self.pwd.selectAll()
            self.pwd.setFocus()


class LockDialog(FramelessDialog):
    """设置 / 修改 / 关闭应用锁。"""

    def __init__(self, parent, settings):
        super().__init__(parent, "应用锁")
        from PyQt5.QtWidgets import QLineEdit

        self.settings = settings
        self.changed = False
        self.old_enabled = settings.lock_enabled()
        self.setStyleSheet(_BTN_QSS)

        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(10)

        style = (
            f"QLineEdit{{background:{C['card']};border:1px solid {C['line']};border-radius:8px;"
            f"padding:8px 10px;font-size:13px;}}"
            f"QLineEdit:focus{{border-color:{C['ink']};}}"
        )

        def add_pwd(placeholder: str):
            e = QLineEdit()
            e.setEchoMode(QLineEdit.Password)
            e.setPlaceholderText(placeholder)
            e.setStyleSheet(style)
            lay.addWidget(e)
            return e

        tip = QLabel("应用锁只拦在本机打开程序的人；数据本身不加密，别把 Data 目录发给别人。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        lay.addWidget(tip)

        self.cur = add_pwd("当前密码") if self.old_enabled else None
        self.new = add_pwd("新密码（至少 4 位）")
        self.new2 = add_pwd("再输一次新密码")
        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{C['ink']};font-size:12px;")
        lay.addWidget(self.err)

        row = QHBoxLayout()
        if self.old_enabled:
            b_off = QPushButton("关闭应用锁")
            b_off.setObjectName("Link")
            b_off.clicked.connect(self._turn_off)
            row.addWidget(b_off)
        row.addStretch(1)
        b_cancel = QPushButton("取消")
        b_cancel.setObjectName("Plain")
        b_cancel.clicked.connect(self.reject)
        b_ok = QPushButton("保存")
        b_ok.setObjectName("Primary")
        b_ok.clicked.connect(self._save)
        row.addWidget(b_cancel)
        row.addWidget(b_ok)
        lay.addLayout(row)

        self.setMinimumWidth(420)
        self.adjustSize()
        self.add_edge()

    def _save(self):
        if self.cur is not None and not self.settings.check_password(self.cur.text()):
            self.err.setText("当前密码不对。")
            return
        p1, p2 = self.new.text(), self.new2.text()
        if len(p1) < 4:
            self.err.setText("新密码至少 4 位。")
            return
        if p1 != p2:
            self.err.setText("两次输入的密码不一致。")
            return
        self.settings.set_password(p1)
        self.changed = True
        self.accept()

    def _turn_off(self):
        if self.cur is not None and not self.settings.check_password(self.cur.text()):
            self.err.setText("要关闭应用锁，需要先输当前密码。")
            return
        self.settings.clear_password()
        self.changed = True
        self.accept()


class BackupDialog(FramelessDialog):
    """备份列表：立即备份、从备份恢复。"""

    def __init__(self, parent, lib):
        super().__init__(parent, "备份与恢复")
        from PyQt5.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QPushButton

        from .. import backup

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
