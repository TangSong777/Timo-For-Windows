"""主窗口：三栏布局 —— 主题侧栏 / 笔记列表 / 编辑器。"""
from __future__ import annotations

from ctypes import wintypes
from pathlib import Path

from PyQt5.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QColor, QCursor, QKeySequence, QPainter, QPen
from PyQt5.QtWidgets import (
    QActionGroup,
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QShortcut,
    QSystemTrayIcon,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

import re
import shutil

from ..exporter import export_zip, note_markdown
from ..settings import Settings
from ..importer import import_export
from ..store import NOTE_TYPES, TYPE_LABELS, Library, Note
from .dialogs import ProgressDialog, confirm, error, info
from .editor import NoteEditor
from .theme import C, NOTE_COLORS, app_qss, color_icon, resolve as resolve_theme, set_mode as set_theme_mode


class _Body(QWidget):
    """浅灰画布：在三块面板下方手绘一层柔和投影。

    不用 QGraphicsDropShadowEffect —— 它会把子控件离屏渲染，
    长列表滚动时既费性能，也会让裁剪区域错位。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.panes: list[QWidget] = []

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.panes:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(Qt.NoBrush)
        for pane in self.panes:
            if pane.isHidden():
                continue
            tl = pane.mapTo(self, QPoint(0, 0))
            r = QRectF(
                tl.x() + 0.5, tl.y() + 0.5, float(pane.width()) - 1.0, float(pane.height()) - 1.0
            )
            for i in range(1, 24):
                alpha = int(90 * (1.0 - (i - 1) / 23.0) ** 2.4)
                if alpha <= 0:
                    continue
                p.setPen(QPen(QColor(0, 0, 0, alpha), 1))
                p.drawRoundedRect(r.adjusted(-i, -i + 5, i, i + 7), 15.5 + i, 15.5 + i)
from .title_bar import (
    FrameEdge,
    HTBOTTOM,
    HTBOTTOMLEFT,
    HTBOTTOMRIGHT,
    HTLEFT,
    HTRIGHT,
    HTTOP,
    HTTOPLEFT,
    HTTOPRIGHT,
    RESIZE_BORDER,
    WM_NCHITTEST,
    TitleBar,
    rounded_mask,
)
from .widgets import AutoFadeScrollBar, NoteCardDelegate, NoteList, TopicDelegate, TopicList


class ImportCanceled(Exception):
    """用户在导入进度条上点了取消。"""


def _search_icon():
    """放大镜：1.6px 线条，跟着 muted 色走。"""
    from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(QPen(QColor(C["muted"]), 1.6))
    p.drawEllipse(2, 2, 9, 9)
    p.drawLine(10, 10, 14, 14)
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self, lib: Library, parent=None):
        super().__init__(parent)
        self.lib = lib
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.view = ("all", None)  # (kind, topic_id)
        self._pending_save = None
        self._search_buf = ""
        self.setWindowTitle("Timo For Windows")
        self.resize(1280, 830)
        self.setMinimumSize(980, 620)
        self.tray = None
        self.setAcceptDrops(True)
        self.settings = Settings(self.lib.root)
        self.sort_mode = self.settings.get("sort_mode", "updated")
        self._quitting = False
        self._tray_hinted = False
        self._build_ui()
        self._sync_sort_menu()
        self._restore_geometry()
        self._build_shortcuts()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._flush_save)
        self._remind_timer = QTimer(self)
        self._remind_timer.setInterval(30_000)
        self._remind_timer.timeout.connect(self._check_reminders)
        self._remind_timer.start()
        QTimer.singleShot(1500, self._check_reminders)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(220)
        self._search_timer.timeout.connect(self._apply_search)
        self.refresh_topics()
        self._restore_view()

    # ---------------- 布局 ----------------
    def _build_ui(self):
        central = QWidget(objectName="Root")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        body = _Body(objectName="Body")
        outer.addWidget(body, 1)
        h = QHBoxLayout(body)
        h.setContentsMargins(20, 14, 20, 18)
        h.setSpacing(12)

        # ===== 侧栏 =====
        sidebar = QFrame(objectName="Sidebar")
        sidebar.setFixedWidth(224)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(14, 16, 12, 14)
        sb.setSpacing(6)

        self.nav = QListWidget(objectName="NavList")
        self.nav.setFrameShape(QListWidget.NoFrame)
        self.nav.setFixedHeight(3 * 34 + 6)
        for key, label, icon in (("all", "全部笔记", "▤"), ("archived", "归档", "▣"), ("trash", "回收站", "♲")):
            it = QListWidgetItem(f"{icon}  {label}")
            it.setData(Qt.UserRole, key)
            it.setSizeHint(QSize(0, 38))
            self.nav.addItem(it)
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        sb.addWidget(self.nav)

        sb.addSpacing(6)
        sec = QHBoxLayout()
        sec_label = QLabel("主题", objectName="SideSection")
        sec.addWidget(sec_label)
        sec.addStretch(1)
        btn_add_topic = QToolButton()
        btn_add_topic.setText("＋")
        btn_add_topic.setToolTip("新建主题")
        btn_add_topic.clicked.connect(self.new_topic)
        sec.addWidget(btn_add_topic)
        sb.addLayout(sec)

        self.topic_list = TopicList(objectName="TopicList")
        self.topic_list.setVerticalScrollBar(AutoFadeScrollBar(Qt.Vertical, self.topic_list))
        self.topic_list.setItemDelegate(TopicDelegate(self.lib, self))
        self.topic_list.setFrameShape(QListWidget.NoFrame)
        self.topic_list.setDefaultDropAction(Qt.MoveAction)
        self.topic_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.topic_list.customContextMenuRequested.connect(self._topic_menu)
        self.topic_list.currentRowChanged.connect(self._on_topic_changed)
        self.topic_list.notesDropped.connect(self._on_notes_dropped)
        self.topic_list.topicsReordered.connect(self._on_topics_reordered)
        sb.addWidget(self.topic_list, 1)

        sb.addSpacing(4)
        btn_topic = QPushButton("＋ 新建主题", objectName="NewTopicBtn")
        btn_topic.clicked.connect(self.new_topic)
        sb.addWidget(btn_topic)

        bottom = QHBoxLayout()
        btn_data = QToolButton()
        btn_data.setText("…")
        btn_data.setToolTip("数据与设置")
        menu = QMenu(self)
        menu.addAction("导入 Timo 导出包（ZIP）…", self.import_zip)
        menu.addAction("导入文件夹…", self.import_folder)
        menu.addSeparator()
        menu.addAction("导出为 Timo ZIP…", self.export_zip)
        menu.addAction("导出为 Markdown 文件夹…", self.export_md_tree)
        menu.addAction("打开数据目录", self.open_data_dir)
        menu.addAction("备份与恢复…", self.backup_dialog)
        menu.addAction("已删除的主题…", self.trash_topics_dialog)
        menu.addSeparator()
        menu.addAction("清空回收站…", self.empty_trash)
        menu.addAction("清理未使用的图片…", self.clean_attachments)
        menu.addSeparator()
        appearance = menu.addMenu("外观")
        grp = QActionGroup(self)
        grp.setExclusive(True)
        current = self.settings.get("theme_mode", "light")
        for key, label in (("light", "浅色"), ("dark", "深色"), ("system", "跟随系统")):
            act = appearance.addAction(label)
            act.setCheckable(True)
            act.setChecked(current == key)
            act.triggered.connect(lambda _=False, k=key: self.set_theme(k))
            grp.addAction(act)
        self._theme_group = grp
        menu.addSeparator()
        menu.addAction("关于 Timo 桌面版", self.show_about)
        btn_data.setMenu(menu)
        btn_data.setPopupMode(QToolButton.InstantPopup)
        bottom.addWidget(btn_data)
        bottom.addStretch(1)
        self.total_label = QLabel("")
        self.total_label.setObjectName("TotalLabel")
        bottom.addWidget(self.total_label)
        sb.addLayout(bottom)
        h.addWidget(sidebar)

        # ===== 列表 =====
        listpane = QFrame(objectName="ListPane")
        listpane.setFixedWidth(334)
        lp = QVBoxLayout(listpane)
        lp.setContentsMargins(18, 18, 14, 14)
        lp.setSpacing(9)

        head = QHBoxLayout()
        self.header_label = QLabel("全部笔记", objectName="ListHeader")
        head.addWidget(self.header_label)
        head.addSpacing(8)
        self.count_label = QLabel("", objectName="CountLabel")
        head.addWidget(self.count_label, alignment=Qt.AlignBottom)
        head.addStretch(1)
        self.btn_sort = QToolButton(objectName="SortBtn")
        self.btn_sort.setText("⇅")
        self.btn_sort.setPopupMode(QToolButton.InstantPopup)
        self.btn_sort.setFixedSize(26, 26)
        self.btn_sort.setCursor(Qt.PointingHandCursor)
        self.sort_menu = QMenu(self)
        for key, label in (("updated", "最近更新"), ("created", "最近创建"), ("title", "标题")):
            act = self.sort_menu.addAction(label)
            act.setCheckable(True)
            act.setData(key)
            act.triggered.connect(lambda _=False, k=key: self.set_sort(k))
        self.btn_sort.setMenu(self.sort_menu)
        head.addWidget(self.btn_sort, alignment=Qt.AlignVCenter)
        newslot = QHBoxLayout()
        newslot.setContentsMargins(0, 0, 0, 0)
        newslot.setSpacing(0)
        self.btn_new_note = QPushButton("＋ 新建", objectName="NewNoteBtn")
        self.btn_new_note.setFixedHeight(32)
        self.btn_new_note.setToolTip("新建便签（Ctrl+N）")
        self.btn_new_note.clicked.connect(lambda: self.new_note("note"))
        newslot.addWidget(self.btn_new_note)
        self.btn_new_type = QToolButton(objectName="NewTypeBtn")
        self.btn_new_type.setText("▾")
        self.btn_new_type.setToolTip("新建其他类型")
        self.btn_new_type.setFixedHeight(32)
        self.btn_new_type.setFixedWidth(26)
        self.btn_new_type.setPopupMode(QToolButton.InstantPopup)
        type_menu = QMenu(self)
        for t in NOTE_TYPES:
            type_menu.addAction(TYPE_LABELS[t], lambda _=False, tt=t: self.new_note(tt))
        self.btn_new_type.setMenu(type_menu)
        newslot.addWidget(self.btn_new_type)
        head.addLayout(newslot)
        lp.addLayout(head)

        self.search = QLineEdit(objectName="Search")
        esc_search = QShortcut(QKeySequence("Escape"), self.search)
        esc_search.setContext(Qt.WidgetShortcut)
        esc_search.activated.connect(lambda: self._clear_search(focus=True))
        self.search.setPlaceholderText("搜索笔记…  Ctrl+F")
        self.search.addAction(_search_icon(), QLineEdit.LeadingPosition)
        self.search.setTextMargins(4, 0, 0, 0)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_search_changed)
        lp.addWidget(self.search)

        self.note_list = NoteList(objectName="NoteList")
        self.note_list.setVerticalScrollBar(AutoFadeScrollBar(Qt.Vertical, self.note_list))
        self.note_list.setItemDelegate(NoteCardDelegate(self.lib, self))
        self.note_list.setFrameShape(QListWidget.NoFrame)
        self.note_list.setMouseTracking(True)
        self.note_list.deleteRequested.connect(self._on_notes_delete_key)
        self.note_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.note_list.setUniformItemSizes(True)
        self.note_list.setLayoutMode(QListView.Batched)
        self.note_list.setBatchSize(80)
        self.note_list.setSpacing(0)
        self.note_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.note_list.setDragEnabled(True)
        self.note_list.setDragDropMode(QListWidget.DragOnly)
        self.note_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._note_menu)
        self.note_list.currentRowChanged.connect(self._on_note_changed)
        self.note_list.setUniformItemSizes(True)
        self.list_empty = QLabel("", objectName="ListEmpty")
        self.list_empty.setAlignment(Qt.AlignCenter)
        self.list_empty.setWordWrap(True)
        self.list_empty.hide()
        lp.addWidget(self.list_empty, 1)
        lp.addWidget(self.note_list, 1)
        h.addWidget(listpane)

        # ===== 编辑器 =====
        self.editor = NoteEditor(self.lib)
        self.editor.contentChanged.connect(self._on_content_changed)
        self.editor.metaChanged.connect(self._on_meta_changed)
        self.editor.requestNewNote.connect(self.new_note)
        h.addWidget(self.editor, 1)

        # 三块面板浮在浅灰画布上，投影由 _Body.paintEvent 手绘
        body.panes = [sidebar, listpane, self.editor]

        self.statusBar().hide()

        # 无边框窗口的轮廓
        self._edge = FrameEdge(central)
        self._edge.setGeometry(central.rect())
        self._edge.raise_()

    def _build_shortcuts(self):
        for seq, fn in [
            ("Ctrl+N", self.new_note),
            ("Ctrl+Shift+N", self.new_topic),
            ("Ctrl+F", lambda: self.search.setFocus()),
            ("Ctrl+S", self.save_now),
            ("Ctrl+E", self._toggle_preview),
            ("Ctrl+Shift+E", lambda: self.editor.set_mode("edit")),
        ]:
            QShortcut(QKeySequence(seq), self, fn)

    # ---------------- 视图记忆 ----------------
    def _restore_view(self):
        """打开时回到上次的视图和笔记；记录失效就退回「全部笔记」。"""
        raw = self.settings.get("last_view") or {}
        kind = raw.get("kind") if isinstance(raw, dict) else None
        topic_id = raw.get("topic") if isinstance(raw, dict) else None
        last_note = self.settings.get("last_note") or None

        if kind == "topic" and topic_id:
            topic = self.lib.topics.get(topic_id)
            if topic is not None and topic.state != "trash":
                self.view = ("topic", topic_id)
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(-1)
                self.nav.blockSignals(False)
                self.refresh_topics()
                self._reload_notes(select_id=last_note)
                return

        kind = kind if kind in ("all", "archived", "trash") else "all"
        self.view = (kind, None)
        row = {"all": 0, "archived": 1, "trash": 2}[kind]
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(row)
        self.nav.blockSignals(False)
        self._reload_notes(select_id=last_note)

    def _save_view(self):
        kind, topic_id = self.view
        try:
            self.settings.set("last_view", {"kind": kind, "topic": topic_id or ""})
            note = getattr(self.editor, "note", None)
            self.settings.set("last_note", note.id if note else "")
        except Exception:
            pass

    # ---------------- 侧栏 ----------------
    def refresh_topics(self):
        current = self.view[1] if self.view[0] == "topic" else None
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        topics = [t for t in self.lib.topics.values() if t.state != "trash"]
        topics.sort(key=lambda t: (t.order, t.created_at))
        active_counts = self.lib.note_counts("active")
        archived_counts = self.lib.note_counts("archived")
        counts = {t.id: (archived_counts if t.state == "archived" else active_counts).get(t.id, 0) for t in topics}
        dlg = self.topic_list.itemDelegate()
        if dlg is not None:
            dlg.counts = counts
        for t in topics:
            it = QListWidgetItem(t.name)
            it.setData(Qt.UserRole, t)
            it.setToolTip(f"{t.name} · {counts.get(t.id, 0)} 条")
            self.topic_list.addItem(it)
        if current:
            for i in range(self.topic_list.count()):
                if getattr(self.topic_list.item(i).data(Qt.UserRole), "id", None) == current:
                    self.topic_list.setCurrentRow(i)
                    break
        self.topic_list.blockSignals(False)
        active = sum(1 for n in self.lib.notes.values() if n.state == "active")
        total = len(self.lib.notes)
        self.total_label.setText(f"{active} / {total} 条")

    def select_nav(self, kind: str):
        row = {"all": 0, "archived": 1, "trash": 2}.get(kind, 0)
        self.nav.setCurrentRow(row)

    def _clear_search(self, focus: bool = False):
        """清掉搜索词（切换视图或按 Esc），免得列表停在上一轮的搜索结果里。"""
        self._search_buf = ""
        if self.search.text():
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        if focus:
            self.note_list.setFocus()

    def _on_nav_changed(self, row: int):
        kind = {0: "all", 1: "archived", 2: "trash"}.get(row, "all")
        self._clear_search()
        self.topic_list.blockSignals(True)
        self.topic_list.clearSelection()
        self.topic_list.setCurrentRow(-1)
        self.topic_list.blockSignals(False)
        self.view = (kind, None)
        self._reload_notes(animate=True)

    def _on_topic_changed(self, row: int):
        if row < 0:
            return
        it = self.topic_list.item(row)
        if not it:
            return
        topic = it.data(Qt.UserRole)
        self._clear_search()
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(-1)
        self.nav.blockSignals(False)
        self.view = ("topic", topic.id)
        self._reload_notes(animate=True)

    def _topic_menu(self, pos):
        it = self.topic_list.itemAt(pos)
        if not it:
            return
        topic = it.data(Qt.UserRole)
        menu = QMenu(self)
        a_new = menu.addAction("在此主题新建笔记")
        menu.addSeparator()
        a_rename = menu.addAction("重命名主题…")
        a_delete = menu.addAction("删除主题")
        act = menu.exec_(self.topic_list.mapToGlobal(pos))
        if act is a_new:
            self.new_note()
        elif act is a_rename:
            from .dialogs import InputDialog

            dlg = InputDialog(self, "重命名主题", "主题名称", text=topic.name)
            name = dlg.value if dlg.exec_() else None
            if name:
                if self._topic_name_taken(name, exclude_id=topic.id):
                    info(self, "已有同名主题", f"已经有一个叫「{name}」的主题了，换个名字吧。")
                    return
                self.lib.rename_topic(topic.id, name)
                self.lib.save()
                self.refresh_topics()
                if self.view == ("topic", topic.id):
                    self._reload_notes()
        elif act is a_delete:
            cnt = self.lib.note_counts().get(topic.id, 0)
            if cnt:
                if not confirm(
                    self,
                    "删除主题",
                    f"「{topic.name}」里还有 {cnt} 条笔记，删除主题会把它们一起移到回收站。继续？",
                ):
                    return
            self.lib.delete_topic(topic.id)
            self.lib.save()
            self.refresh_topics()
            self.select_nav("all")

    def _topic_name_taken(self, name: str, exclude_id: str | None = None) -> bool:
        """是否已有同名主题（回收站里的不算，重命名自己也不算）。"""
        key = name.strip()
        return any(
            t.name.strip() == key and t.state != "trash" and t.id != exclude_id
            for t in self.lib.topics.values()
        )

    def new_topic(self):
        from .dialogs import InputDialog

        dlg = InputDialog(self, "新建主题", "主题名称", placeholder="比如：日记、工作、读书")
        name = dlg.value if dlg.exec_() else None
        if not name:
            return
        if self._topic_name_taken(name):
            info(self, "已有同名主题", f"已经有一个叫「{name}」的主题了，换个名字吧。")
            return
        t = self.lib.add_topic(name)
        self.lib.save()
        self.refresh_topics()
        for i in range(self.topic_list.count()):
            if self.topic_list.item(i).data(Qt.UserRole).id == t.id:
                self.topic_list.setCurrentRow(i)
                break

    # ---------------- 列表 ----------------
    def _current_notes(self) -> list[Note]:
        kind, tid = self.view
        order = getattr(self, "sort_mode", "updated")
        if kind == "all":
            return self.lib.sorted_notes(state="active", order=order)
        if kind == "archived":
            return self.lib.sorted_notes(state="archived", order=order)
        if kind == "trash":
            return self.lib.sorted_notes(state="trash", order=order)
        t = self.lib.topics.get(tid)
        state = "archived" if (t and t.state == "archived") else "active"
        return self.lib.topic_notes(tid, state=state, order=order)

    def _fade_in(self, widget: QWidget, ms: int = 180):
        """短暂的透明度过渡，用于切换视图、页面时的柔和出现。"""
        try:
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(ms)
            anim.setStartValue(0.2)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start(QAbstractAnimation.DeleteWhenStopped)
        except RuntimeError:
            pass

    def _reload_notes(self, select_id: str | None = None, animate: bool = False):
        kind, tid = self.view
        title = "全部笔记"
        if kind == "archived":
            title = "归档"
        elif kind == "trash":
            title = "回收站"
        elif kind == "topic":
            t = self.lib.topics.get(tid)
            title = t.name if t else "主题"
        self.header_label.setText(title)

        delegate = self.note_list.itemDelegate()
        if delegate is not None:
            delegate.show_topic = kind in ("all", "archived") or bool(self._search_buf)
            delegate.term = self._search_buf or ""

        notes = self._current_notes()
        if self._search_buf:
            # 搜索和手机版一样是「全库搜索」：当前在回收站里才只搜回收站
            if kind == "trash":
                pool = notes
            else:
                pool = self.lib.sorted_notes(state="active") + self.lib.sorted_notes(state="archived")
            notes = self.lib.search(self._search_buf, pool=pool)
            self.header_label.setText(f"搜索「{self._search_buf}」")

        self.note_list.blockSignals(True)
        self.note_list.setUpdatesEnabled(False)
        try:
            self.note_list.clear()
            for n in notes:
                it = QListWidgetItem()
                it.setData(Qt.UserRole, n.id)
                it.setSizeHint(QSize(0, 100))
                self.note_list.addItem(it)
        finally:
            self.note_list.setUpdatesEnabled(True)
            self.note_list.blockSignals(False)
        self.count_label.setText(str(len(notes)) if notes else "")
        if notes:
            self.note_list.show()
            self.list_empty.hide()
        else:
            self.note_list.hide()
            if self._search_buf:
                self.list_empty.setText(f"没有找到「{self._search_buf}」相关的笔记")
            elif kind == "trash":
                self.list_empty.setText("回收站是空的")
            elif kind == "archived":
                self.list_empty.setText("还没有归档的笔记")
            else:
                self.list_empty.setText("这里还没有笔记\n点「＋ 新建」开始记录")
            self.list_empty.show()

        # 保留当前选中
        target = select_id or (self.editor.note.id if self.editor.note else None)
        found = -1
        if target:
            for i in range(self.note_list.count()):
                if self.note_list.item(i).data(Qt.UserRole) == target:
                    found = i
                    break
        if found >= 0:
            self.note_list.blockSignals(True)
            self.note_list.setCurrentRow(found)
            self.note_list.blockSignals(False)
            if select_id:
                self.note_list.scrollToItem(self.note_list.item(found))
            self.editor.set_note(self.lib.notes.get(target))
        else:
            self.note_list.blockSignals(True)
            self.note_list.setCurrentRow(-1)
            self.note_list.blockSignals(False)
            self.note_list.scrollToTop()
            self.editor.set_note(None)

        if animate and notes:
            self._fade_in(self.note_list, 170)

    def _check_reminders(self):
        """把到点的提醒弹出来（每条只提醒一次）。"""
        due = self.lib.due_reminders()
        if not due:
            return
        names = "、".join(n.display_title(self.lib.content(n.id)) for n in due[:3])
        if len(due) > 3:
            names += " 等"
        text = f"{len(due)} 条笔记到时间了：{names}"
        if self.tray is not None:
            self.tray.showMessage("Timo 提醒", text, QSystemTrayIcon.Information, 8000)
        if self.isVisible():
            self._toast(text, 6000)
            QApplication.alert(self, 0)  # 任务栏图标闪烁，直到用户回到窗口
            self._reload_notes()
        else:
            self._reload_notes(select_id=self.editor.note.id if self.editor.note else None)

    def _on_notes_delete_key(self, note_ids):
        """列表上按 Delete：移到回收站（回收站里的笔记不在这里处理）。"""
        ids = [
            i
            for i in note_ids
            if i in self.lib.notes and self.lib.notes[i].state != "trash"
        ]
        if not ids:
            self._toast("回收站里的笔记请用右键彻底删除")
            return
        from .dialogs import confirm

        if not confirm(self, "移到回收站", f"把 {len(ids)} 条笔记移到回收站？"):
            return
        self._flush_save()
        for nid in ids:
            self.lib.delete_note(nid)
        self.lib.save()
        self.refresh_topics()
        self._reload_notes(animate=True)
        self._toast(f"已移到回收站（{len(ids)} 条）")

    def _on_topics_reordered(self):
        """主题拖动排序后，按界面顺序写回 order 并保存。"""
        ids = []
        for i in range(self.topic_list.count()):
            it = self.topic_list.item(i)
            topic = it.data(Qt.UserRole) if it else None
            tid = getattr(topic, "id", None)
            if tid:
                ids.append(tid)
        if len(ids) < 2:
            return
        self.lib.reorder_topics(ids)

    def _move_targets(self):
        """右键「移动到主题」的可选目标：正常主题 + 归档主题（回收站里的不给选）。"""
        ts = [t for t in self.lib.topics.values() if t.state != "trash"]
        ts.sort(key=lambda t: (t.order, t.created_at))
        return ts

    def _move_label(self, t) -> str:
        return t.name + ("（已归档）" if t.state == "archived" else "")

    def _on_notes_dropped(self, note_ids, topic_id: str):
        """把笔记（可多选）拖到左侧主题上：批量移动到该主题。"""
        ids = [i for i in note_ids if i in self.lib.notes]
        if not ids:
            return
        self._flush_save()
        moved = self.lib.move_notes(ids, topic_id)
        if not moved:
            return
        self.refresh_topics()
        self._reload_notes(animate=True)
        if len(ids) > 1:
            self._toast(f"已移动 {len(ids)} 条笔记")

    def _on_note_changed(self, row: int):
        if row < 0:
            return
        it = self.note_list.item(row)
        if not it:
            return
        self._flush_save()
        nid = it.data(Qt.UserRole)
        note = self.lib.notes.get(nid)
        self.editor.set_note(note)

    def _note_menu(self, pos):
        items = self.note_list.selectedItems()
        if len(items) > 1:
            self._bulk_menu(pos, items)
            return
        it = self.note_list.itemAt(pos)
        if not it:
            return
        nid = it.data(Qt.UserRole)
        note = self.lib.notes.get(nid)
        if not note:
            return
        menu = QMenu(self)
        a_pin = menu.addAction("取消置顶" if note.pinned_at else "置顶")
        color_menu = menu.addMenu("颜色标记")
        for name, col in NOTE_COLORS:
            act = color_menu.addAction(color_icon(col), name)
            act.setData(col)
            if col == note.color:
                act.setCheckable(True)
                act.setChecked(True)
        menu.addSeparator()
        a_arch = menu.addAction("取消归档" if note.state == "archived" else "归档")
        move_menu = menu.addMenu("移动到主题")
        for t in self._move_targets():
            if t.id != note.topic_id:
                act = move_menu.addAction(self._move_label(t))
                act.setData(t.id)
        a_dup = menu.addAction("复制笔记")
        a_copy_md = menu.addAction("复制为 Markdown")
        a_export_md = menu.addAction("导出为 Markdown…")
        a_export_pdf = menu.addAction("导出为 PDF…")
        menu.addSeparator()
        a_del = a_restore = None
        if note.state == "trash":
            a_restore = menu.addAction("从回收站恢复")
        else:
            a_del = menu.addAction("删除到回收站")
        act = menu.exec_(self.note_list.mapToGlobal(pos))
        if act is a_pin:
            self.lib.toggle_pin(nid)
        elif act is a_arch:
            self.lib.archive_note(nid, note.state != "archived")
        elif act is a_dup:
            n = self.lib.add_note(note.topic_id, note.type, self.lib.content(nid), note.title)
            n.url, n.account, n.password, n.remark = note.url, note.account, note.password, note.remark
            n.date, n.images, n.description = note.date, list(note.images), note.description
        elif act is a_copy_md:
            QApplication.clipboard().setText(note_markdown(note, self.lib.content(nid)))
            self._toast("已复制 Markdown")
        elif act is a_export_md:
            self._export_markdown(note)
        elif act is a_export_pdf:
            self._export_pdf(note)
        elif act is a_del:
            self.lib.delete_note(nid)
        elif act is a_restore:
            self.lib.restore_note(nid)
        elif act and act.parent() is color_menu:
            self.lib.toggle_color(nid, act.data())
        elif act and act.parent() is move_menu:
            self.lib.move_note(nid, act.data())
        self.lib.save()
        self.refresh_topics()
        self._reload_notes(animate=act in (a_del, a_arch, a_restore, a_dup))

    def _bulk_menu(self, pos, items):
        """多选时的批量操作菜单。"""
        ids = [it.data(Qt.UserRole) for it in items if it.data(Qt.UserRole) in self.lib.notes]
        n = len(ids)
        if not n:
            return
        menu = QMenu(self)
        if self.view[0] == "trash":
            a_restore = menu.addAction(f"恢复 {n} 条")
            a_pin = a_arch = None
        else:
            a_pin = menu.addAction(f"置顶 {n} 条")
            a_arch = menu.addAction(f"归档 {n} 条")
            a_restore = None
        move_menu = menu.addMenu(f"移动到主题（{n} 条）")
        for t in self._move_targets():
            act = move_menu.addAction(self._move_label(t))
            act.setData(t.id)
        menu.addSeparator()
        a_del = menu.addAction(f"删除 {n} 条")
        act = menu.exec_(self.note_list.mapToGlobal(pos))
        if act is None:
            return
        if act is a_pin:
            self._bulk_apply(ids, "pin")
        elif act is a_arch:
            self._bulk_apply(ids, "archive")
        elif act is a_restore:
            self._bulk_apply(ids, "restore")
        elif act is a_del:
            self._bulk_apply(ids, "delete")
        elif act.parent() is move_menu:
            self._bulk_apply(ids, "move", act.data())

    def _bulk_apply(self, ids, kind: str, payload=None):
        """对一批笔记执行同一操作。kind: pin/archive/restore/delete/move"""
        self._flush_save()
        for nid in ids:
            note = self.lib.notes.get(nid)
            if note is None:
                continue
            if kind == "pin":
                if not note.pinned_at:
                    self.lib.toggle_pin(nid)
            elif kind == "archive":
                self.lib.archive_note(nid, True)
            elif kind == "restore":
                self.lib.restore_note(nid)
            elif kind == "delete":
                self.lib.delete_note(nid)
            elif kind == "move" and payload:
                self.lib.move_note(nid, payload)
        self.lib.save()
        self.refresh_topics()
        self._reload_notes(animate=True)

    # ---------------- 编辑保存 ----------------
    def new_note(self, note_type: str = "note"):
        kind, tid = self.view
        topic_id = tid
        if kind != "topic" or not topic_id:
            if not self.lib.topics:
                self.new_topic()
                if not self.lib.topics:
                    return
            t = self.lib.sorted_topics()[0]
            topic_id = t.id
        note = self.lib.add_note(topic_id, note_type, "", None)
        self.lib.save()
        self.refresh_topics()
        if self.view != ("topic", topic_id):
            self.view = ("topic", topic_id)
            for i in range(self.topic_list.count()):
                if self.topic_list.item(i).data(Qt.UserRole).id == topic_id:
                    self.topic_list.blockSignals(True)
                    self.topic_list.setCurrentRow(i)
                    self.topic_list.blockSignals(False)
                    break
        self._reload_notes(select_id=note.id, animate=True)
        self.editor._content_widget().setFocus()

    def _on_content_changed(self, note_id: str, content: str, title: str):
        self._pending_save = (note_id, content, title)
        self._save_timer.start()

    def _on_meta_changed(self):
        self.refresh_topics()
        self._reload_notes()

    def _flush_save(self):
        if not self._pending_save:
            return
        note_id, content, title = self._pending_save
        self._pending_save = None
        note = self.lib.notes.get(note_id)
        if not note:
            return
        self.lib.set_content(note_id, content)
        if self.editor.note and self.editor.note.id == note_id:
            self.editor.flush_note()
        if note.type == "article" and title is not None:
            note.title = title.strip() or None
        self.lib.touch(note_id)
        try:
            self.lib.save()
        except OSError as exc:  # 磁盘满、目录只读、文件被杀软占用
            self._save_failed(exc)
            return
        self._save_error_shown = False
        self.editor.mark_saved()
        self._refresh_item(note_id)

    def _save_failed(self, exc: OSError) -> None:
        """写盘失败时不要吞掉：把状态标成未保存，并提示一次原因。"""
        self.editor.save_state.setText("未保存")
        if getattr(self, "_save_error_shown", False):
            return
        self._save_error_shown = True
        self._toast("保存失败：磁盘可能已满，或数据目录没有写入权限", 6000)

    def save_now(self):
        self._save_timer.stop()
        self._flush_save()

    def _refresh_item(self, note_id: str):
        for i in range(self.note_list.count()):
            if self.note_list.item(i).data(Qt.UserRole) == note_id:
                self.note_list.update(self.note_list.indexFromItem(self.note_list.item(i)))
                break

    def _toggle_preview(self):
        m = getattr(self.editor, "_mode", "split")
        self.editor.set_mode("preview" if m != "preview" else "split")

    def _on_search_changed(self, text: str):
        self._search_buf = text.strip()
        self._search_timer.start()

    def _apply_search(self):
        term = self.search.text().strip()
        self._search_buf = term
        self.editor.set_highlight(term if term else "")
        self._reload_notes(animate=True)
        # 搜索后直接落在第一条命中上，右侧就能看到高亮
        if term and self.note_list.count():
            self.note_list.setCurrentRow(0)

    # ---------------- 数据操作 ----------------
    def import_zip(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 Timo 导出包", "", "Timo 导出 (*.zip);;所有文件 (*)")
        if not path:
            return
        self._do_import(path)

    def import_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择导出文件夹（含 manifest.json）")
        if not path:
            return
        self._do_import(path)

    # ---------------- 拖拽导入 ----------------
    TEXT_EXTS = (".md", ".markdown", ".txt")

    @staticmethod
    def _droppable(path: str) -> bool:
        if not path:
            return False
        low = path.lower()
        return low.endswith(".zip") or low.endswith(MainWindow.TEXT_EXTS) or Path(path).is_dir()

    def _has_droppable(self, e) -> bool:
        md = e.mimeData()
        if md is None or not md.hasUrls():
            return False
        return any(self._droppable(u.toLocalFile()) for u in md.urls())

    def dragEnterEvent(self, e):
        if self._has_droppable(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self._has_droppable(e):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        md = e.mimeData()
        if md is not None and md.hasUrls():
            for u in md.urls():
                p = u.toLocalFile()
                if self._droppable(p):
                    e.acceptProposedAction()
                    if p.lower().endswith(MainWindow.TEXT_EXTS):
                        self._import_text_file(p)
                    else:
                        self._do_import(p)
                    return
        e.ignore()

    def _import_text_file(self, path: str):
        """把 .md / .txt 拖进来 → 在当前主题新建一条笔记。"""
        try:
            raw = Path(path).read_bytes()
        except OSError as exc:
            self._toast(f"读不了这个文件：{exc}")
            return
        text = None
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            self._toast("这个文件的编码认不出来")
            return
        stem = Path(path).stem.strip() or "新笔记"
        body = text.replace("\r\n", "\n").strip()
        title = ""
        lines = body.split("\n")
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            body = "\n".join(lines[1:]).strip()
        topic_id = self.view[1] if self.view[0] == "topic" and self.view[1] else None
        if not topic_id:
            topics = self.lib.sorted_topics()
            topic_id = topics[0].id if topics else self.lib.add_topic("我的笔记").id
        if title:
            note = self.lib.add_note(topic_id, "article", content=body, title=title)
        else:
            note = self.lib.add_note(topic_id, "note", content=body, title=stem)
        self.lib.save()
        self.refresh_topics()
        self._reload_notes(select_id=note.id, animate=True)
        self._toast(f"已导入「{note.display_title(self.lib.content(note.id))}」")

    def _do_import(self, path: str):
        mode = "replace"
        if self.lib.notes:
            from .dialogs import ImportModeDialog

            pick = ImportModeDialog(self, len(self.lib.notes))
            if not pick.exec_() or not pick.mode:
                return
            mode = pick.mode
        dlg = ProgressDialog(self, "导入 Timo 数据", "正在导入…")
        dlg.show()
        QApplication.processEvents()

        def progress(done: int, total: int):
            dlg.set_progress(done, total)
            QApplication.processEvents()
            if dlg.was_canceled():
                raise ImportCanceled()

        backup = None
        try:
            backup = self._backup_current() if mode == "replace" else None
            report = import_export(path, self.lib, progress=progress, mode=mode)
            self.lib.save()
        except ImportCanceled:
            dlg.close()
            restored = self._restore_from_backup(backup) if backup else False
            if restored:
                info(self, "已取消", "导入已取消，数据已还原成导入前的样子。")
            else:
                info(self, "已取消", "导入已取消。")
            return
        except Exception as e:  # noqa: BLE001
            dlg.close()
            error(self, "导入失败", f"{e}")
            return
        dlg.close()
        self.refresh_topics()
        self.select_nav("all")
        msg = report.summary().split("\n")[0] + "。"
        if report.skipped:
            msg += f"\n跳过已存在的笔记 {report.skipped} 条。"
        if report.missing_attachments:
            msg += f"\n有 {len(report.missing_attachments)} 个附件缺失。"
        if report.warnings:
            msg += "\n" + "\n".join(report.warnings[:5])
        if backup:
            msg += f"\n原数据已备份到：{backup}"
        info(self, "导入完成", msg)

    def _restore_from_backup(self, bdir: Path | None) -> bool:
        """导入被取消时把库还原回导入前。"""
        if not bdir or not bdir.exists():
            return False
        import shutil

        try:
            meta = bdir / "library.json"
            if meta.exists():
                shutil.copy2(meta, self.lib.meta_path)
            for name, real in (("notes", self.lib.notes_dir), ("attachments", self.lib.attachments_dir)):
                src = bdir / name
                if not src.exists():
                    continue
                if real.exists():
                    shutil.rmtree(real)
                shutil.copytree(src, real)
            self.lib.load()
            self.editor.set_note(None)
            self.refresh_topics()
            self._reload_notes()
            return True
        except Exception:
            return False

    def _backup_current(self) -> Path | None:
        if not self.lib.notes:
            return None
        import time

        bdir = self.lib.root / "backup" / time.strftime("%Y%m%d-%H%M%S")
        bdir.mkdir(parents=True, exist_ok=True)
        import shutil

        if self.lib.meta_path.exists():
            shutil.copy2(self.lib.meta_path, bdir / "library.json")
        if self.lib.notes_dir.exists():
            shutil.copytree(self.lib.notes_dir, bdir / "notes")
        if self.lib.attachments_dir.exists():
            shutil.copytree(self.lib.attachments_dir, bdir / "attachments")
        return bdir

    def empty_trash(self):
        """回收站里彻底删掉，和手机版一样有二次确认。"""
        notes = self.lib.sorted_notes(state="trash")
        if not notes:
            info(self, "清空回收站", "回收站是空的。")
            return
        if not confirm(self, "清空回收站", f"回收站里的 {len(notes)} 条笔记会被永久删除，无法恢复。继续？"):
            return
        for n in notes:
            self.lib.delete_note(n.id, hard=True)
        self.lib.save()
        self.refresh_topics()
        self._reload_notes(animate=True)

    def clean_attachments(self):
        """删掉 attachments/ 里没有任何笔记引用的图片（粘贴后又删掉文字常会留下）。"""
        unused = self.lib.unused_attachments()
        if not unused:
            info(self, "清理未使用的图片", "没有发现多余的图片，附件目录是干净的。")
            return
        size = 0
        for name in unused:
            try:
                size += self.lib.attachment_path(name).stat().st_size
            except OSError:
                pass
        sample = "、".join(unused[:3]) + ("…" if len(unused) > 3 else "")
        if not confirm(
            self,
            "清理未使用的图片",
            f"有 {len(unused)} 个图片文件没有被任何笔记引用（约 {size / 1024 / 1024:.1f} MB）：\n{sample}\n\n"
            "删除后无法恢复（备份里也不含附件）。继续？",
        ):
            return
        n = self.lib.purge_attachments(unused)
        self._toast(f"已清理 {n} 个文件")

    def export_zip(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出为 Timo ZIP", f"Timo_Desktop_Export_{_stamp()}.zip", "ZIP (*.zip)"
        )
        if not path:
            return
        try:
            out, counts = export_zip(self.lib, path)
        except Exception as e:  # noqa: BLE001
            error(self, "导出失败", str(e))
            return
        info(
            self,
            "导出完成",
            f"已导出到：\n{out}\n\n{counts['topics']} 个主题、{counts['documents']} 条笔记、{counts['attachments']} 个附件。",
        )

    def backup_dialog(self):
        from .dialogs import BackupDialog

        d = BackupDialog(self, self.lib)
        if d.exec_() and d.restored:
            self.editor.set_note(None)
            self.refresh_topics()
            self._reload_notes(animate=True)

    def open_data_dir(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.lib.root)))

    def _toast(self, text: str, ms: int = 1600):
        """不改变布局的小提示：贴着鼠标弹一个 tooltip。"""
        QToolTip.showText(QCursor.pos(), text, self)

    def _export_markdown(self, note: Note):
        content = self.lib.content(note.id)
        md = note_markdown(note, content)
        # 导出包用 ../../../attachments/，单独导出时改成相对当前目录
        md = md.replace("../../../attachments/", "attachments/")
        t = self.lib.topics.get(note.topic_id)
        title = note.display_title(content, t.name if t else "")
        safe = re.sub(r'[\\/:*?"<>|]', "_", title).strip()[:60] or "未命名"
        path, _ = QFileDialog.getSaveFileName(self, "导出为 Markdown", f"{safe}.md", "Markdown (*.md)")
        if not path:
            return
        p = Path(path)
        try:
            p.write_text(md, encoding="utf-8")
            copied = 0
            for rel in sorted(set(re.findall(r"\]\((attachments/[^)\s]+)\)", md))):
                name = rel.split("/", 1)[1]
                src = self.lib.attachment_abspath(name)
                if src and Path(src).exists():
                    dst = p.parent / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1
        except OSError as e:
            error(self, "导出失败", f"写入文件时出错：\n{e}")
            return
        extra = f"，图片 {copied} 张" if copied else ""
        info(self, "已导出", f"已保存到\n{p}{extra}")

    def _export_pdf(self, note: Note):
        """把笔记排成 PDF（用预览同一套渲染）。"""
        from PyQt5.QtGui import QTextDocument
        from PyQt5.QtPrintSupport import QPrinter

        from ..render import render

        content = self.lib.content(note.id)
        t = self.lib.topics.get(note.topic_id)
        title = note.display_title(content, t.name if t else "")
        safe = re.sub(r'[\\/:*?"<>|]', "_", title).strip()[:60] or "未命名"
        path, _ = QFileDialog.getSaveFileName(self, "导出为 PDF", f"{safe}.pdf", "PDF (*.pdf)")
        if not path:
            return
        doc = QTextDocument()
        doc.setHtml(render(content, self.lib.root))
        doc.setDocumentMargin(0)
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageMargins(16, 16, 16, 16, QPrinter.Millimeter)
        try:
            doc.print_(printer)
        except Exception as e:  # pragma: no cover - 打印机子系统异常
            error(self, "导出失败", f"写入 PDF 时出错：\n{e}")
            return
        if not Path(path).exists():
            error(self, "导出失败", "没有生成文件，请换个位置再试。")
            return
        self._toast(f"已导出 {Path(path).name}")

    def export_md_tree(self):
        """导出成「主题/笔记.md + attachments/」，方便交给别的编辑器。"""
        from ..exporter import export_markdown_tree

        out = QFileDialog.getExistingDirectory(self, "选择导出位置", str(Path.home()))
        if not out:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            counts = export_markdown_tree(self.lib, out)
        except OSError as e:
            QApplication.restoreOverrideCursor()
            error(self, "导出失败", f"写入时出错：\n{e}")
            return
        QApplication.restoreOverrideCursor()
        info(
            self,
            "导出完成",
            f"主题 {counts['topics']} 个、笔记 {counts['notes']} 条、图片 {counts['attachments']} 张。\n\n{out}",
        )

    def set_sort(self, mode: str):
        if mode == getattr(self, "sort_mode", "updated"):
            return
        self.sort_mode = mode
        self.settings.set("sort_mode", mode)
        self._sync_sort_menu()
        self._reload_notes(animate=True)

    def _sync_sort_menu(self):
        labels = {"updated": "最近更新", "created": "最近创建", "title": "标题"}
        for act in self.sort_menu.actions():
            act.setChecked(act.data() == self.sort_mode)
        self.btn_sort.setToolTip(f"排序：{labels.get(self.sort_mode, '最近更新')}")

    def set_theme(self, mode: str) -> None:
        """切换浅色 / 深色 / 跟随系统，立即生效并记住选择。"""
        set_theme_mode(resolve_theme(mode))
        self.settings.set("theme_mode", mode)
        if self._theme_group:
            for act in self._theme_group.actions():
                act.setChecked(act.text() == {"light": "浅色", "dark": "深色", "system": "跟随系统"}[mode])
        QApplication.instance().setStyleSheet(app_qss())
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)
        self.title_bar.refresh_style()
        self.note_list.viewport().update()
        self.topic_list.viewport().update()
        self._edge.update()
        self.editor.refresh_theme()
        self.update()

    def trash_topics_dialog(self):
        """回收站里的主题：恢复（连同笔记）或彻底删除。"""
        from .dialogs import TrashTopicsDialog

        dlg = TrashTopicsDialog(self, self.lib)
        dlg.exec_()
        if dlg.changed:
            self.refresh_topics()
            self._reload_notes(animate=True)

    def show_about(self):
        from timodesk import __version__

        from .dialogs import AboutDialog

        AboutDialog(self, self.lib, __version__).exec_()

    def _restore_geometry(self):
        try:
            geo = self.settings.get("window_geometry")
            if geo:
                from PyQt5.QtCore import QByteArray

                self.restoreGeometry(QByteArray.fromBase64(str(geo).encode()))
        except Exception:
            pass

    def _save_geometry(self):
        try:
            self.settings.set("window_geometry", bytes(self.saveGeometry().toBase64()).decode())
        except Exception:
            pass

    def closeEvent(self, e):  # noqa: N802
        self._save_geometry()
        self._save_view()
        self.save_now()
        self.lib.save()
        # 有托盘时，关闭 = 收进托盘；从托盘菜单退出才算真退出
        if self.tray is not None and not self._quitting:
            e.ignore()
            self.hide()
            if not self._tray_hinted:
                self._tray_hinted = True
                self.tray.showMessage(
                    "Timo For Windows",
                    "已收进托盘。点托盘图标可以重新打开，右键可以退出。",
                    QSystemTrayIcon.Information,
                    4000,
                )
            return
        super().closeEvent(e)

    # ---------------- 无边框窗口 ----------------
    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.sync_max_button()
        self._apply_mask()

    def _apply_mask(self):
        if not hasattr(self, "title_bar"):
            return
        if self.isMaximized() or self.isFullScreen():
            self.clearMask()
        else:
            self.setMask(rounded_mask(self.width(), self.height()))

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        self._apply_mask()
        edge = getattr(self, "_edge", None)
        if edge is not None:
            edge.setGeometry(self.centralWidget().rect())
            edge.raise_()

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        self._apply_mask()
        if hasattr(self, "title_bar"):
            self.title_bar.sync_max_button()
        if not getattr(self, "_entered", False):
            self._entered = True
            self._play_enter_animation()

    def _play_enter_animation(self):
        """第一次出现时整体淡化进入，别太慢。"""
        central = self.centralWidget()
        if central is None:
            return
        eff = QGraphicsOpacityEffect(central)
        central.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(240)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.finished.connect(lambda: central.setGraphicsEffect(None))
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        self._enter_anim = anim

    def changeEvent(self, e):  # noqa: N802
        if e.type() == QEvent.WindowStateChange:
            QTimer.singleShot(0, self._on_window_state)
        super().changeEvent(e)

    def _on_window_state(self):
        if hasattr(self, "title_bar"):
            self.title_bar.sync_max_button()
        self._apply_mask()

    def _hit_border(self, pos: QPoint) -> int:
        """鼠标在窗口边缘时返回 Win32 命中码，交给系统处理缩放。"""
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        edge = RESIZE_BORDER
        left, right = x <= edge, x >= w - edge
        top, bottom = y <= edge, y >= h - edge
        if top and left:
            return HTTOPLEFT
        if top and right:
            return HTTOPRIGHT
        if bottom and left:
            return HTBOTTOMLEFT
        if bottom and right:
            return HTBOTTOMRIGHT
        if left:
            return HTLEFT
        if right:
            return HTRIGHT
        if top:
            return HTTOP
        if bottom:
            return HTBOTTOM
        return 0

    def nativeEvent(self, eventType, message):  # noqa: N802
        if eventType not in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            return super().nativeEvent(eventType, message)
        try:
            msg = wintypes.MSG.from_address(int(message))
        except Exception:  # noqa: BLE001
            return super().nativeEvent(eventType, message)
        if msg.message == WM_NCHITTEST and not self.isMaximized():
            pos = self.mapFromGlobal(QCursor.pos())
            if 0 <= pos.x() < self.width() and 0 <= pos.y() < self.height():
                hit = self._hit_border(pos)
                if hit:
                    return True, hit
        return super().nativeEvent(eventType, message)


class _UnusedNavDelegate:
    """占位，保留旧结构引用。"""


def _stamp() -> str:
    import time

    return time.strftime("%Y%m%d_%H%M%S")
