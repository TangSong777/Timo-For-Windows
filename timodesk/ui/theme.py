"""Timo 桌面版的视觉主题。

黑白灰为主：浅灰画布上浮着白色圆角卡片，接近黑文字、极淡分隔线。
质感来自三层：画布底色 → 卡片（1px 边 + 柔和投影）→ 卡片内部控件。
强调色就是黑色本身（主按钮黑底白字），不引入彩色主题。
笔记的颜色标记（NOTE_COLORS）按黑白灰阶保留，属于内容不属于皮肤。
"""
from __future__ import annotations

C = {
    # 画布与卡片
    "canvas": "#ededf0",
    "paper": "#ffffff",
    "paper_alt": "#fafafb",
    "card": "#ffffff",
    "card_hover": "#f8f8fa",
    "card_border": "#ebebed",
    "card_border_strong": "#dedee2",
    # 文字
    "ink": "#1d1d1f",
    "ink_soft": "#3a3a3c",
    "muted": "#86868b",
    "faint": "#a8a8ad",
    # 分隔
    "line": "#ececee",
    "line_soft": "#f4f4f6",
    # 强调（历史命名保留：green 系列现在就是黑）
    "green": "#1d1d1f",
    "green_dark": "#000000",
    "green_soft": "#efeff1",
    "lime": "#d6d6d6",
    "lime_soft": "#ededef",
    "danger": "#1d1d1f",
    "danger_soft": "#f2f2f2",
    "amber": "#7a7a7a",
    "shadow": "rgba(0, 0, 0, 0.06)",
}

# 笔记颜色标记（Timo 的 color 字段），默认无标记
NOTE_COLORS = [
    ("无", None),
    ("浅灰", "#e8e8e8"),
    ("灰", "#d4d4d4"),
    ("中灰", "#bfbfbf"),
    ("深灰", "#a3a3a3"),
    ("石墨", "#7a7a7a"),
    ("炭灰", "#565656"),
    ("墨黑", "#262626"),
]

FONT_UI = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif'
FONT_TEXT = '"Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif'
FONT_MONO = '"Cascadia Code", "Consolas", "JetBrains Mono", monospace'


def color_icon(col, size: int = 14):
    """画一个小圆角色块，给「颜色标记」菜单用。col 为 None 时画空心圈（表示无）。"""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if col:
        p.setBrush(QColor(col))
        p.setPen(Qt.NoPen)
    else:
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(C["card_border_strong"]), 1.2))
    p.drawRoundedRect(1, 1, size - 2, size - 2, 4, 4)
    p.end()
    return QIcon(pm)


def add_shadow(widget, blur: int = 26, y: int = 6, alpha: int = 24):
    """给控件挂一层柔和投影。只用在数量少、不随滚动重绘的控件上。"""
    from PyQt5.QtGui import QColor
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect

    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, y)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return eff


