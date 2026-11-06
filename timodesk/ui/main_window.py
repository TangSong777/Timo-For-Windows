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
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QShortcut,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..exporter import export_zip
from ..importer import import_export
from ..store import NOTE_TYPES, TYPE_LABELS, Library, Note
from .dialogs import ProgressDialog, confirm, error, info
from .editor import NoteEditor
from .theme import C, NOTE_COLORS, color_icon


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
from .widgets import AutoFadeScrollBar, NoteCardDelegate, TopicDelegate


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
        self._quitting = False
        self._tray_hinted = False
        self._build_ui()
        self._build_shortcuts()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._flush_save)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(220)
        self._search_timer.timeout.connect(self._apply_search)
        self.refresh_topics()
        self.select_nav("all")

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
            it.setSizeHint(QSize(0, 32))
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

        self.topic_list = QListWidget(objectName="TopicList")
        self.topic_list.setVerticalScrollBar(AutoFadeScrollBar(Qt.Vertical, self.topic_list))
        self.topic_list.setItemDelegate(TopicDelegate(self.lib, self))
        self.topic_list.setFrameShape(QListWidget.NoFrame)
        self.topic_list.setDragDropMode(QListWidget.InternalMove)
        self.topic_list.setDefaultDropAction(Qt.MoveAction)
        self.topic_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.topic_list.customContextMenuRequested.connect(self._topic_menu)
        self.topic_list.currentRowChanged.connect(self._on_topic_changed)
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
        menu.addAction("打开数据目录", self.open_data_dir)
        menu.addSeparator()
        menu.addAction("清空回收站…", self.empty_trash)
        menu.addSeparator()
        menu.addAction("关于 Timo 桌面版", self.show_about)
        btn_data.setMenu(menu)
        btn_data.setPopupMode(QToolButton.InstantPopup)
        bottom.addWidget(btn_data)
        bottom.addStretch(1)
        self.total_label = QLabel("")
        self.total_label.setStyleSheet(f"color:{C['faint']};font-size:11px;")
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
        self.search.setPlaceholderText("搜索笔记…  Ctrl+F")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._on_search_changed)
        lp.addWidget(self.search)

        self.note_list = QListWidget(objectName="NoteList")
        self.note_list.setVerticalScrollBar(AutoFadeScrollBar(Qt.Vertical, self.note_list))
        self.note_list.setItemDelegate(NoteCardDelegate(self.lib, self))
        self.note_list.setFrameShape(QListWidget.NoFrame)
        self.note_list.setMouseTracking(True)
        self.note_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.note_list.setSpacing(0)
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

    # ---------------- 侧栏 ----------------
    def refresh_topics(self):
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        topics = [t for t in self.lib.topics.values() if t.state != "trash"]
        topics.sort(key=lambda t: (t.order, t.created_at))
        for t in topics:
            it = QListWidgetItem(t.name)
            it.setData(Qt.UserRole, t)
            it.setToolTip(f"{t.name} · {self.lib.note_counts().get(t.id, 0)} 条")
            self.topic_list.addItem(it)
        self.topic_list.blockSignals(False)
        active = sum(1 for n in self.lib.notes.values() if n.state == "active")
        total = len(self.lib.notes)
        self.total_label.setText(f"{active} / {total} 条")

    def select_nav(self, kind: str):
        row = {"all": 0, "archived": 1, "trash": 2}.get(kind, 0)
        self.nav.setCurrentRow(row)

    def _on_nav_changed(self, row: int):
        kind = {0: "all", 1: "archived", 2: "trash"}.get(row, "all")
        self.topic_list.clearSelection()
        self.topic_list.setCurrentRow(-1)
        self.view = (kind, None)
        self._reload_notes(animate=True)

    def _on_topic_changed(self, row: int):
        if row < 0:
            return
        it = self.topic_list.item(row)
        if not it:
            return
        topic = it.data(Qt.UserRole)
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
            name, ok = QInputDialog.getText(self, "重命名主题", "主题名称：", text=topic.name)
            if ok and name.strip():
                self.lib.rename_topic(topic.id, name.strip())
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

    def new_topic(self):
        name, ok = QInputDialog.getText(self, "新建主题", "主题名称：")
        if not ok or not name.strip():
            return
        t = self.lib.add_topic(name.strip())
        self.lib.save()
        self.refresh_topics()
        for i in range(self.topic_list.count()):
            if self.topic_list.item(i).data(Qt.UserRole).id == t.id:
                self.topic_list.setCurrentRow(i)
                break

    # ---------------- 列表 ----------------
    def _current_notes(self) -> list[Note]:
        kind, tid = self.view
        if kind == "all":
            return self.lib.sorted_notes(state="active")
        if kind == "archived":
            return self.lib.sorted_notes(state="archived")
        if kind == "trash":
            return self.lib.sorted_notes(state="trash")
        t = self.lib.topics.get(tid)
        state = "archived" if (t and t.state == "archived") else "active"
        return self.lib.topic_notes(tid, state=state)

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
        self.note_list.clear()
        for n in notes:
            it = QListWidgetItem()
            it.setData(Qt.UserRole, n.id)
            it.setSizeHint(QSize(0, 100))
            self.note_list.addItem(it)
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
        for t in self.lib.sorted_topics():
            if t.id != note.topic_id:
                act = move_menu.addAction(t.name)
                act.setData(t.id)
        a_dup = menu.addAction("复制笔记")
        menu.addSeparator()
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
        self.lib.save()
        self.editor.mark_saved()
        self._refresh_item(note_id)

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
        self._reload_notes(animate=True)

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

    def _do_import(self, path: str):
        if self.lib.notes:
            if not confirm(
                self,
                "导入数据",
                "导入会用包里的内容替换当前库（现有笔记会先备份到 backup 目录）。继续？",
            ):
                return
        dlg = ProgressDialog(self, "导入 Timo 数据", "正在导入…")
        dlg.show()
        QApplication.processEvents()

        def progress(done: int, total: int):
            dlg.set_progress(done, total)
            QApplication.processEvents()
            if dlg.was_canceled():
                raise RuntimeError("用户取消")

        try:
            backup = self._backup_current()
            report = import_export(path, self.lib, progress=progress)
            self.lib.save()
        except Exception as e:  # noqa: BLE001
            dlg.close()
            error(self, "导入失败", f"{e}")
            return
        dlg.close()
        self.refresh_topics()
        self.select_nav("all")
        msg = f"导入完成：{report.topics} 个主题、{report.notes} 条笔记、{report.attachments} 个附件。"
        if report.missing_attachments:
            msg += f"\n有 {len(report.missing_attachments)} 个附件缺失。"
        if report.warnings:
            msg += "\n" + "\n".join(report.warnings[:5])
        if backup:
            msg += f"\n原数据已备份到：{backup}"
        info(self, "导入完成", msg)

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

    def open_data_dir(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.lib.root)))

    def show_about(self):
        from timodesk import __version__

        info(
            self,
            "关于 Timo For Windows",
            f"<h3>Timo For Windows {__version__}</h3>"
            "<p>Windows 本地笔记软件，可导入 Timo（Android）导出的数据包，"
            "数据全部保存在本机，不需要账号，也不联网。</p>"
            f"<p style='color:{C['muted']}'>数据目录：{self.lib.root}</p>"
            "<p>笔记以 Markdown 文件保存，随时可以导出为 Timo 兼容的 ZIP。</p>",
        )

    def closeEvent(self, e):  # noqa: N802
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
