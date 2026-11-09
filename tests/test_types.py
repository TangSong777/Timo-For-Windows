"""六种笔记类型的功能一致性测试：新建 → 填字段 → 保存 → 导出 → 重导入 → 逐字段比对。"""
import shutil
import sys
import zipfile
from pathlib import Path

from timodesk.exporter import export_zip
from timodesk.importer import import_export
from timodesk.store import Library

ROOT = Path("_types_tmp")
ok = 0
fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"PASS {name}")
    else:
        fail += 1
        print(f"FAIL {name} {detail}")


def main():
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir()

    lib = Library(ROOT / "lib").load()
    topic = lib.add_topic("测试主题")
    other = lib.add_topic("另一个主题")

    # 找一个真实图片做附件
    src_img = next(Path("testlib/attachments").glob("*")) if Path("testlib/attachments").exists() else None

    # ---- 1. 便签 ----
    n1 = lib.add_note(topic.id, "note", "便签正文第一行\n第二行 **加粗**", None)
    lib.toggle_pin(n1.id)
    lib.toggle_color(n1.id, "#d4d4d4")

    # ---- 2. 文章 ----
    n2 = lib.add_note(topic.id, "article", "# 文章标题\n\n正文内容。", "文章标题")

    # ---- 3. 图库 ----
    n3 = lib.add_note(topic.id, "gallery", "", None)
    if src_img:
        rel = lib.import_attachment(src_img)
        n3.images = [rel]
    n3.description = "图库说明文字"

    # ---- 4. 链接 ----
    n4 = lib.add_note(topic.id, "link", "链接描述", "示例站点")
    n4.url = "https://example.com/page"

    # ---- 5. 日子 ----
    n5 = lib.add_note(topic.id, "date", "这一天要做点什么", "生日")
    n5.date = {"year": 2026, "month": 3, "dayOfMonth": 15, "dayOfWeek": -1, "type": 1, "isLunar": False}

    # ---- 6. 账号 ----
    n6 = lib.add_note(topic.id, "account", "", "某个网站")
    n6.account = "user@example.com"
    n6.password = "S3cret!密码"
    n6.remark = "备注内容"

    lib.save()
    print(f"built {len(lib.notes)} notes")

    # ---- 重载后确认 ----
    lib2 = Library(ROOT / "lib").load()
    check("六条都在", len(lib2.notes) == 6, len(lib2.notes))
    check("便签正文", lib2.content(n1.id) == "便签正文第一行\n第二行 **加粗**", lib2.content(n1.id))
    check("便签置顶", bool(lib2.notes[n1.id].pinned_at))
    check("便签颜色", lib2.notes[n1.id].color == "#d4d4d4")
    check("文章标题", lib2.notes[n2.id].title == "文章标题")
    check("图库图片", lib2.notes[n3.id].images == n3.images, lib2.notes[n3.id].images)
    check("图库说明", lib2.notes[n3.id].description == "图库说明文字")
    check("链接 URL", lib2.notes[n4.id].url == "https://example.com/page")
    check("日子", lib2.notes[n5.id].date == n5.date, lib2.notes[n5.id].date)
    check("账号", lib2.notes[n6.id].account == "user@example.com")
    check("密码", lib2.notes[n6.id].password == "S3cret!密码")
    check("备注", lib2.notes[n6.id].remark == "备注内容")

    # ---- 导出 ----
    zp, counts = export_zip(lib2, ROOT / "out.zip")
    print("export counts:", counts)
    z = zipfile.ZipFile(zp)
    names = z.namelist()
    check("导出含 manifest", "manifest.json" in names)
    check("导出含 topics", "data/topics.json" in names)
    check("导出含 documents", "data/documents.json" in names)
    check("导出含 accounts.csv", "content/accounts.csv" in names)
    check("导出主题数", counts["topics"] == 2, counts["topics"])
    check("导出文档数", counts["documents"] == 6, counts["documents"])
    check("导出账号数", counts.get("accounts") == 1, counts.get("accounts"))

    # ---- 重导入 ----
    lib3 = Library(ROOT / "lib3").load()
    report = import_export(zp, lib3)
    print("import:", report)
    check("导入文档数", len(lib3.notes) == 6, len(lib3.notes))
    by_type = {}
    for n in lib3.notes.values():
        by_type.setdefault(n.type, []).append(n)
    check("类型齐 6 种", set(by_type) == {"note", "article", "gallery", "link", "date", "account"}, set(by_type))

    r1 = by_type["note"][0]
    check("回环便签正文", lib3.content(r1.id) == "便签正文第一行\n第二行 **加粗**")
    r2 = by_type["article"][0]
    check("回环文章标题", r2.title == "文章标题")
    check("回环文章正文不含重复标题", lib3.content(r2.id).strip().startswith("正文内容") or not lib3.content(r2.id).startswith("# 文章标题"))
    r3 = by_type["gallery"][0]
    check("回环图库图片", len(r3.images) == 1, r3.images)
    check("回环图库说明", r3.description == "图库说明文字")
    r4 = by_type["link"][0]
    check("回环链接 URL", r4.url == "https://example.com/page")
    r5 = by_type["date"][0]
    check("回环日子", r5.date == n5.date, r5.date)
    r6 = by_type["account"][0]
    check("回环账号", r6.account == "user@example.com")
    check("回环密码", r6.password == "S3cret!密码", r6.password)
    check("回环备注", r6.remark == "备注内容")

    # 跨主题
    lib3.move_note(r1.id, other.id)
    check("换主题", lib3.notes[r1.id].topic_id == other.id)

    print(f"\ntotal: {ok} / {ok + fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
