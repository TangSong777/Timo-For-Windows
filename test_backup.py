"""备份模块：创建、到期判断、保留份数、恢复。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk import backup
from timodesk.store import Library

app = QApplication(sys.argv)
root = Path("worklib_backup")
import shutil
shutil.rmtree(root, ignore_errors=True)
lib = Library(root).load()
t = lib.add_topic("备份测试")
n = lib.add_note(t.id, "note", content="第一版内容")
lib.save()

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


# 1. 从未备份 → 到期
check("首次判断为到期", backup.due(lib))

# 2. 创建备份
p = backup.create(lib)
check("备份文件存在", p.exists())
check("备份在 backup 目录", p.parent.name == "backup")
check("zip 里有 library.json", "library.json" in __import__("zipfile").ZipFile(p).namelist())
check("zip 里有笔记正文", f"notes/{n.id}.md" in __import__("zipfile").ZipFile(p).namelist())

# 3. 刚备份 → 不到期
check("刚备份不到期", not backup.due(lib))

# 4. 列出来
items = backup.list_all(root)
check("列表 1 份", len(items) == 1)
check("列表含路径与时间", items[0]["path"] == p and items[0]["size"] > 0)

# 5. 改内容后恢复
lib.set_content(n.id, "改坏的内容")
lib.save()
check("改动已生效", lib.content(n.id) == "改坏的内容")
backup.restore(lib, p)
check("恢复后正文回滚", lib.content(n.id) == "第一版内容")
check("恢复前留了现场备份", len(backup.list_all(root)) >= 2)

# 6. 恢复后库仍可用
check("笔记仍在", n.id in lib.notes)
check("主题仍在", t.id in lib.topics)

# 7. 保留份数
for i in range(9):
    backup.create(lib, stamp=f"2020010{i % 9 + 1}-1200{i:02d}")
check("只保留 7 份", len(backup.list_all(root)) == 7)

# 8. 不含附件
att = lib.root / "attachments"
att.mkdir(exist_ok=True)
(att / "x.jpg").write_bytes(b"fake")
p2 = backup.create(lib, stamp="20301231-235959")
names = __import__("zipfile").ZipFile(p2).namelist()
check("备份不含附件", not any("attachments" in x for x in names))

# 9. 清空新加的
print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
