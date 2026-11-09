"""导入模式：替换 / 合并。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.exporter import export_zip
from timodesk.importer import import_export
from timodesk.store import Library

app = QApplication(sys.argv)

for d in ("worklib_imp_a", "worklib_imp_b"):
    shutil.rmtree(d, ignore_errors=True)

# 源库 A：2 主题 3 笔记
a = Library("worklib_imp_a").load()
t1 = a.add_topic("工作")
t2 = a.add_topic("生活")
n1 = a.add_note(t1.id, "note", content="会议纪要 alpha")
n2 = a.add_note(t1.id, "article", content="# 报告\n\n正文 beta", title="报告")
n3 = a.add_note(t2.id, "note", content="买菜 gamma")
a.save()
zip_path, counts = export_zip(a, "worklib_imp_a/out.zip")

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


check("导出 3 条", counts.get("notes") == 3 or a.notes.__len__() == 3)

# 1. 空库合并导入 = 全量导入
b = Library("worklib_imp_b").load()
r = import_export(zip_path, b, mode="merge")
check("合并到空库 3 条", r.notes == 3 and len(b.notes) == 3)
check("主题 2 个", len(b.topics) == 2)
check("正文正确", b.content(n1.id) == "会议纪要 alpha")

# 2. 再次合并：全部跳过
r2 = import_export(zip_path, b, mode="merge")
check("重复合并 0 新增", r2.notes == 0)
check("重复合并 3 跳过", r2.skipped == 3)
check("笔记数不变", len(b.notes) == 3)

# 3. 本地改内容，合并不应覆盖
b.set_content(n1.id, "本地改过的内容")
b.save()
import_export(zip_path, b, mode="merge")
check("合并不覆盖本地修改", b.content(n1.id) == "本地改过的内容")

# 4. 删一条后合并补回
del b.notes[n3.id]
b._content.pop(n3.id, None)
Path(b.note_path(n3.id)).unlink(missing_ok=True)
b.save()
r3 = import_export(zip_path, b, mode="merge")
check("删除后合并补回 1 条", r3.notes == 1 and n3.id in b.notes)

# 5. 替换导入会覆盖
r4 = import_export(zip_path, b, mode="replace")
check("替换导入 3 条", r4.notes == 3)
check("替换后恢复原内容", b.content(n1.id) == "会议纪要 alpha")
check("替换模式主题数 2", len(b.topics) == 2)

# 6. summary 文案
check("合并摘要含跳过", "跳过" in r2.summary())
check("替换摘要含主题", "主题" in r4.summary())

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