def app_qss(scale: float = 1.0) -> str:
    s = scale
    return f"""
* {{ outline: none; }}
QWidget {{
    font-family: {FONT_UI};
    font-size: {int(13 * s)}px;
    color: {C['ink']};
}}
QMainWindow, #Root, #Body {{ background: {C['canvas']}; }}

/* ---------- 卡片容器 ---------- */
#Sidebar, #ListPane, #EditorPane {{
    background: {C['card']};
    border: 1px solid {C['card_border']};
    border-radius: 16px;
}}

/* ---------- 侧栏 ---------- */
#Brand {{
    font-family: {FONT_TEXT};
    font-size: {int(23 * s)}px;
    font-weight: 600;
    color: {C['ink']};
    letter-spacing: 0.4px;
}}
#BrandSub {{ color: {C['muted']}; font-size: {int(11 * s)}px; }}
#SideSection {{ color: {C['faint']}; font-size: {int(11 * s)}px; font-weight: 600; padding: 2px 6px; }}
#NewTopicBtn {{
    background: {C['paper_alt']}; border: 1px solid {C['card_border']};
    border-radius: 10px; color: {C['muted']}; padding: 8px 10px;
}}
#NewTopicBtn:hover {{ border-color: {C['card_border_strong']}; color: {C['ink']}; background: #f2f2f5; }}

QListWidget#TopicList, QListWidget#NavList {{
    background: {C['card']}; border: none;
}}
QListWidget#NavList::item {{
    border-radius: 9px; padding: 8px 9px; margin: 1px 3px;
}}
QListWidget#NavList::item:selected {{
    background: #ececee; color: {C['ink']};
    border-left: 2px solid {C['ink']};
}}
QListWidget#NavList::item:hover {{
    background: {C['card_hover']};
}}

QListWidget#Wall {{ background: transparent; border: none; }}
QListWidget#Wall::item {{ border-radius: 10px; margin: 2px; }}
QListWidget#Wall::item:hover {{ background: #f4f4f6; }}
QListWidget#Wall::item:selected {{ background: #eaeaec; }}

/* ---------- 中栏 ---------- */
#ListHeader {{ font-size: {int(15 * s)}px; font-weight: 600; color: {C['ink']}; }}
#CountLabel {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#Search {{
    background: #f5f5f7; border: 1px solid transparent; border-radius: 11px;
    padding: 9px 13px; selection-background-color: {C['ink']}; selection-color: #fff;
}}
QLineEdit#Search:focus {{ background: {C['card']}; border: 1px solid {C['ink']}; }}

QListWidget#NoteList {{ background: {C['card']}; border: none; padding: 2px; }}
QListWidget#NoteList::item {{ border: none; margin: 0px; }}

QPushButton#NewNoteBtn {{
    background: {C['ink']}; color: #ffffff; border: none; border-radius: 10px;
    padding: 9px 15px; font-weight: 600;
}}
QPushButton#NewNoteBtn:hover {{ background: #000000; }}
QPushButton#NewNoteBtn:pressed {{ background: #333333; }}

/* ---------- 编辑区 ---------- */
#EditorTopBar {{ background: {C['card']}; border-bottom: 1px solid {C['line_soft']}; }}
#TypeBadge {{
    color: {C['ink_soft']}; background: #f2f2f4;
    border-radius: 7px; padding: 3px 9px; font-size: {int(11 * s)}px; font-weight: 600;
}}
#SaveState {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#NoteTitle {{
    background: transparent; border: none; padding: 2px 0;
    font-family: {FONT_TEXT}; font-size: {int(22 * s)}px; font-weight: 500; color: {C['ink']};
}}
QLineEdit#NoteTitle::placeholder {{ color: {C['faint']}; }}
QLineEdit#NoteTitle:focus {{ border-bottom: 1px solid {C['card_border']}; }}

QPlainTextEdit#Editor {{
    background: {C['card']}; border: none; padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: #d9d9dd; selection-color: {C['ink']};
}}
QTextBrowser#Preview {{
    background: {C['paper_alt']}; border: none; border-left: 1px solid {C['line']};
    padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: #d9d9dd;
}}

/* 格式栏：一条浅浅的卡片 */
#FormatBar {{
    background: {C['card']}; border: 1px solid {C['line_soft']};
    border-radius: 12px; margin: 6px 16px 2px 16px;
}}
#FormatBar QToolButton {{ padding: 4px 6px; border-radius: 7px; }}

/* 类型页内部的小卡片（账号 / 日子 / 链接） */
#Card {{
    background: #fbfbfc; border: 1px solid {C['card_border']};
    border-radius: 14px;
}}
#Card QLabel {{ color: {C['muted']}; font-size: {int(12 * s)}px; background: transparent; border: none; }}
#Card QLineEdit {{
    background: transparent; border: none; border-radius: 8px; padding: 6px 4px;
    font-size: {int(15 * s)}px;
}}
#Card QLineEdit:focus {{ background: {C['card']}; }}

QToolButton {{
    background: transparent; border: none; border-radius: 8px; padding: 5px 7px; color: {C['ink_soft']};
}}
QToolButton:hover {{ background: #f1f1f3; color: {C['ink']}; }}
QToolButton:checked {{ background: #e6e6e9; color: {C['ink']}; }}
QToolButton:pressed {{ background: #dcdce0; }}

/* ---------- 通用按钮 ---------- */
QPushButton {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 9px;
    padding: 7px 14px; color: {C['ink']};
}}
QPushButton:hover {{ border-color: {C['ink']}; background: {C['card']}; }}
QPushButton:pressed {{ background: #f1f1f3; }}
QPushButton:default {{ background: {C['ink']}; color: white; border: none; }}
QPushButton:default:hover {{ background: #000000; }}
QPushButton:disabled {{ color: {C['faint']}; border-color: {C['line']}; background: {C['paper_alt']}; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px 2px; }}
QScrollBar::handle:vertical {{ background: #d8d8dc; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: #bdbdc4; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 3px; }}
QScrollBar::handle:horizontal {{ background: #d8d8dc; border-radius: 4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- 菜单 ---------- */
QMenu {{
    background: {C['card']}; border: 1px solid {C['card_border']}; border-radius: 11px; padding: 6px;
}}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 7px; }}
QMenu::item:selected {{ background: #f1f1f3; color: {C['ink']}; }}
QMenu::separator {{ height: 1px; background: {C['line']}; margin: 5px 8px; }}

QToolTip {{
    background: {C['ink']}; color: #fff; border: none; padding: 6px 9px; border-radius: 7px;
}}

/* ---------- 对话框 ---------- */
QDialog {{ background: {C['canvas']}; }}
QDialog QLabel {{ color: {C['ink']}; }}
#DialogBody {{ background: {C['card']}; }}
QComboBox {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 9px; padding: 6px 10px;
}}
QComboBox:focus {{ border-color: {C['ink']}; }}
QComboBox QAbstractItemView {{
    background: {C['card']}; border: 1px solid {C['card_border']}; selection-background-color: #f1f1f3;
    selection-color: {C['ink']}; outline: none;
}}
QSpinBox {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 9px; padding: 5px 8px;
}}
QCheckBox {{ spacing: 8px; }}
QSplitter::handle {{ background: {C['line_soft']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
"""
