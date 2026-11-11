# -*- coding: utf-8 -*-
r"""安装新建文件夹图标监控（开机自启）"""
import sys
import io
import os
import subprocess
import winreg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
WATCHER = os.path.join(ROOT, "folder_icon_watcher.py")

PY_CANDIDATES = [
    r"C:\Users\Lenovo\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\pythonw.exe",
    r"C:\Users\Lenovo\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe",
]


def main():
    pyw = None
    for p in PY_CANDIDATES:
        if os.path.exists(p):
            pyw = p
            break
    if not pyw:
        print("✗ 找不到 pythonw.exe")
        return
    print("python:", pyw)
    print("watcher:", WATCHER, os.path.exists(WATCHER))

    # 开机自启
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    cmd = '"%s" "%s"' % (pyw, WATCHER)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "ZsFolderIcons", 0, winreg.REG_SZ, cmd)
    print("已写入开机自启: ZsFolderIcons")

    # 立即启动
    subprocess.Popen([pyw, WATCHER], creationflags=0x00000008,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("监控进程已启动（后台）")

    # 立即补一次现有文件夹
    sys.path.insert(0, ROOT)
    import folder_icon_watcher as W
    n = 0
    for root in (r"D:\Desktop", os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
                 os.path.expanduser("~/Documents"), os.path.expanduser("~/Downloads"),
                 os.path.expanduser("~/Pictures")):
        if not os.path.isdir(root):
            continue
        for f in os.listdir(root):
            p = os.path.join(root, f)
            if os.path.isdir(p) and not os.path.exists(os.path.join(p, "desktop.ini")):
                if W.set_icon(p):
                    n += 1
    print("补全 %d 个文件夹" % n)


if __name__ == "__main__":
    main()
