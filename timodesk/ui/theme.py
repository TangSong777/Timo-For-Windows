"""Timo 桌面版的视觉主题。

黑白灰为主：白纸底、近黑文字、浅灰分隔线与悬停态。
强调色就是黑色本身（主按钮黑底白字），不引入彩色主题。
笔记的彩色标记（NOTE_COLORS）仍按 Timo 的 color 字段保留，属于内容不属于皮肤。
"""
from __future__ import annotations

C = {
    "paper": "#ffffff",
    "paper_alt": "#f7f7f7",
    "card": "#ffffff",
    "card_hover": "#fafafa",
    "ink": "#1f1f1f",
    "ink_soft": "#3f3f3f",
    "muted": "#737373",
    "faint": "#a3a3a3",
    "line": "#e4e4e4",
    "line_soft": "#f0f0f0",
    # 强调色（历史命名保留：green 系列现在就是黑）
    "green": "#1f1f1f",
    "green_dark": "#000000",
    "green_soft": "#efefef",
    "lime": "#d6d6d6",
    "lime_soft": "#ededed",
    "danger": "#b4302a",
    "danger_soft": "#f7e7e5",
    "amber": "#7a5c22",
    "shadow": "rgba(0, 0, 0, 0.06)",
}

# 笔记颜色标记（Timo 的 color 字段），默认无标记
NOTE_COLORS = [
    ("无", None),
    ("青柠", "#dfed95"),
    ("浅绿", "#c8e6c9"),
    ("湖蓝", "#b3e5fc"),
    ("淡紫", "#d1c4e9"),
    ("樱粉", "#f8bbd0"),
    ("杏黄", "#ffe0b2"),
    ("珊瑚", "#ffccbc"),
]

FONT_UI = '"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif'
FONT_TEXT = '"Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif'
FONT_MONO = '"Cascadia Code", "Consolas", "JetBrains Mono", monospace'


