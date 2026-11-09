"""启动便携目录里的 exe，确认窗口出现、Data 目录写盘，然后结束进程。"""
import subprocess
import sys
import time
from ctypes import WINFUNCTYPE, windll, wintypes
from pathlib import Path

TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else
              Path(__file__).resolve().parents[1] / "dist" / "Timo For Windows")
EXE = TARGET / "Timo For Windows.exe"

proc = subprocess.Popen([str(EXE)], cwd=str(TARGET))
print("pid", proc.pid)

user32 = windll.user32
titles = []


def cb(hwnd, _):
    if not user32.IsWindowVisible(hwnd):
        return True
    n = user32.GetWindowTextLengthW(hwnd)
    if n:
        buf = wintypes.LPWSTR()
        buf = (wintypes.WCHAR * (n + 2))()
        user32.GetWindowTextW(hwnd, buf, n + 2)
        titles.append((hwnd, buf.value))
    return True


CB = WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb)
for i in range(30):
    time.sleep(1)
    titles.clear()
    user32.EnumWindows(CB, 0)
    hits = [t for t in titles if t[1].strip() in ("Timo For Windows", "欢迎使用 Timo 桌面版")]
    if hits:
        print(f"{i + 1}s 找到窗口:", hits)
        break
else:
    print("没找到窗口")

time.sleep(1.5)
print("Data 内容:", [p.name for p in (TARGET / "Data").iterdir()])
subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
time.sleep(1)
print("进程已结束")
