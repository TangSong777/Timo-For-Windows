"""Timo 桌面版的视觉主题。

黑白灰为主：浅灰画布上浮着圆角卡片，接近黑文字、极淡分隔线。
质感来自三层：画布底色 → 卡片（1px 边 + 柔和投影）→ 卡片内部控件。
强调色就是黑本身（主按钮黑底白字），不引入彩色主题。
笔记的颜色标记（NOTE_COLORS）按黑白灰阶保留，属于内容不属于皮肤。

支持两套皮肤：light / dark，运行时用 set_mode() 切换，C 是原地更新的字典，
各模块 `from .theme import C` 拿到的引用会跟着变。
"""
from __future__ import annotations

LIGHT = {
    # 画布与卡片
    "canvas": "#f1f1f2",
    "titlebar": "#ffffff",
    "sidebar": "#fafafb",
    "paper": "#ffffff",
    "paper_alt": "#fafafb",
    "card": "#ffffff",
    "card_soft": "#fbfbfc",
    "card_hover": "#f8f8fa",
    "card_border": "#ececee",
    "card_border_strong": "#dedee2",
    # 文字
    "ink": "#1d1d1f",
    "ink_soft": "#3a3a3c",
    "muted": "#86868b",
    "faint": "#a8a8ad",
    "on_ink": "#ffffff",
    # 分隔
    "line": "#ececee",
    "line_soft": "#f4f4f6",
    # 控件状态
    "input_bg": "#f4f4f5",
    "hover_bg": "#f1f1f3",
    "press_bg": "#dcdce0",
    "checked_bg": "#e6e6e9",
    "sel_bg": "#d9d9dd",
    "wall_hover": "#f4f4f6",
    "wall_sel": "#eaeaec",
    "btn_hover": "#000000",
    "btn_press": "#333333",
    "close_hover": "#2e2e2e",
    "scroll": "#d8d8dc",
    "scroll_hover": "#bdbdc4",
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

DARK = {
    "canvas": "#0f0f11",
    "titlebar": "#131316",
    "sidebar": "#131316",
    "paper": "#131316",
    "paper_alt": "#17171a",
    "card": "#18181b",
    "card_soft": "#1b1b1f",
    "card_hover": "#1e1e22",
    "card_border": "#26262b",
    "card_border_strong": "#33333a",
    "ink": "#ececee",
    "ink_soft": "#c8c8cd",
    "muted": "#8e8e96",
    "faint": "#6b6b73",
    "on_ink": "#0d0d0f",
    "line": "#24242a",
    "line_soft": "#1f1f24",
    "input_bg": "#1f1f24",
    "hover_bg": "#232329",
    "press_bg": "#2a2a31",
    "checked_bg": "#2a2a31",
    "sel_bg": "#2f2f37",
    "wall_hover": "#202027",
    "wall_sel": "#2a2a31",
    "btn_hover": "#ffffff",
    "btn_press": "#d4d4d4",
    "close_hover": "#3a3a42",
    "scroll": "#3a3a42",
    "scroll_hover": "#4e4e58",
    "green": "#ececee",
    "green_dark": "#ffffff",
    "green_soft": "#232329",
    "lime": "#4a4a54",
    "lime_soft": "#22222a",
    "danger": "#ececee",
    "danger_soft": "#22222a",
    "amber": "#a8a8ad",
    "shadow": "rgba(0, 0, 0, 0.45)",
}

C = dict(LIGHT)
_mode = "light"


def set_mode(mode: str) -> str:
    """切换皮肤：light / dark。返回实际生效的模式。"""
    global _mode
    _mode = "dark" if str(mode).lower() in ("dark", "深色", "夜间") else "light"
    C.clear()
    C.update(DARK if _mode == "dark" else LIGHT)
    return _mode


def current_mode() -> str:
    return _mode


def is_dark() -> bool:
    return _mode == "dark"


# 笔记颜色标记（Timo 的 color 字段），默认无标记；深色下自动换成亮一档的灰阶
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
#Sidebar {{
    background: {C['sidebar']};
    border: 1px solid {C['card_border']};
    border-radius: 16px;
}}
#ListPane, #EditorPane {{
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
    background: {C['card']}; border: 1px solid {C['card_border']};
    border-radius: 10px; color: {C['muted']}; padding: 8px 10px;
}}
#NewTopicBtn:hover {{ border-color: {C['card_border_strong']}; color: {C['ink']}; background: {C['hover_bg']}; }}

