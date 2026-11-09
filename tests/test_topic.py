"""删除主题 / 恢复笔记 / 未分类兜底 的一致性。"""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timodesk.store import Library

ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1; print("PASS", name)
    else:
        fail += 1; print("FAIL", name, extra)

def main():
    root = tempfile.mkdtemp(prefix="timo-topic-")
    try:
        lib = Library(root); lib.load()
        t = lib.add_topic("临时主题")
        n1 = lib.add_note(t.id, "note", content="A")
        n2 = lib.add_note(t.id, "note", content="B")
        other = lib.add_topic("保留主题")
        n3 = lib.add_note(other.id, "note", content="C")
        lib.save()

        lib.delete_topic(t.id)
        lib.save()
        check("主题已进回收站", lib.topics[t.id].state == "trash")
        check("主题内笔记一起进回收站",
              lib.notes[n1.id].state == "trash" and lib.notes[n2.id].state == "trash",
              f"{lib.notes[n1.id].state}/{lib.notes[n2.id].state}")
        check("别的主题不受影响", lib.notes[n3.id].state == "active")

        lib.restore_note(n1.id)
        lib.save()
        check("恢复后状态 active", lib.notes[n1.id].state == "active")
        inbox = lib.topics.get(lib.notes[n1.id].topic_id)
        check("孤儿笔记落到未分类", inbox is not None and inbox.name == "（未分类）",
              inbox.name if inbox else "None")
        check("未分类主题只有一个", len([x for x in lib.topics.values() if x.name == "（未分类）"]) == 1)

        lib.restore_note(n2.id)
        check("第二条也落到同一个未分类",
              lib.notes[n2.id].topic_id == lib.notes[n1.id].topic_id)

        # 重载后依然一致
        lib2 = Library(root); lib2.load()
        check("重载后一致", lib2.notes[n1.id].topic_id == lib.notes[n1.id].topic_id)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"\ntotal: {ok} / {ok + fail}")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
