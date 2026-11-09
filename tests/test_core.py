"""核心功能自动化测试：新建 / 编辑 / 搜索 / 删除 / 归档 / 导出导入。"""
import shutil
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from timodesk.store import Library
from timodesk.ui.main_window import MainWindow

app = QApplication([])

shutil.rmtree("worklib", ignore_errors=True)
shutil.copytree("testlib", "worklib")
lib = Library("worklib").load()
w = MainWindow(lib)
w.resize(1280, 830)
w.show()

ok = []

# 1) 新建笔记并写入正文
w.view = ("all", None)
w._reload_notes()
n0 = len(lib.notes)
w.new_note()
app.processEvents()
note = w.editor.note
assert note is not None and len(lib.notes) == n0 + 1
w.editor.edit.setPlainText("桌面版写入的第一条笔记\n\n- [ ] 待办一项\n支持 **Markdown**")
w.editor._emit()
w.save_now()
txt = (Path("worklib/notes") / f"{note.id}.md").read_text(encoding="utf-8")
ok.append(("新建+保存", "第一条笔记" in txt and "[ ] 待办一项" in txt))
ok.append(("正文长度", len(lib.content(note.id)) > 20))

# 2) 搜索
found = lib.search("桌面版写入")
ok.append(("搜索命中新建笔记", any(n.id == note.id for n in found)))
found2 = lib.search("奖学金")
ok.append(("搜索已有数据", len(found2) >= 1))

# 3) 置顶 / 颜色
lib.toggle_pin(note.id)
lib.toggle_color(note.id, "#ffe0b2")
note2 = lib.notes[note.id]
ok.append(("置顶+颜色", bool(note2.pinned_at) and note2.color == "#ffe0b2"))
top = [n.id for n in lib.sorted_notes(state="active")][:1]
ok.append(("置顶排在最前", top == [note.id]))

# 4) 归档 / 恢复
lib.archive_note(note.id, True)
ok.append(("归档", lib.notes[note.id].state == "archived"))
lib.archive_note(note.id, False)
ok.append(("取消归档", lib.notes[note.id].state == "active"))

# 5) 删除到回收站 → 恢复
lib.delete_note(note.id)
ok.append(("删除到回收站", lib.notes[note.id].state == "trash"))
lib.restore_note(note.id)
ok.append(("恢复", lib.notes[note.id].state == "active"))

# 6) 新建主题 + 移动笔记
t = lib.add_topic("测试主题")
lib.move_note(note.id, t.id)
ok.append(("换主题", lib.notes[note.id].topic_id == t.id))
lib.save()

# 7) 往返导出导入
from timodesk.exporter import export_zip
from timodesk.importer import import_export

path, counts = export_zip(lib, "worklib_export.zip")
shutil.rmtree("worklib2", ignore_errors=True)
lib2 = Library("worklib2").load()
rep = import_export(path, lib2)
ok.append(("导出导入数量", rep.notes == len(lib.notes) and rep.topics == len(lib.topics)))
same = sum(1 for nid in lib.notes if lib.content(nid).strip() == lib2.content(nid).strip())
ok.append(("正文一致", same == len(lib.notes)))

for name, passed in ok:
    print(("PASS" if passed else "FAIL"), name)
print("total:", sum(1 for _, p in ok if p), "/", len(ok))
