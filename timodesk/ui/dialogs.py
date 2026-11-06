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
