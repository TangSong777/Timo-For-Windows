"""自绘对话框：消息、确认、进度。全部无边框，与主窗口风格一致。"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
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
