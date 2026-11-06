"""Markdown 渲染：把笔记正文转成预览用的 HTML。

Timo 只支持「简单 Markdown」，这里按便签的阅读习惯放宽一点：
换行即断行（nl2br），支持标题、粗斜体、列表、待办、引用、代码、表格、图片和链接。
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import markdown

TASK_RE = re.compile(r"^(\s*(?:[-*+]|\d+\.)\s+)\[([ xX])\]\s+", re.M)
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")


def _render_tasks(text: str) -> str:
    """把 - [ ] / - [x] 变成可点击的方框（点击回写原文，和手机上的待办一样）。

    便签里经常是「标题」下一行直接接列表，Markdown 默认认不出来，
    这里顺手补一个空行。行号始终按原文计算，点击方框才能回到正确的行。
    """
    lines = text.split("\n")
    out = []
    for lineno, line in enumerate(lines):
        m = TASK_RE.match(line)
        if m:
            box = "☑" if m.group(2).lower() == "x" else "☐"
            item = f'{m.group(1)}<a class="todo" href="todo:{lineno}">{box}</a> {line[m.end():]}'
        else:
            item = line
        if (
            LIST_RE.match(item)
            and lineno > 0
            and lines[lineno - 1].strip()
            and not LIST_RE.match(lines[lineno - 1])
        ):
            out.append("")
        out.append(item)
    return "\n".join(out)


def _abs_images(html_text: str, root: Path) -> str:
    """把 attachments/xxx 的相对图片路径换成绝对 file:// URI，保证预览能显示。"""

    def repl(m: re.Match) -> str:
        src = m.group(1)
        if re.match(r"^(https?:|file:|data:|qrc:)", src):
            return m.group(0)
        p = (root / src).resolve()
        try:
            uri = p.as_uri()
        except ValueError:
            return m.group(0)
        return f'src="{uri}"'

    return re.sub(r'src="([^"]+)"', repl, html_text)


def _css() -> str:
    """预览用的内联样式，颜色跟随当前皮肤（浅色 / 深色）。"""
    from .ui.theme import C

    return f"""
body {{ color:{C['ink']}; font-family:"Microsoft YaHei","Segoe UI",sans-serif; font-size:15px;
       line-height:1.85; margin:0; }}
h1 {{ font-size:24px; font-weight:600; margin:22px 0 10px; }}
h2 {{ font-size:19px; font-weight:600; margin:18px 0 8px; }}
h3 {{ font-size:16px; font-weight:600; margin:14px 0 6px; color:{C['ink_soft']}; }}
p {{ margin: 8px 0; }}
a {{ color:{C['ink']}; text-decoration:underline; text-decoration-color:{C['faint']}; }}
a.todo {{ text-decoration:none; }}
li {{ margin:4px 0; }}
blockquote {{ margin:10px 0; padding:6px 14px; border-left:3px solid {C['card_border_strong']};
             color:{C['muted']}; background:{C['paper_alt']}; border-radius:0 8px 8px 0; }}
code {{ background:{C['hover_bg']}; padding:1px 5px; border-radius:4px;
       font-family:"Cascadia Code",Consolas,monospace; font-size:13px; color:{C['ink_soft']}; }}
pre {{ background:{C['paper_alt']}; padding:12px 14px; border-radius:8px; border:1px solid {C['card_border']}; }}
pre code {{ background:transparent; padding:0; }}
ul, ol {{ margin:8px 0; padding-left:24px; }}
hr {{ border:none; border-top:1px solid {C['card_border']}; margin:18px 0; }}
img {{ max-width:100%; border-radius:8px; margin:6px 0; }}
table {{ border-collapse:collapse; margin:10px 0; }}
th, td {{ border:1px solid {C['card_border']}; padding:6px 10px; }}
th {{ background:{C['hover_bg']}; font-weight:600; }}
.empty {{ color:{C['faint']}; }}
"""


def render(text: str, root: str | Path, empty_hint: str = "开始写点什么……") -> str:
    body = text or ""
    if not body.strip():
        return f'<html><head><style>{_css()}</style></head><body><p class="empty">{html.escape(empty_hint)}</p></body></html>'
    body = _render_tasks(body)
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
        output_format="html5",
    )
    inner = md.convert(body)
    inner = _abs_images(inner, Path(root))
    return f"<html><head><meta charset='utf-8'><style>{_css()}</style></head><body>{inner}</body></html>"
