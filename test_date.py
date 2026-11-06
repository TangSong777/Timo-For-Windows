"""「日子」笔记的倒数文案。"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")
from timodesk.store import date_countdown

ok = 0
total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


today = date(2026, 11, 7)
check("未来固定日期", date_countdown({"type": 0, "year": 2027, "month": 11, "dayOfMonth": 7}, today) == "还有 365 天")
check("过去固定日期", date_countdown({"type": 0, "year": 2020, "month": 1, "dayOfMonth": 1}, today) == f"已过去 {(today - date(2020, 1, 1)).days} 天")
check("就是今天", date_countdown({"type": 0, "year": 2026, "month": 11, "dayOfMonth": 7}, today) == "就是今天")
check("每年重复：今年未到", date_countdown({"type": 1, "month": 12, "dayOfMonth": 25}, today) == "还有 48 天")
check("每年重复：今年已过，顺延明年", date_countdown({"type": 1, "month": 1, "dayOfMonth": 1}, today) == "还有 55 天")
check("每年重复：正好今天", date_countdown({"type": 1, "month": 11, "dayOfMonth": 7}, today) == "就是今天")
check("2 月 29 日不崩", isinstance(date_countdown({"type": 1, "month": 2, "dayOfMonth": 29}, date(2026, 3, 1)), str))
check("月份非法返回空", date_countdown({"type": 0, "year": 2026, "month": 13, "dayOfMonth": 1}, today) == "")
check("缺失字段返回空", date_countdown({}, today) == "")
check("非 dict 返回空", date_countdown(None, today) == "")
check("兼容旧键 day", date_countdown({"type": 0, "year": 2026, "month": 11, "day": 8}, today) == "还有 1 天")

# 卡片文案带上倒数
from timodesk.ui.widgets import _date_text
txt = _date_text({"type": 0, "year": 2027, "month": 1, "dayOfMonth": 1, "isLunar": False})
check("卡片带倒数", "还有" in txt or "已过去" in txt)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
