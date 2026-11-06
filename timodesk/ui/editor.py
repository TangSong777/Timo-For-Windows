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
import shutil
from pathlib import Path

from PyQt5.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QImage,
    QKeySequence,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PyQt5.QtWidgets import (
    QApplication,
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
    QScrollArea,
    QShortcut,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..render import TASK_RE, render
from ..store import TYPE_LABELS, Library, Note
from .dialogs import error as dlg_error
from .theme import C, NOTE_COLORS, color_icon
from .widgets import AutoFadeScrollBar
from .widgets import human_time


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


class ImageWall(QListWidget):
    """图片墙：可以拖入图片文件、Ctrl+V 粘贴、Delete 删除选中项。"""

    filesDropped = pyqtSignal(list)
    pasteRequested = pyqtSignal()
    deleteRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            return
        super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            return
        super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            files = []
            for url in e.mimeData().urls():
                p = url.toLocalFile()
                if p and Path(p).suffix.lower() in IMAGE_EXTS:
                    files.append(p)
            if files:
                self.filesDropped.emit(files)
            e.acceptProposedAction()
            return
        super().dropEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.selectedItems():
            self.deleteRequested.emit()
            return
        if e.matches(QKeySequence.Paste):
            self.pasteRequested.emit()
            return
        super().keyPressEvent(e)


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
        self.setStyleSheet(
            f"QDialog{{background:{C['ink']};}}"
            "QPushButton{background:rgba(255,255,255,0.12);color:#f2f2f2;border:0;"
            "border-radius:8px;padding:6px 18px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.22);}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._pm = QPixmap()
        self.zoom = 0.0  # 0 = 适应窗口，其它值是相对原始尺寸的倍数
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;}")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.label)
        lay.addWidget(self.scroll, 1)
        bar = QHBoxLayout()
        bar.setContentsMargins(12, 6, 12, 10)
        prev = QPushButton("‹ 上一张")
        prev.setCursor(Qt.PointingHandCursor)
        prev.clicked.connect(lambda: self._step(-1))
        bar.addWidget(prev)
        bar.addStretch(1)
        self.counter = QLabel()
        self.counter.setStyleSheet("color:#cfcfcf;")
        bar.addWidget(self.counter)
        bar.addStretch(1)
        nxt = QPushButton("下一张 ›")
        nxt.setCursor(Qt.PointingHandCursor)
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
        self._pm = QPixmap(self.paths[self.idx])
        if self._pm.isNull():
            self.label.setPixmap(QPixmap())
            self.label.setText("图片无法读取")
        else:
            self.label.setText("")
            self._apply_zoom()
        pct = "" if self.zoom <= 0 else f" · {int(self.zoom * 100)}%"
        self.counter.setText(f"{self.idx + 1} / {len(self.paths)}{pct} · 滚轮缩放")

    def _apply_zoom(self):
        if self._pm.isNull():
            return
        if self.zoom <= 0:
            box = self.scroll.viewport().size()
            box.setWidth(max(80, box.width() - 8))
            box.setHeight(max(80, box.height() - 8))
            if self._pm.width() > box.width() or self._pm.height() > box.height():
                pm = self._pm.scaled(box, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                pm = self._pm
        else:
            w = max(20, int(self._pm.width() * self.zoom))
            h = max(20, int(self._pm.height() * self.zoom))
            pm = self._pm.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(pm)
        self.label.resize(pm.size())

    def wheelEvent(self, e):  # noqa: N802
        if self._pm.isNull():
            return
        cur = self.zoom if self.zoom > 0 else 1.0
        step = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.zoom = max(0.1, min(8.0, cur * step))
        self._apply_zoom()
        pct = "" if self.zoom <= 0 else f" · {int(self.zoom * 100)}%"
        self.counter.setText(f"{self.idx + 1} / {len(self.paths)}{pct} · 滚轮缩放")

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        self.zoom = 0.0 if self.zoom > 0 else 1.0
        self._apply_zoom()
        pct = "" if self.zoom <= 0 else f" · {int(self.zoom * 100)}%"
        self.counter.setText(f"{self.idx + 1} / {len(self.paths)}{pct} · 滚轮缩放")

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        if self.zoom <= 0:
            self._apply_zoom()

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
        self.btn_remind = QToolButton()
        self.btn_remind.setText("提醒")
        self.btn_remind.setToolTip("设置提醒")
        self.btn_remind.clicked.connect(self._on_remind)
        tl.addWidget(self.btn_remind)
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

        # 编辑器内查找条（Ctrl+F 在正文里时出现）
        self.find_bar = QFrame(objectName="FindBar")
        self.find_bar.setVisible(False)
        fl = QHBoxLayout(self.find_bar)
        fl.setContentsMargins(10, 4, 10, 4)
        fl.setSpacing(6)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("在笔记中查找…")
        self.find_edit.setFixedWidth(220)
        self.find_edit.textChanged.connect(lambda _t: self._find_step(forward=True, restart=True))
        self.find_edit.returnPressed.connect(lambda: self._find_step(forward=True))
        fl.addWidget(self.find_edit)
        self.find_count = QLabel("")
        self.find_count.setObjectName("FindCount")
        fl.addWidget(self.find_count)
        for text, tip, fwd in (("↑", "上一个 Shift+Enter", False), ("↓", "下一个 Enter", True)):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(lambda _c=False, f=fwd: self._find_step(forward=f))
            fl.addWidget(b)
        fl.addStretch(1)
        b_close = QToolButton()
        b_close.setText("✕")
        b_close.setToolTip("关闭 Esc")
        b_close.clicked.connect(self.hide_find)
        fl.addWidget(b_close)
        pl.addWidget(self.find_bar)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.edit = MarkdownEdit("开始写点什么……\n\n支持简单 Markdown：**粗体**、*斜体*、# 标题、- 列表、> 引用、`代码`")
        self.edit.textChanged.connect(self._on_text_changed)
        self.edit.imageDropped.connect(self._insert_image_file)
        self.preview = QTextBrowser(objectName="Preview")
        self.preview.setOpenExternalLinks(True)
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self._on_anchor)
        self.preview.setFrameShape(QFrame.NoFrame)
        self.splitter.addWidget(self.edit)
        self.splitter.addWidget(self.preview)
        pl.addWidget(self.splitter, 1)
        self.stack.addWidget(self.page_text)
        self.set_mode("split")
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        def add(seq, fn, ctx=Qt.WidgetShortcut):
            sc = QShortcut(QKeySequence(seq), self.edit)
            sc.setContext(ctx)
            sc.activated.connect(fn)
            return sc

        add(QKeySequence.Find, self.show_find)
        add("Ctrl+B", lambda: self._wrap("**", "**"))
        add("Ctrl+I", lambda: self._wrap("*", "*"))
        add("Ctrl+K", self._insert_link)
        add("Ctrl+Shift+T", lambda: self._prefix("- [ ] "))
        add("Ctrl+Shift+1", lambda: self._prefix("# "))
        add("Ctrl+Shift+2", lambda: self._prefix("## "))
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self.find_edit)
        esc.setContext(Qt.WidgetShortcut)
        esc.activated.connect(self.hide_find)
        up = QShortcut(QKeySequence("Shift+Return"), self.find_edit)
        up.setContext(Qt.WidgetShortcut)
        up.activated.connect(lambda: self._find_step(forward=False))

    def show_find(self):
        self.find_bar.setVisible(True)
        text = self.edit.textCursor().selectedText()
        if text and "\n" not in text:
            self.find_edit.setText(text)
        self.find_edit.setFocus()
        self.find_edit.selectAll()
        self._find_step(forward=True, restart=True)

    def hide_find(self):
        self.find_bar.setVisible(False)
        self.edit.setFocus()

    def _find_step(self, forward: bool = True, restart: bool = False):
        needle = self.find_edit.text()
        if not needle:
            self.find_count.setText("")
            return
        total = self.edit.toPlainText().count(needle)
        self.find_count.setText(f"{total} 处" if total else "无匹配")
        if not total:
            return
        flags = QTextDocument.FindFlags()
        if not forward:
            flags |= QTextDocument.FindBackward
        if restart:
            cur = self.edit.textCursor()
            cur.movePosition(QTextCursor.Start if forward else QTextCursor.End)
            self.edit.setTextCursor(cur)
        if not self.edit.find(needle, flags):
            cur = self.edit.textCursor()
            cur.movePosition(QTextCursor.Start if forward else QTextCursor.End)
            self.edit.setTextCursor(cur)
            self.edit.find(needle, flags)

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

        self.wall = ImageWall()
        self.wall.filesDropped.connect(self._add_images_from_files)
        self.wall.pasteRequested.connect(self._paste_wall_image)
        self.wall.deleteRequested.connect(self._remove_selected_images)
        self.wall.setDragDropMode(QListWidget.InternalMove)
        self.wall.setDefaultDropAction(Qt.MoveAction)
        self.wall.model().rowsMoved.connect(self._on_wall_reordered)
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
            self.word_label.setText("")
            self.time_label.setText("")
            self._loading = False
            return

        self.top_bar.setVisible(True)
        self._sync_remind()

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
            n.description = self.link_desc.toPlainText().strip() or None
        elif n.type == "gallery":
            n.description = self.gallery_desc.toPlainText().strip() or None
        elif n.type == "date":
            n.description = self.date_desc.toPlainText().strip() or None
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

    def _on_wall_reordered(self, *args):
        """拖动图片后把新顺序写回笔记（只在图库类型下有效）。"""
        if not self.note or self.note.type != "gallery":
            return
        order = []
        for i in range(self.wall.count()):
            rel = self._rel_for_path(self.wall.item(i).data(Qt.UserRole))
            if rel:
                order.append(rel)
        if len(order) == len(self.note.images) and order != self.note.images:
            self.note.images = order
            self.lib.save()
            self.metaChanged.emit()

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
        self.gallery_hint.setText(
            f"{n} 张图片 · 双击看大图，拖入或粘贴可添加" if n else "还没有图片，点右上角添加，也可以把图片拖进来"
        )

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
        a_save = menu.addAction("图片另存为…")
        a_copy = menu.addAction("复制图片")
        menu.addSeparator()
        a_remove = menu.addAction("移除这张图片")
        act = menu.exec_(self.wall.mapToGlobal(pos))
        if act is a_view:
            self._open_viewer(item)
        elif act is a_save:
            self._save_image(item)
        elif act is a_copy:
            self._copy_image(item)
        elif act is a_remove:
            rel = self._rel_of(item)
            if rel and rel in self.note.images:
                self.note.images.remove(rel)
                self.lib.save()
            self._reload_wall()
            self.metaChanged.emit()

    def _save_image(self, item: QListWidgetItem):
        src = item.data(Qt.UserRole)
        if not src:
            return
        src = Path(src)
        out, _ = QFileDialog.getSaveFileName(self, "图片另存为", src.name, "图片 (*.png *.jpg *.jpeg *.webp *.gif *.bmp)")
        if not out:
            return
        try:
            shutil.copy2(src, out)
        except OSError as e:
            dlg_error(self, "保存失败", f"写入图片时出错：\n{e}")

    def _copy_image(self, item: QListWidgetItem):
        src = item.data(Qt.UserRole)
        if not src:
            return
        img = QImage(src)
        if img.isNull():
            return
        QApplication.clipboard().setImage(img)

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
        if not files:
            return
        for f in files:
            self._add_image(f, reload=False)
        self._reload_wall()
        self.metaChanged.emit()

    def _add_images_from_files(self, files: list):
        """拖进图片墙的文件。"""
        if not self.note or self.note.type != "gallery" or not files:
            return
        for f in files:
            self._add_image(f, reload=False)
        self._reload_wall()
        self.metaChanged.emit()

    def _paste_wall_image(self):
        """Ctrl+V：把剪贴板里的图片存进图库。"""
        if not self.note or self.note.type != "gallery":
            return
        img = QApplication.clipboard().image()
        if img.isNull():
            self._flash("剪贴板里没有图片")
            return
        tmp = self.lib.root / "attachments" / f"_paste_{os.getpid()}.png"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        if not img.save(str(tmp), "PNG"):
            self._flash("图片保存失败")
            return
        try:
            self._add_image(str(tmp), reload=False)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
        self._reload_wall()
        self.metaChanged.emit()
        self._flash("已粘贴图片")

    def _remove_selected_images(self):
        """Delete：从图库里删掉选中的图片（文件留在附件目录）。"""
        if not self.note or self.note.type != "gallery":
            return
        rels = [self._rel_of(it) for it in self.wall.selectedItems()]
        rels = [r for r in rels if r]
        if not rels:
            return
        for r in rels:
            if r in self.note.images:
                self.note.images.remove(r)
        self.lib.save()
        self._reload_wall()
        self.metaChanged.emit()

    def _flash(self, text: str, ms: int = 1200):
        self.save_state.setText(text)
        QTimer.singleShot(ms, lambda: self.save_state.setText(""))

    def _insert_image_file(self, path: str):
        if not self.note:
            return
        self._add_image(path)

    def _add_image(self, path: str, reload: bool = True):
        rel = self.lib.import_attachment(path)
        if self.note.type == "gallery":
            self.note.images.append(rel)
            self.lib.save()
            if reload:
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

    def _sync_remind(self):
        n = self.note
        if n and n.remind_at:
            self.btn_remind.setText("⏰")
            self.btn_remind.setToolTip("提醒：" + human_time(n.remind_at) + "（点击修改）")
        else:
            self.btn_remind.setText("提醒")
            self.btn_remind.setToolTip("设置提醒")

    def _on_remind(self):
        if not self.note:
            return
        from .dialogs import ReminderDialog
        from ..store import from_iso, to_iso

        cur = from_iso(self.note.remind_at)
        d = ReminderDialog(self, cur, has_reminder=bool(self.note.remind_at))
        if not d.exec_():
            return
        if d.cleared:
            self.lib.set_reminder(self.note.id, None)
        elif d.result_when:
            self.lib.set_reminder(self.note.id, to_iso(d.result_when))
        self._sync_remind()
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
    def _on_anchor(self, url: QUrl):
        """预览里的链接：待办方框就地勾选，其余链接交给系统浏览器。"""
        if url.scheme() == "todo":
            try:
                self._toggle_todo(int(url.path()))
            except (TypeError, ValueError):
                pass
            return
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)

    def _toggle_todo(self, lineno: int):
        """把正文第 lineno 行的 [ ] / [x] 翻过来（保留撤销栈）。"""
        text = self.edit.toPlainText()
        lines = text.split("\n")
        if not (0 <= lineno < len(lines)):
            return
        m = TASK_RE.match(lines[lineno])
        if not m:
            return
        checked = m.group(2).lower() == "x"
        offset = sum(len(x) + 1 for x in lines[:lineno]) + m.start(2)
        cur = QTextCursor(self.edit.document())
        cur.setPosition(offset)
        cur.setPosition(offset + 1, QTextCursor.KeepAnchor)
        cur.insertText(" " if checked else "x")
        self._emit()
        self._refresh_preview()

    def _refresh_preview(self):
        if not self.note:
            return
        self.preview.setHtml(render(self.edit.toPlainText(), self.lib.root, "开始写点什么……"))
        self._paint_highlight()
        self._update_meta_labels()

    def _paint_highlight(self):
        """搜索词在预览里刷一层浅灰底（QTextBrowser 不认 span 背景，用 ExtraSelection）。"""
        term = getattr(self, "_highlight", "")
        if not term:
            self.preview.setExtraSelections([])
            return
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#c9c9c9"))
        doc = self.preview.document()
        sels = []
        for word in [w for w in term.split() if w]:
            cur = QTextCursor(doc)
            while True:
                cur = doc.find(word, cur)
                if cur.isNull():
                    break
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cur
                sel.format = fmt
                sels.append(sel)
        self.preview.setExtraSelections(sels)

    def set_highlight(self, term: str):
        """搜索时把命中词在预览里标出来。"""
        term = (term or "").strip()
        if term == getattr(self, "_highlight", ""):
            return
        self._highlight = term
        if self.note and self.note.type in ("note", "article"):
            self._refresh_preview()
        else:
            self._paint_highlight()

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
