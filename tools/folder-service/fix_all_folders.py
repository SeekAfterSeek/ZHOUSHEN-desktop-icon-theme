# -*- coding: utf-8 -*-
r"""全局文件夹图标（对所有文件夹生效，含新建）

原理：Explorer 读 HKCU\...\Explorer\Shell Icons\<n> 作为图标覆盖。
  3  = 文件夹（关闭）
  4  = 文件夹（打开）
另外清掉指向不存在文件的历史键值。
"""
import sys
import io
import os
import time
import ctypes
import subprocess
import winreg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ICO = os.path.join(r"C:\Users\Lenovo\zsIcons", "sys_folder.ico")
SHELL_ICONS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons"


def ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return ((r.stdout or "") + (r.stderr or "")).strip()


def main():
    if not os.path.exists(ICO):
        print("✗ 缺少 sys_folder.ico")
        return
    print("图标:", ICO, os.path.getsize(ICO), "字节")

    # 1. 清理指向不存在文件的键值
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SHELL_ICONS, 0,
                        winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
        names = []
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(k, i)
            except OSError:
                break
            names.append(name)
            i += 1
            if isinstance(val, str) and val.lower().endswith(".ico"):
                target = val.split(",")[0].strip().strip('"')
                if not os.path.exists(target):
                    try:
                        winreg.DeleteValue(k, name)
                        print("  清理失效键值 %s -> %s" % (name, val))
                    except Exception as e:
                        print("  删除失败", name, e)
        print("  现有键:", names)

    # 2. 设置文件夹图标
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, SHELL_ICONS, 0,
                            winreg.KEY_SET_VALUE) as k:
        for n in (3, 4):
            winreg.SetValueEx(k, str(n), 0, winreg.REG_SZ, ICO + ",0")
            print("  设置 Shell Icons\\%d = %s" % (n, ICO))

    # 3. 同时写 Classes（双保险）
    for sub in (r"Software\Classes\Folder\DefaultIcon",
                r"Software\Classes\Directory\DefaultIcon"):
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, sub, 0,
                                winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ICO + ",0")
        print("  设置", sub)

    # 4. 刷新
    sh = ctypes.windll.shell32
    sh.SHChangeNotify(0x08000000, 0x0000, None, None)
    ps("ie4uinit.exe -show")
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], capture_output=True)
    time.sleep(3)
    cd = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                      r"Microsoft\Windows\Explorer")
    for x in os.listdir(cd):
        if x.lower().startswith(("iconcache", "thumbcache")) and x.lower().endswith(".db"):
            try:
                os.remove(os.path.join(cd, x))
            except Exception:
                pass
    subprocess.Popen(["explorer.exe"])
    time.sleep(14)
    print("explorer 已重启")


if __name__ == "__main__":
    main()