QListWidget#TopicList, QListWidget#NavList {{
    background: transparent; border: none;
}}
QListWidget#NavList::item {{
    border-radius: 10px; padding: 10px 12px; margin: 2px 4px;
    color: {C['ink_soft']};
}}
QListWidget#NavList::item:selected {{
    background: {C['card']}; color: {C['ink']};
    border: 1px solid {C['card_border_strong']};
}}
QListWidget#NavList::item:hover {{
    background: {C['card_hover']};
}}

QListWidget#Wall {{ background: transparent; border: none; }}
QListWidget#Wall::item {{ border-radius: 10px; margin: 2px; }}
QListWidget#Wall::item:hover {{ background: {C['wall_hover']}; }}
QListWidget#Wall::item:selected {{ background: {C['wall_sel']}; }}

/* ---------- 中栏 ---------- */
#ListHeader {{ font-size: {int(18 * s)}px; font-weight: 600; color: {C['ink']}; letter-spacing: 0.2px; }}
#CountLabel {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#Search {{
    background: {C['input_bg']}; border: 1px solid transparent; border-radius: 12px;
    padding: 9px 14px; selection-background-color: {C['ink']}; selection-color: {C['on_ink']};
}}
QLineEdit#Search:focus {{ background: {C['card']}; border: 1px solid {C['ink']}; }}

QFrame#FindBar {{ background: {C['paper_alt']}; border: none; border-top: 1px solid {C['line']}; border-bottom: 1px solid {C['line']}; }}
QFrame#FindBar QLineEdit {{
    background: {C['card']}; border: 1px solid {C['card_border']}; border-radius: 8px;
    padding: 4px 9px; selection-background-color: {C['ink']}; selection-color: {C['on_ink']};
}}
QFrame#FindBar QLineEdit:focus {{ border: 1px solid {C['ink']}; }}
QFrame#FindBar QToolButton {{ border: none; border-radius: 6px; padding: 3px 6px; color: {C['muted']}; }}
QFrame#FindBar QToolButton:hover {{ background: {C['hover_bg']}; color: {C['ink']}; }}
#FindCount {{ color: {C['muted']}; font-size: {int(11 * s)}px; }}

#ListEmpty {{ color: {C['faint']}; font-size: {int(12 * s)}px; line-height:1.6; }}
QListWidget#NoteList {{ background: {C['card']}; border: none; padding: 4px 2px; }}
QListWidget#NoteList::item {{ border: none; margin: 0px; }}

QPushButton#NewNoteBtn {{
    background: {C['ink']}; color: {C['on_ink']}; border: none;
    border-radius: 10px 0 0 10px;
    padding: 9px 14px; font-weight: 600;
}}
QPushButton#NewNoteBtn:hover {{ background: {C['btn_hover']}; }}
QPushButton#NewNoteBtn:pressed {{ background: {C['btn_press']}; }}
QToolButton#SortBtn {{
    border: none; background: transparent; border-radius: 7px;
    color: {C['muted']}; font-size: {int(13 * s)}px;
}}
QToolButton#SortBtn:hover {{ background: {C['paper_alt']}; color: {C['ink']}; }}
QToolButton#SortBtn:pressed {{ background: {C['line']}; }}
QToolButton#SortBtn::menu-indicator {{ image: none; width: 0px; }}

QToolButton#NewTypeBtn {{
    background: {C['ink']}; color: {C['on_ink']}; border: none;
    border-radius: 0 10px 10px 0;
    font-size: {int(11 * s)}px;
}}
QToolButton#NewTypeBtn:hover {{ background: {C['btn_hover']}; }}
QToolButton#NewTypeBtn::menu-indicator {{ image: none; width: 0px; }}

/* ---------- 编辑区 ---------- */
#EditorTopBar {{ background: {C['card']}; border-bottom: 1px solid {C['line_soft']}; }}
#TypeBadge {{
    color: {C['ink_soft']}; background: {C['hover_bg']};
    border-radius: 7px; padding: 3px 9px; font-size: {int(11 * s)}px; font-weight: 600;
}}
#SaveState {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#NoteTitle {{
    background: transparent; border: none; padding: 2px 0;
    font-family: {FONT_TEXT}; font-size: {int(24 * s)}px; font-weight: 500; color: {C['ink']};
}}
QLineEdit#NoteTitle::placeholder {{ color: {C['faint']}; }}
QLineEdit#NoteTitle:focus {{ border-bottom: 1px solid {C['card_border']}; }}

