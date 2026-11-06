"""应用锁：密码哈希、校验与对话框。"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from PyQt5.QtWidgets import QApplication

from timodesk.settings import Settings
from timodesk.store import Library
from timodesk.ui.dialogs import LockDialog, UnlockDialog
from timodesk.ui.theme import app_qss

app = QApplication(sys.argv)
app.setStyleSheet(app_qss())
root = Path("worklib_lock")
lib = Library(root).load()
if not lib.topics:
    t = lib.add_topic("锁测试")
    lib.add_note(t.id, "note", content="内容")
    lib.save()

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += 1 if cond else 0
    print(("  PASS " if cond else "  FAIL ") + name)


st = Settings(root)
st.clear_password()

# 1. 默认无锁
check("默认无应用锁", not st.lock_enabled())
check("无锁时任意密码通过", st.check_password("whatever"))

# 2. 设置密码
st.set_password("timo1234")
check("已开启", st.lock_enabled())
check("settings.json 已落盘", (root / "settings.json").exists())
check("正确密码通过", st.check_password("timo1234"))
check("错误密码拒绝", not st.check_password("timo12345"))
check("空密码拒绝", not st.check_password(""))

# 3. 重新加载后仍有效
st2 = Settings(root)
check("重载后仍验证", st2.check_password("timo1234"))

# 4. 密码不落明文
raw = (root / "settings.json").read_text(encoding="utf-8")
check("文件不含明文密码", "timo1234" not in raw)
check("文件含 salt/hash", "salt" in raw and "hash" in raw)

# 5. 解锁对话框
u = UnlockDialog(None, st2)
u.pwd.setText("bad")
u._try()
check("错误密码不进", u.result() != u.Accepted)
u.pwd.setText("timo1234")
u._try()
check("正确密码解锁", u.result() == u.Accepted)

# 6. 设置对话框：新密码太短
d = LockDialog(None, Settings(root))
d.cur.setText("timo1234")
d.new.setText("12")
d.new2.setText("12")
d._save()
check("短密码被拒", not d.changed and d.result() != d.Accepted)

# 7. 两次不一致
d.new.setText("abcd1234")
d.new2.setText("abcd9999")
d._save()
check("两次不一致被拒", not d.changed)

# 8. 修改成功
d.new.setText("abcd1234")
d.new2.setText("abcd1234")
d._save()
check("修改成功", d.changed and Settings(root).check_password("abcd1234"))

# 9. 关闭应用锁需要正确当前密码
st = Settings(root)
d2 = LockDialog(None, st)
d2.cur.setText("wrong")
d2._turn_off()
check("密码错误不能关闭", st.lock_enabled())
d2.cur.setText("abcd1234")
d2._turn_off()
check("密码正确可关闭", not st.lock_enabled())

print(f"\n{ok}/{total} PASS")
sys.exit(0 if ok == total else 1)
