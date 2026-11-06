"""笔记编辑器：便签式正文 + 类型专属视图 + Markdown 预览。

不同笔记类型在 Timo 里本来就有各自的样式，这里按同样的思路分开呈现：
* note / article —— Markdown 正文 + 预览
* gallery       —— 图片墙（点击看大图）+ 说明
* account       —— 账号卡片（账号 / 密码 / 备注，可复制）
* link          —— 链接卡片 + 说明
* date          —— 日子卡片（大号日期）+ 说明
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..render import render
from ..store import TYPE_LABELS, Library, Note
from .theme import C, NOTE_COLORS, color_icon
from .widgets import AutoFadeScrollBar
from .widgets import human_time


# ---------------------------------------------------------------- 基础控件
class MarkdownEdit(QPlainTextEdit):
    """正文编辑框：粘贴/拖入图片会发出 imageDropped。"""

    imageDropped = pyqtSignal(str)

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Editor")
        self.setPlaceholderText(placeholder)
        self.setTabChangesFocus(True)
        f = QFont("Microsoft YaHei")
        f.setPixelSize(15)
        self.setFont(f)

    def insertFromMimeData(self, source):  # noqa: N802
        if source.hasImage():
            img = source.imageData()
            if isinstance(img, QImage) and not img.isNull():
                import tempfile

                fd, path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                img.save(path, "PNG")
                self.imageDropped.emit(path)
                return
        super().insertFromMimeData(source)

    def dragEnterEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            urls = [u for u in e.mimeData().urls() if u.isLocalFile()]
            if urls:
                e.acceptProposedAction()
                return
        super().dragEnterEvent(e)

    def dropEvent(self, e):  # noqa: N802
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if u.isLocalFile():
                    self.imageDropped.emit(u.toLocalFile())
            e.acceptProposedAction()
            return
        super().dropEvent(e)


class ImageViewer(QDialog):
    """双击图片后的大图查看。"""

    def __init__(self, paths: list[str], start: int, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.idx = start
        self.setWindowTitle("查看图片")
        self.resize(1000, 720)
        self.setStyleSheet(f"QDialog{{background:{C['ink']};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.label, 1)
        bar = QHBoxLayout()
        bar.setContentsMargins(12, 6, 12, 10)
        prev = QPushButton("‹ 上一张")
        prev.clicked.connect(lambda: self._step(-1))
        bar.addWidget(prev)
        self.counter = QLabel()
        self.counter.setStyleSheet("color:#cfcfcf;")
        bar.addWidget(self.counter, alignment=Qt.AlignCenter)
        nxt = QPushButton("下一张 ›")
        nxt.clicked.connect(lambda: self._step(1))
        bar.addWidget(nxt)
        lay.addLayout(bar)
        self._render()

    def _step(self, d: int):
        if not self.paths:
            return
        self.idx = (self.idx + d) % len(self.paths)
        self._render()

    def _render(self):
        if not self.paths:
            return
        pm = QPixmap(self.paths[self.idx])
        if pm.isNull():
            self.label.setText("图片无法读取")
        else:
            self.label.setPixmap(pm.scaled(self.label.size() * 0.98, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.counter.setText(f"{self.idx + 1} / {len(self.paths)}")

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() == Qt.Key_Left:
            self._step(-1)
        elif e.key() == Qt.Key_Right:
            self._step(1)
        elif e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)


class NoteEditor(QWidget):
    contentChanged = pyqtSignal(str, str, str)  # note_id, content, title
    metaChanged = pyqtSignal()
    requestNewNote = pyqtSignal()

    def __init__(self, lib: Library, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.note: Note | None = None
        self._loading = False
        self._dirty = False
        self._mode = "split"
        self.setObjectName("EditorPane")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()
        self.top_bar.setVisible(False)
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(280)
        self._preview_timer.timeout.connect(self._refresh_preview)

    # ================= 布局 =================
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 顶栏 ----
        top = QWidget(objectName="EditorTopBar")
        self.top_bar = top
        tl = QHBoxLayout(top)
        tl.setContentsMargins(22, 11, 16, 9)
        tl.setSpacing(6)
        self.badge = QLabel("便签", objectName="TypeBadge")
        tl.addWidget(self.badge)
        self.save_state = QLabel("", objectName="SaveState")
        tl.addWidget(self.save_state)
        tl.addStretch(1)
        self.btn_pin = QToolButton()
        self.btn_pin.setText("置顶")
        self.btn_pin.setCheckable(True)
        self.btn_pin.clicked.connect(self._toggle_pin)
        tl.addWidget(self.btn_pin)
        self.btn_color = QToolButton()
        self.btn_color.setText("颜色")
        self.btn_color.setPopupMode(QToolButton.InstantPopup)
        cmenu = QMenu(self)
        for name, col in NOTE_COLORS:
            a = cmenu.addAction(color_icon(col), name)
            a.setData(col)
        cmenu.triggered.connect(lambda a: self._set_color(a.data()))
        self.btn_color.setMenu(cmenu)
        tl.addWidget(self.btn_color)
        self.btn_more = QToolButton()
        self.btn_more.setText("⋯")
        more = QMenu(self)
        more.addAction("归档 / 取消归档", self._toggle_archive)
        more.addAction("复制笔记", self._duplicate)
        more.addSeparator()
        more.addAction("删除到回收站", self._delete)
        self.btn_more.setMenu(more)
        tl.addWidget(self.btn_more)
        root.addWidget(top)

        # ---- 标题 ----
        self.title_wrap = QWidget()
        tw = QHBoxLayout(self.title_wrap)
        tw.setContentsMargins(22, 6, 26, 2)
        self.title_edit = QLineEdit(objectName="NoteTitle")
        self.title_edit.setPlaceholderText("标题")
        self.title_edit.textChanged.connect(self._on_title_changed)
        tw.addWidget(self.title_edit)
        root.addWidget(self.title_wrap)

        # ---- 页面栈 ----
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # 空状态
        self.page_empty = QWidget()
        el = QVBoxLayout(self.page_empty)
        el.setAlignment(Qt.AlignCenter)
        icon = QLabel("✎")
        icon.setStyleSheet(f"font-size:54px;color:{C['line']};")
        icon.setAlignment(Qt.AlignCenter)
        el.addWidget(icon)
        hint = QLabel("选择一条笔记，或新建一条")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color:{C['faint']};font-size:13px;")
        el.addWidget(hint)
        b = QPushButton("新建笔记")
        b.setFixedWidth(132)
        b.clicked.connect(self.requestNewNote.emit)
        el.addWidget(b, alignment=Qt.AlignCenter)
        self.stack.addWidget(self.page_empty)

        self._build_text_page()
        self._build_gallery_page()
        self._build_account_page()
        self._build_link_page()
        self._build_date_page()

        # ---- 底部 ----
        bottom = QWidget()
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(22, 3, 18, 8)
        self.word_label = QLabel("")
        self.word_label.setStyleSheet(f"color:{C['faint']};font-size:11px;")
        bl.addWidget(self.word_label)
        bl.addStretch(1)
        self.time_label = QLabel("")
        self.time_label.setStyleSheet(f"color:{C['faint']};font-size:11px;")
        bl.addWidget(self.time_label)
        root.addWidget(bottom)

    def _build_text_page(self):
        self.page_text = QWidget()
        pl = QVBoxLayout(self.page_text)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        self.format_bar = QFrame(objectName="FormatBar")
        fb = QHBoxLayout(self.format_bar)
        fb.setContentsMargins(10, 4, 10, 4)
        fb.setSpacing(2)
        _groups = (3, 5, 8)
        for _i, (text, tip, cb) in enumerate([
            ("B", "粗体 Ctrl+B", lambda: self._wrap("**", "**")),
            ("I", "斜体 Ctrl+I", lambda: self._wrap("*", "*")),
            ("S", "删除线", lambda: self._wrap("~~", "~~")),
            ("H1", "一级标题", lambda: self._prefix("# ")),
            ("H2", "二级标题", lambda: self._prefix("## ")),
            ("•", "列表", lambda: self._prefix("- ")),
            ("☑", "待办", lambda: self._prefix("- [ ] ")),
            ("❝", "引用", lambda: self._prefix("> ")),
            ("</>", "代码块", lambda: self._wrap("\n```\n", "\n```\n")),
            ("🔗", "链接 Ctrl+K", self._insert_link),
            ("🖼", "插入图片", self._pick_images),
        ]):
            if _i in _groups:
                sep = QFrame()
                sep.setFixedSize(1, 16)
                sep.setStyleSheet(f"background:{C['line']};border:none;")
                fb.addWidget(sep)
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            fb.addWidget(b)
        fb.addStretch(1)
        self.mode_btn = QToolButton()
        self.mode_btn.setPopupMode(QToolButton.InstantPopup)
        mmenu = QMenu(self)
        for m, label in (("edit", "只显示编辑"), ("split", "分屏"), ("preview", "只显示预览")):
            a = mmenu.addAction(label)
            a.setData(m)
        mmenu.triggered.connect(lambda a: self.set_mode(a.data()))
        self.mode_btn.setMenu(mmenu)
        fb.addWidget(self.mode_btn)
        pl.addWidget(self.format_bar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.edit = MarkdownEdit("开始写点什么……\n\n支持简单 Markdown：**粗体**、*斜体*、# 标题、- 列表、> 引用、`代码`")
        self.edit.textChanged.connect(self._on_text_changed)
        self.edit.imageDropped.connect(self._insert_image_file)
        self.preview = QTextBrowser(objectName="Preview")
        self.preview.setOpenExternalLinks(True)
        self.preview.setFrameShape(QFrame.NoFrame)
        self.splitter.addWidget(self.edit)
        self.splitter.addWidget(self.preview)
        pl.addWidget(self.splitter, 1)
        self.stack.addWidget(self.page_text)
        self.set_mode("split")

    def _build_gallery_page(self):
        self.page_gallery = QWidget()
        gl = QVBoxLayout(self.page_gallery)
        gl.setContentsMargins(22, 6, 22, 14)
        gl.setSpacing(8)

        bar = QHBoxLayout()
        self.gallery_hint = QLabel("")
        self.gallery_hint.setStyleSheet(f"color:{C['faint']};font-size:11px;")
        bar.addWidget(self.gallery_hint)
        bar.addStretch(1)
        b = QPushButton("＋ 添加图片")
        b.setFixedHeight(30)
        b.clicked.connect(self._pick_images)
        bar.addWidget(b)
        gl.addLayout(bar)

        self.wall = QListWidget()
        self.wall.setViewMode(QListWidget.IconMode)
        self.wall.setIconSize(QSize(190, 190))
        self.wall.setGridSize(QSize(198, 202))
        self.wall.setResizeMode(QListWidget.Adjust)
        self.wall.setMovement(QListWidget.Static)
        self.wall.setSpacing(6)
        self.wall.setWordWrap(True)
        self.wall.setObjectName("Wall")
        self.wall.setVerticalScrollBar(AutoFadeScrollBar(Qt.Vertical, self.wall))
        self.wall.itemDoubleClicked.connect(self._open_viewer)
        self.wall.setContextMenuPolicy(Qt.CustomContextMenu)
        self.wall.customContextMenuRequested.connect(self._wall_menu)
        gl.addWidget(self.wall, 1)

        self.gallery_desc = MarkdownEdit("给这组图片写点说明……")
        self.gallery_desc.setFixedHeight(96)
        self.gallery_desc.setStyleSheet(
            f"background:{C['card']};border:1px solid {C['line']};border-radius:10px;padding:10px 14px;"
        )
        self.gallery_desc.textChanged.connect(self._on_desc_changed)
        gl.addWidget(self.gallery_desc)
        self.stack.addWidget(self.page_gallery)

    def _build_account_page(self):
        self.page_account = QWidget()
        al = QVBoxLayout(self.page_account)
        al.setContentsMargins(22, 8, 26, 16)
        al.setSpacing(10)

        card = QFrame(objectName="Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 16, 16)
        cl.setSpacing(12)

        for label_text, attr, secret in (("账号", "account_edit", False), ("密码", "password_edit", True)):
            row = QHBoxLayout()
            lb = QLabel(label_text)
            lb.setFixedWidth(36)
            row.addWidget(lb)
            le = QLineEdit()
            le.setPlaceholderText("（未填写）")
            if secret:
                le.setEchoMode(QLineEdit.Password)
            le.textChanged.connect(self._on_field_changed)
            setattr(self, attr, le)
            row.addWidget(le, 1)
            if secret:
                eye = QToolButton()
                eye.setText("显示")
                eye.setCheckable(True)
                eye.setToolTip("显示 / 隐藏密码")
                eye.toggled.connect(
                    lambda on, b=eye: (
                        le.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password),
                        b.setText("隐藏" if on else "显示"),
                    )
                )
                row.addWidget(eye)
            cp = QToolButton()
            cp.setText("复制")
            cp.clicked.connect(lambda _=False, w=le: self._copy(w.text()))
            row.addWidget(cp)
            cl.addLayout(row)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C['line_soft']};border:none;")
        cl.addWidget(sep)

        rrow = QHBoxLayout()
        rl = QLabel("备注")
        rl.setFixedWidth(36)
        rrow.addWidget(rl)
        self.remark_edit = QLineEdit()
        self.remark_edit.setPlaceholderText("比如：这个账号用来登录什么")
        self.remark_edit.textChanged.connect(self._on_field_changed)
        rrow.addWidget(self.remark_edit, 1)
        cl.addLayout(rrow)
        al.addWidget(card)

        self.account_tip = QLabel("密码未加密保存在本机的 library.json 里，导出时也会写进 accounts.csv。")
        self.account_tip.setWordWrap(True)
        self.account_tip.setStyleSheet(f"color:{C['faint']};font-size:11px;")
        al.addWidget(self.account_tip)
        al.addStretch(1)
        self.stack.addWidget(self.page_account)

    def _build_link_page(self):
        self.page_link = QWidget()
        ll = QVBoxLayout(self.page_link)
        ll.setContentsMargins(22, 8, 26, 16)
        ll.setSpacing(10)

        card = QFrame(objectName="Card")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(18, 12, 14, 12)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://")
        self.url_edit.textChanged.connect(self._on_field_changed)
        cl.addWidget(self.url_edit, 1)
        b = QPushButton("打开")
        b.setFixedWidth(64)
        b.clicked.connect(self._open_url)
        cl.addWidget(b)
        ll.addWidget(card)

        self.link_desc = MarkdownEdit("写下这条链接的说明……")
        self.link_desc.setStyleSheet(
            f"background:{C['card']};border:1px solid {C['line']};border-radius:12px;padding:12px 16px;"
        )
        self.link_desc.textChanged.connect(self._on_desc_changed)
        ll.addWidget(self.link_desc, 1)
        self.stack.addWidget(self.page_link)

    def _build_date_page(self):
        self.page_date = QWidget()
        dl = QVBoxLayout(self.page_date)
        dl.setContentsMargins(22, 8, 26, 16)
        dl.setSpacing(10)

        card = QFrame(objectName="Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(6)
        self.date_big = QLabel("")
        self.date_big.setStyleSheet(f"color:{C['green']};font-size:40px;font-weight:500;background:transparent;border:none;")
        cl.addWidget(self.date_big)
        self.date_sub = QLabel("")
        self.date_sub.setStyleSheet(f"color:{C['muted']};font-size:13px;background:transparent;border:none;")
        cl.addWidget(self.date_sub)
        cl.addSpacing(8)

        row = QHBoxLayout()
        self.date_type = QComboBox()
        self.date_type.addItems(["固定日期", "每年重复"])
        self.date_type.currentIndexChanged.connect(self._on_date_changed)
        row.addWidget(self.date_type)
        self.date_year = QSpinBox()
        self.date_year.setRange(1900, 2200)
        self.date_year.setButtonSymbols(QSpinBox.NoButtons)
        self.date_year.setAlignment(Qt.AlignCenter)
        self.date_year.setFixedWidth(76)
        self.date_year.valueChanged.connect(self._on_date_changed)
        row.addWidget(self.date_year)
        self.year_label = QLabel("年")
        row.addWidget(self.year_label)
        self.date_month = QSpinBox()
        self.date_month.setRange(1, 12)
        self.date_month.setButtonSymbols(QSpinBox.NoButtons)
        self.date_month.setAlignment(Qt.AlignCenter)
        self.date_month.setFixedWidth(52)
        self.date_month.valueChanged.connect(self._on_date_changed)
        row.addWidget(self.date_month)
        row.addWidget(QLabel("月"))
        self.date_day = QSpinBox()
        self.date_day.setRange(1, 31)
        self.date_day.setButtonSymbols(QSpinBox.NoButtons)
        self.date_day.setAlignment(Qt.AlignCenter)
        self.date_day.setFixedWidth(52)
        self.date_day.valueChanged.connect(self._on_date_changed)
        row.addWidget(self.date_day)
        row.addWidget(QLabel("日"))
        self.date_lunar = QCheckBox("农历")
        self.date_lunar.toggled.connect(self._on_date_changed)
        row.addWidget(self.date_lunar)
        row.addStretch(1)
        cl.addLayout(row)
        dl.addWidget(card)

        self.date_desc = MarkdownEdit("这个日子对你意味着什么……")
        self.date_desc.setStyleSheet(
            f"background:{C['card']};border:1px solid {C['line']};border-radius:12px;padding:12px 16px;"
        )
        self.date_desc.textChanged.connect(self._on_desc_changed)
        dl.addWidget(self.date_desc, 1)
        self.stack.addWidget(self.page_date)

    # ================= 数据 =================
    def set_library(self, lib: Library):
        self.lib = lib

    def _fade_in(self, widget):
        """切换类型页时轻轻淡入一下，别做成花哨的转场。"""
        try:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(170)
            anim.setStartValue(0.25)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start(QAbstractAnimation.DeleteWhenStopped)
        except RuntimeError:
            pass

    def set_note(self, note: Note | None, focus: bool = True):
        self.note = note
        self._loading = True
        if note is None:
            self.stack.setCurrentWidget(self.page_empty)
            self.title_wrap.setVisible(False)
            self.top_bar.setVisible(False)
            self._loading = False
            return

        self.top_bar.setVisible(True)

        self.badge.setText(TYPE_LABELS.get(note.type, "笔记"))
        self.title_edit.blockSignals(True)
        self.title_edit.setText(note.title or "")
        self.title_edit.blockSignals(False)
        self.title_wrap.setVisible(note.type in ("article", "account", "link", "date"))

        content = self.lib.content(note.id)
        page = {
            "note": self.page_text,
            "article": self.page_text,
            "gallery": self.page_gallery,
            "account": self.page_account,
            "link": self.page_link,
            "date": self.page_date,
        }.get(note.type, self.page_text)
        changed = self.stack.currentWidget() is not page
        self.stack.setCurrentWidget(page)
        if changed:
            self._fade_in(page)

        if note.type in ("note", "article"):
            self.edit.blockSignals(True)
            self.edit.setPlainText(content)
            self.edit.blockSignals(False)
            self._refresh_preview()
        elif note.type == "gallery":
            self.gallery_desc.blockSignals(True)
            self.gallery_desc.setPlainText(content)
            self.gallery_desc.blockSignals(False)
            self._reload_wall()
        elif note.type == "link":
            self.url_edit.blockSignals(True)
            self.url_edit.setText(note.url or "")
            self.url_edit.blockSignals(False)
            self.link_desc.blockSignals(True)
            self.link_desc.setPlainText(content)
            self.link_desc.blockSignals(False)
        elif note.type == "date":
            d = note.date or {}
            import datetime as _dt

            yearly = d.get("type") == 1
            year = d.get("year")
            if not year or int(year) < 1900:
                year = _dt.date.today().year
            self.date_type.setCurrentIndex(1 if yearly else 0)
            self.date_year.setValue(int(year))
            self.date_year.setVisible(not yearly)
            self.year_label.setVisible(not yearly)
            self.date_month.setValue(int(d.get("month") or 1))
            self.date_day.setValue(int(d.get("dayOfMonth") or 1))
            self.date_lunar.setChecked(bool(d.get("isLunar")))
            for w in (self.date_type, self.date_year, self.date_month, self.date_day, self.date_lunar):
                w.blockSignals(False)
            self.date_desc.blockSignals(True)
            self.date_desc.setPlainText(content)
            self.date_desc.blockSignals(False)
            self._update_date_card()
        elif note.type == "account":
            for w, v in ((self.account_edit, note.account), (self.password_edit, note.password), (self.remark_edit, note.remark)):
                w.blockSignals(True)
                w.setText(v or "")
                w.blockSignals(False)

        self.btn_pin.blockSignals(True)
        self.btn_pin.setChecked(bool(note.pinned_at))
        self.btn_pin.blockSignals(False)
        self.save_state.setText("")
        self._dirty = False
        self._update_meta_labels()
        self._loading = False
        if focus:
            w = self.title_edit if self.title_wrap.isVisible() else self._content_widget()
            w.setFocus()

    def _content_widget(self) -> QWidget:
        if not self.note:
            return self.edit
        return {
            "note": self.edit,
            "article": self.edit,
            "gallery": self.gallery_desc,
            "link": self.link_desc,
            "date": self.date_desc,
            "account": self.account_edit,
        }.get(self.note.type, self.edit)

    def _update_meta_labels(self):
        if not self.note:
            return
        n = self.note
        text = self.current_content()
        chars = len(text.strip())
        if n.type == "gallery":
            self.word_label.setText(f"{len(n.images)} 张图片 · 说明 {chars} 字")
        elif n.type == "account":
            self.word_label.setText("账号笔记")
        elif n.type == "date":
            self.word_label.setText(f"说明 {chars} 字" if chars else "")
        else:
            self.word_label.setText(f"{chars} 字")
        self.time_label.setText(f"创建 {human_time(n.created_at)}   更新 {human_time(n.updated_at)}")

    # ================= 编辑事件 =================
    def _emit(self):
        if self._loading or not self.note:
            return
        self._dirty = True
        self.save_state.setText("编辑中…")
        self.contentChanged.emit(self.note.id, self.current_content(), self.note.title or "")

    def _on_text_changed(self):
        self._emit()
        self._preview_timer.start()

    def _on_desc_changed(self):
        self._emit()
        self._update_meta_labels()

    def _on_title_changed(self, text: str):
        if self._loading or not self.note:
            return
        self.note.title = text
        self._emit()

    def _on_field_changed(self):
        if self._loading or not self.note:
            return
        n = self.note
        if n.type == "account":
            n.account = self.account_edit.text()
            n.password = self.password_edit.text()
            n.remark = self.remark_edit.text()
        elif n.type == "link":
            n.url = self.url_edit.text() or None
        self._emit()

    def _on_date_changed(self):
        if self._loading or not self.note:
            return
        yearly = self.date_type.currentIndex() == 1
        self.date_year.setVisible(not yearly)
        if hasattr(self, "year_label"):
            self.year_label.setVisible(not yearly)
        self.note.date = {
            "type": self.date_type.currentIndex(),
            "year": self.date_year.value(),
            "month": self.date_month.value(),
            "dayOfMonth": self.date_day.value(),
            "isLunar": self.date_lunar.isChecked(),
            "dayOfWeek": -1,
        }
        self._update_date_card()
        self._emit()

    def _update_date_card(self):
        y, m, d = self.date_year.value(), self.date_month.value(), self.date_day.value()
        self.date_big.setText(f"{m} 月 {d} 日")
        parts = []
        if self.date_type.currentIndex() == 0:
            parts.append(f"{y} 年")
        else:
            parts.append("每年重复")
        parts.append("农历" if self.date_lunar.isChecked() else "公历")
        self.date_sub.setText(" · ".join(parts))

    # ================= 正文 =================
    def current_content(self) -> str:
        if not self.note:
            return ""
        return {
            "note": self.edit.toPlainText,
            "article": self.edit.toPlainText,
            "gallery": self.gallery_desc.toPlainText,
            "link": self.link_desc.toPlainText,
            "date": self.date_desc.toPlainText,
            "account": lambda: "",
        }.get(self.note.type, self.edit.toPlainText)()

    def flush_note(self) -> Note | None:
        if not self.note:
            return None
        n = self.note
        if self.title_wrap.isVisible():
            n.title = self.title_edit.text().strip() or None
        if n.type == "link":
            n.url = self.url_edit.text() or None
        elif n.type == "account":
            n.account = self.account_edit.text()
            n.password = self.password_edit.text()
            n.remark = self.remark_edit.text()
        elif n.type == "date":
            n.date = {
                "type": self.date_type.currentIndex(),
                "year": self.date_year.value(),
                "month": self.date_month.value(),
                "dayOfMonth": self.date_day.value(),
                "isLunar": self.date_lunar.isChecked(),
                "dayOfWeek": -1,
            }
        return n

    # ================= 图片墙 =================
    def _reload_wall(self):
        self.wall.clear()
        if not self.note:
            return
        for rel in self.note.images:
            p = self.lib.attachment_abspath(rel)
            item = QListWidgetItem()
            if p.exists():
                pm = QPixmap(str(p))
                if not pm.isNull():
                    item.setIcon(_thumb(pm, 200))
            else:
                item.setText("图片缺失")
            item.setData(Qt.UserRole, str(p))
            item.setToolTip(Path(rel).name)
            self.wall.addItem(item)
        n = len(self.note.images)
        self.gallery_hint.setText(f"{n} 张图片 · 双击看大图，右键可移除" if n else "还没有图片，点右上角添加")

    def _open_viewer(self, item: QListWidgetItem):
        paths = [self.wall.item(i).data(Qt.UserRole) for i in range(self.wall.count())]
        paths = [p for p in paths if p and Path(p).exists()]
        if not paths:
            return
        idx = max(0, paths.index(item.data(Qt.UserRole)))
        ImageViewer(paths, idx, self).exec_()

    def _wall_menu(self, pos):
        item = self.wall.itemAt(pos)
        if not item or not self.note:
            return
        menu = QMenu(self)
        a_view = menu.addAction("查看大图")
        a_remove = menu.addAction("移除这张图片")
        act = menu.exec_(self.wall.mapToGlobal(pos))
        if act is a_view:
            self._open_viewer(item)
        elif act is a_remove:
            rel = self._rel_of(item)
            if rel and rel in self.note.images:
                self.note.images.remove(rel)
                self.lib.save()
            self._reload_wall()
            self.metaChanged.emit()

    def _rel_of(self, item: QListWidgetItem) -> str | None:
        p = item.data(Qt.UserRole)
        if not p:
            return None
        for rel in self.note.images if self.note else []:
            if str(self.lib.attachment_abspath(rel)) == p:
                return rel
        return None

    def _pick_images(self):
        if not self.note:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "图片 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)")
        for f in files:
            self._add_image(f)

    def _insert_image_file(self, path: str):
        if not self.note:
            return
        self._add_image(path)

    def _add_image(self, path: str):
        rel = self.lib.import_attachment(path)
        if self.note.type == "gallery":
            self.note.images.append(rel)
            self.lib.save()
            self._reload_wall()
            self.metaChanged.emit()
        else:
            cursor = self.edit.textCursor()
            cursor.insertText(f"\n![图片]({rel})\n")
            self.edit.setFocus()

    # ================= 编辑器操作 =================
    def _wrap(self, left: str, right: str):
        e = self.edit
        c = e.textCursor()
        if c.hasSelection():
            c.insertText(f"{left}{c.selectedText()}{right}")
        else:
            c.insertText(f"{left}{right}")
            c.movePosition(c.Left)
            e.setTextCursor(c)
        e.setFocus()

    def _prefix(self, prefix: str):
        e = self.edit
        c = e.textCursor()
        c.beginEditBlock()
        line_start = e.toPlainText().rfind("\n", 0, c.selectionStart()) + 1
        c.setPosition(line_start)
        c.insertText(prefix)
        c.endEditBlock()
        e.setFocus()

    def _insert_link(self):
        from PyQt5.QtWidgets import QInputDialog

        url, ok = QInputDialog.getText(self, "插入链接", "链接地址：")
        if ok and url.strip():
            c = self.edit.textCursor()
            c.insertText(f"[{c.selectedText() or url.strip()}]({url.strip()})")
            self.edit.setFocus()

    def _open_url(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        u = self.url_edit.text().strip()
        if not u:
            return
        if not u.lower().startswith(("http://", "https://")):
            u = "https://" + u
        QDesktopServices.openUrl(QUrl(u))

    def _copy(self, text: str):
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(text or "")
        self.save_state.setText("已复制")
        QTimer.singleShot(1200, lambda: self.save_state.setText(""))

    # ================= 笔记操作 =================
    def _toggle_pin(self):
        if not self.note:
            return
        self.lib.toggle_pin(self.note.id)
        self.note.pinned_at = self.lib.notes[self.note.id].pinned_at
        self.metaChanged.emit()

    def _set_color(self, color):
        if not self.note:
            return
        self.note.color = color
        self.lib.toggle_color(self.note.id, color)
        self.metaChanged.emit()

    def _toggle_archive(self):
        if not self.note:
            return
        self.lib.archive_note(self.note.id, self.note.state != "archived")
        self.note.state = self.lib.notes[self.note.id].state
        self.metaChanged.emit()

    def _delete(self):
        if not self.note:
            return
        self.lib.delete_note(self.note.id)
        self.note = None
        self.stack.setCurrentWidget(self.page_empty)
        self.title_wrap.setVisible(False)
        self.metaChanged.emit()

    def _duplicate(self):
        if not self.note:
            return
        n = self.lib.add_note(self.note.topic_id, self.note.type, self.current_content(), self.note.title)
        n.url, n.account, n.password, n.remark = self.note.url, self.note.account, self.note.password, self.note.remark
        n.date, n.images, n.description = self.note.date, list(self.note.images), self.note.description
        self.lib.save()
        self.metaChanged.emit()

    # ================= 预览 =================
    def _refresh_preview(self):
        if not self.note:
            return
        self.preview.setHtml(render(self.edit.toPlainText(), self.lib.root, "开始写点什么……"))
        self._update_meta_labels()

    def set_mode(self, mode: str):
        self._mode = mode
        if not hasattr(self, "edit"):
            return
        if mode == "edit":
            self.edit.show()
            self.preview.hide()
            self.mode_btn.setText("编辑")
        elif mode == "preview":
            self.edit.hide()
            self.preview.show()
            self.mode_btn.setText("预览")
            self._refresh_preview()
        else:
            self.edit.show()
            self.preview.show()
            self.mode_btn.setText("分屏")
            self.splitter.setSizes([10, 10])

    def mark_saved(self):
        self._dirty = False
        self.save_state.setText("已保存")


def _thumb(pm: QPixmap, size: int):
    from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath

    scaled = pm.scaled(size - 2, size - 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(QColor("#f3f3f5"))
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(1, 1, size - 2, size - 2, 9, 9)
    p.setClipPath(path)
    p.drawPixmap((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
    p.end()
    return QIcon(out)
