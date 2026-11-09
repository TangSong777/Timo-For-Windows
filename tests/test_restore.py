"""导入中断后的回滚。"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.exporter import export_zip
from timodesk.importer import import_export
from timodesk.store import Library
from timodesk.ui.main_window import ImportCanceled, MainWindow
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())

for d in ("worklib_rs_a", "worklib_rs_b"):
    shutil.rmtree(d, ignore_errors=True)

a = Library("worklib_rs_a").load()
t = a.add_topic("源")
for i in range(30):
    a.add_note(t.id, "note", content=f"第 {i} 条")
a.save()
zp, _ = export_zip(a, "worklib_rs_a/out.zip")

lib = Library("worklib_rs_b").load()
t2 = lib.add_topic("我的")
for i in range(5):
    lib.add_note(t2.id, "note", content=f"本地 {i}")
lib.save()

win = MainWindow(lib)
ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


before = set(lib.notes)
check("本地 5 条", len(before) == 5)

# 1. 备份
bdir = win._backup_current()
check("备份目录存在", bdir is not None and bdir.exists())
check("备份含 library.json", (bdir / "library.json").exists())

# 2. 模拟中途取消：前 10 条后抛异常
def cancel_after_ten(done, total):
    if done >= 10:
        raise ImportCanceled()


canceled = False
try:
    import_export(zp, lib, progress=cancel_after_ten, mode="replace")
except ImportCanceled:
    canceled = True
check("中途取消抛出", canceled)

# 3. 此时库已被清空/部分写入
check("库已被改动", len(lib.notes) != 5)

# 4. 回滚
restored = win._restore_from_backup(bdir)
check("回滚成功", restored)
check("笔记数量恢复", len(lib.notes) == 5)
check("主题恢复", len(lib.topics) == 1)
check("正文恢复", any(lib.content(n.id) == "本地 0" for n in lib.notes.values()))
check("界面列表恢复", win.note_list.count() == 5)

# 5. 没有备份时不崩
check("无备份返回 False", win._restore_from_backup(None) is False)

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