QPlainTextEdit#Editor {{
    background: {C['card']}; border: none; padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: {C['sel_bg']}; selection-color: {C['ink']};
}}
QTextBrowser#Preview {{
    background: {C['paper_alt']}; border: none; border-left: 1px solid {C['line']};
    padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: {C['sel_bg']};
}}

/* 格式栏：一条浅浅的卡片 */
#FormatBar {{
    background: {C['card']}; border: 1px solid {C['line_soft']};
    border-radius: 12px; margin: 6px 16px 2px 16px;
}}
#FormatBar QDateEdit, QTimeEdit {{
    background: {C['card']}; border: 1px solid {C['line']};
    border-radius: 8px; padding: 6px 8px; min-height: 18px;
    selection-background-color: {C['ink']}; selection-color: {C['on_ink']};
}}
QDateEdit:focus, QTimeEdit:focus {{ border-color: {C['ink']}; }}
QDateEdit::drop-down {{ width: 22px; border: none; }}
QTimeEdit::up-button, QTimeEdit::down-button {{ width: 16px; border: none; }}

QToolButton {{ padding: 4px 6px; border-radius: 7px; }}

/* 类型页内部的小卡片（账号 / 日子 / 链接） */
#Card {{
    background: {C['card_soft']}; border: 1px solid {C['card_border']};
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
QToolButton:hover {{ background: {C['hover_bg']}; color: {C['ink']}; }}
QToolButton:checked {{ background: {C['checked_bg']}; color: {C['ink']}; }}
QToolButton:pressed {{ background: {C['press_bg']}; }}

/* ---------- 通用按钮 ---------- */
QPushButton {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 9px;
    padding: 7px 14px; color: {C['ink']};
}}
QPushButton:hover {{ border-color: {C['ink']}; background: {C['card']}; }}
QPushButton:pressed {{ background: {C['hover_bg']}; }}
QPushButton:default {{ background: {C['ink']}; color: {C['on_ink']}; border: none; }}
QPushButton:default:hover {{ background: {C['btn_hover']}; }}
QPushButton:disabled {{ color: {C['faint']}; border-color: {C['line']}; background: {C['paper_alt']}; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 3px 2px; }}
QScrollBar::handle:vertical {{ background: {C['scroll']}; border-radius: 4px; min-height: 32px; }}
QScrollBar::handle:vertical:hover {{ background: {C['scroll_hover']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px 3px; }}
QScrollBar::handle:horizontal {{ background: {C['scroll']}; border-radius: 4px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- 菜单 ---------- */
QMenu {{
    background: {C['card']}; border: 1px solid {C['card_border']}; border-radius: 11px; padding: 6px;
}}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 7px; }}
QMenu::item:selected {{ background: {C['hover_bg']}; color: {C['ink']}; }}
QMenu::separator {{ height: 1px; background: {C['line']}; margin: 5px 8px; }}

QToolTip {{
    background: {C['ink']}; color: {C['on_ink']}; border: none; padding: 6px 9px; border-radius: 7px;
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
    background: {C['card']}; border: 1px solid {C['card_border']}; selection-background-color: {C['hover_bg']};
    selection-color: {C['ink']}; outline: none;
}}
QSpinBox {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 9px; padding: 5px 8px;
}}
QCheckBox {{ spacing: 8px; }}
QSplitter::handle {{ background: {C['line_soft']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

#TotalLabel {{ color: {C['faint']}; font-size: 11px; }}
#EmptyIcon {{ font-size: 54px; color: {C['line']}; }}
#EmptyHint {{ color: {C['faint']}; font-size: 13px; }}
#WordLabel, #TimeLabel {{ color: {C['muted']}; font-size: 11px; }}
#FmtSep {{ background: {C['line']}; border: none; }}
#GalleryHint, #AccountTip {{ color: {C['muted']}; font-size: 11px; }}
#NoteDesc {{
    background: {C['card']}; border: 1px solid {C['card_border_strong']}; border-radius: 12px; padding: 12px 16px;
}}
QLabel#DateBig {{ color: {C['ink']}; font-size: 40px; font-weight: 500; background: transparent; border: none; }}
QLabel#DateSub {{ color: {C['muted']}; font-size: 13px; background: transparent; border: none; }}
"""


def system_mode() -> str:
    """读 Windows「应用模式」：浅色 → light，深色 → dark。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as k:
            light, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
        return "light" if light else "dark"
    except Exception:
        return "light"


def resolve(mode: str) -> str:
    """light / dark / system → 实际生效的 light|dark。"""
    if mode == "system":
        return system_mode()
    return "dark" if mode == "dark" else "light"
