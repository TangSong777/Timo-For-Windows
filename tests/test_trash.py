"""回收站自动清理：超过 N 天的笔记在启动时彻底删除。"""
import shutil
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")
from timodesk.store import Library, to_iso

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


shutil.rmtree("worklib_trash", ignore_errors=True)
lib = Library("worklib_trash").load()
t = lib.add_topic("杂")
old = lib.add_note(t.id, "note", content="x")
new = lib.add_note(t.id, "note", content="x")
lib.set_content(old.id, "很久以前删的")
lib.set_content(new.id, "刚删的")
lib.save()

lib.delete_note(old.id)
lib.delete_note(new.id)
# 手动把 old 的 deleted_at 改成 40 天前
lib.notes[old.id].deleted_at = to_iso(datetime.now(timezone.utc) - timedelta(days=40))
lib.save()

n = lib.purge_trash(30)
check("清理了一条", n == 1)
check("老的没了", old.id not in lib.notes)
check("新的还在", new.id in lib.notes and lib.notes[new.id].state == "trash")
check("文件也删了", not (lib.root / "notes" / f"{old.id}.md").exists())

# 关掉清理
lib2 = Library("worklib_trash").load()
check("重载后仍是 1 条", len([x for x in lib2.notes.values() if x.state == "trash"]) == 1)
check("days=0 不清理", lib2.purge_trash(0) == 0)

# 所有笔记都在回收站且过期
lib2.delete_note(new.id)
lib2.notes[new.id].deleted_at = to_iso(datetime.now(timezone.utc) - timedelta(days=90))
lib2.save()
check("全部过期也能清", lib2.purge_trash(30) == 1)
check("清空后为空", not any(x.state == "trash" for x in lib2.notes.values()))

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
