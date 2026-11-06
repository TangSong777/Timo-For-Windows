"""Timo 桌面版启动入口（双击 exe / 命令行 python run.py）。"""
import sys

from timodesk.app import run

if __name__ == "__main__":
    sys.exit(run())
