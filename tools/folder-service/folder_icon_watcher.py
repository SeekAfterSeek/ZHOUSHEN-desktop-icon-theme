# -*- coding: utf-8 -*-
r"""新建文件夹图标自动补全服务（独立运行）

由 install_folder_service.py 启动，常驻后台：
  监控 桌面/文档/下载/图片，发现新目录立即写入 desktop.ini。
"""
import os
import time
import ctypes

FOLDER_ICO = os.path.join(r"C:\Users\Lenovo\zsIcons", "sys_folder.ico")
k32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

INIT = "[.ShellClassInfo]\r\nIconResource=" + FOLDER_ICO + ",0\r\n"


def set_icon(folder):
    if not os.path.isdir(folder):
        return False
    ini = os.path.join(folder, "desktop.ini")
    try:
        k32.SetFileAttributesW(folder, 0x80)
        if os.path.exists(ini):
            k32.SetFileAttributesW(ini, 0x80)
        with open(ini, "w", encoding="utf-16") as f:
            f.write(INIT)
        k32.SetFileAttributesW(ini, 0x06)      # HIDDEN | SYSTEM
        k32.SetFileAttributesW(folder, 0x01)   # READONLY
        shell32.SHChangeNotify(0x00002000, 0x0005,
                               ctypes.c_wchar_p(folder), None)
        return True
    except Exception:
        return False


def main():
    HOME = os.path.expanduser("~")
    watch = [os.path.join(HOME, d) for d in
             ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music")]
    watch.append(r"D:\Desktop")
    watch = [w for w in watch if os.path.isdir(w)]
    known = set()
    # 首轮扫描
    for root in watch:
        try:
            for f in os.listdir(root):
                p = os.path.join(root, f)
                if os.path.isdir(p):
                    known.add(p)
                    if not os.path.exists(os.path.join(p, "desktop.ini")):
                        set_icon(p)
        except Exception:
            pass

    while True:
        for root in watch:
            try:
                for f in os.listdir(root):
                    p = os.path.join(root, f)
                    if os.path.isdir(p) and p not in known:
                        known.add(p)
                        set_icon(p)
            except Exception:
                pass
        time.sleep(2)


if __name__ == "__main__":
    main()