def app_qss(scale: float = 1.0) -> str:
    s = scale
    return f"""
* {{ outline: none; }}
QWidget {{
    font-family: {FONT_UI};
    font-size: {int(13 * s)}px;
    color: {C['ink']};
}}
QMainWindow, #Root {{ background: {C['paper']}; }}

/* ---------- 侧栏 ---------- */
#Sidebar {{
    background: {C['paper_alt']};
    border-right: 1px solid {C['line']};
}}
#Brand {{
    font-family: {FONT_TEXT};
    font-size: {int(23 * s)}px;
    font-weight: 600;
    color: {C['ink']};
    letter-spacing: 0.5px;
}}
#BrandSub {{ color: {C['muted']}; font-size: {int(11 * s)}px; }}
#SideSection {{ color: {C['faint']}; font-size: {int(11 * s)}px; font-weight: 600; padding: 2px 6px; }}
#NewTopicBtn {{
    background: transparent; border: 1px dashed {C['line']};
    border-radius: 8px; color: {C['muted']}; padding: 7px 10px;
}}
#NewTopicBtn:hover {{ border-color: {C['ink']}; color: {C['ink']}; background: {C['card']}; }}

QListWidget#TopicList, QListWidget#NavList {{
    background: transparent; border: none;
}}
QListWidget#TopicList::item, QListWidget#NavList::item {{
    border-radius: 8px; padding: 7px 8px; margin: 1px 4px;
}}
QListWidget#TopicList::item:selected, QListWidget#NavList::item:selected {{
    background: #e9e9e9; color: {C['ink']};
}}
QListWidget#TopicList::item:hover, QListWidget#NavList::item:hover {{
    background: {C['card']};
}}

/* ---------- 中栏 ---------- */
#ListPane {{ background: {C['paper']}; border-right: 1px solid {C['line']}; }}
#ListHeader {{ font-size: {int(15 * s)}px; font-weight: 600; color: {C['ink']}; }}
#CountLabel {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#Search {{
    background: {C['card']}; border: 1px solid {C['line']}; border-radius: 9px;
    padding: 8px 12px; selection-background-color: {C['ink']}; selection-color: #fff;
}}
QLineEdit#Search:focus {{ border-color: {C['ink']}; }}

QListWidget#NoteList {{ background: transparent; border: none; padding: 2px; }}
QListWidget#NoteList::item {{ border: none; margin: 0px; }}

QPushButton#NewNoteBtn {{
    background: {C['ink']}; color: #ffffff; border: none; border-radius: 9px;
    padding: 9px 14px; font-weight: 600;
}}
QPushButton#NewNoteBtn:hover {{ background: #000000; }}

/* ---------- 编辑区 ---------- */
#EditorPane {{ background: {C['card']}; }}
#EditorTopBar {{ background: {C['card']}; border-bottom: 1px solid {C['line_soft']}; }}
#TypeBadge {{
    color: {C['ink_soft']}; background: #f0f0f0;
    border-radius: 6px; padding: 2px 8px; font-size: {int(11 * s)}px; font-weight: 600;
}}
#SaveState {{ color: {C['faint']}; font-size: {int(11 * s)}px; }}

QLineEdit#NoteTitle {{
    background: transparent; border: none; padding: 2px 0;
    font-family: {FONT_TEXT}; font-size: {int(22 * s)}px; font-weight: 600; color: {C['ink']};
}}
QLineEdit#NoteTitle::placeholder {{ color: {C['faint']}; }}

QPlainTextEdit#Editor {{
    background: {C['card']}; border: none; padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: #d6d6d6; selection-color: {C['ink']};
}}
QTextBrowser#Preview {{
    background: {C['card']}; border: none; padding: 18px 26px;
    font-family: {FONT_TEXT}; font-size: {int(15 * s)}px; color: {C['ink']};
    selection-background-color: #d6d6d6;
}}

QToolButton {{
    background: transparent; border: none; border-radius: 7px; padding: 5px 7px; color: {C['ink_soft']};
}}
QToolButton:hover {{ background: #f0f0f0; color: {C['ink']}; }}
QToolButton:checked {{ background: #e4e4e4; color: {C['ink']}; }}
QToolButton:pressed {{ background: {C['line']}; }}

/* ---------- 通用按钮 ---------- */
QPushButton {{
    background: {C['card']}; border: 1px solid {C['line']}; border-radius: 8px;
    padding: 7px 14px; color: {C['ink']};
}}
QPushButton:hover {{ border-color: {C['ink']}; }}
QPushButton:default {{ background: {C['ink']}; color: white; border: none; }}
QPushButton:default:hover {{ background: #000000; }}
QPushButton:disabled {{ color: {C['faint']}; border-color: {C['line_soft']}; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #d2d2d2; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #b6b6b6; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #d2d2d2; border-radius: 5px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ---------- 菜单 ---------- */
QMenu {{
    background: {C['card']}; border: 1px solid {C['line']}; border-radius: 9px; padding: 5px;
}}
QMenu::item {{ padding: 6px 26px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: #efefef; color: {C['ink']}; }}
QMenu::separator {{ height: 1px; background: {C['line_soft']}; margin: 4px 8px; }}

QToolTip {{
    background: {C['ink']}; color: #fff; border: none; padding: 5px 8px; border-radius: 6px;
}}

/* ---------- 对话框 ---------- */
QDialog {{ background: {C['paper']}; }}
QDialog QLabel {{ color: {C['ink']}; }}
QComboBox {{
    background: {C['card']}; border: 1px solid {C['line']}; border-radius: 8px; padding: 6px 10px;
}}
QComboBox:focus {{ border-color: {C['ink']}; }}
QComboBox QAbstractItemView {{
    background: {C['card']}; border: 1px solid {C['line']}; selection-background-color: #efefef;
    selection-color: {C['ink']}; outline: none;
}}
QSpinBox {{
    background: {C['card']}; border: 1px solid {C['line']}; border-radius: 8px; padding: 5px 8px;
}}
QCheckBox {{ spacing: 8px; }}
QSplitter::handle {{ background: {C['line_soft']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
"""
