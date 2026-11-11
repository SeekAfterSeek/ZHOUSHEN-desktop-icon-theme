# -*- coding: utf-8 -*-
r"""统一收尾：把「新建对象」和「系统位置」两类图标全部固定下来

已验证有效的机制：
  ✓ 文件夹（含新建）：desktop.ini + ReadOnly + 后台监控（已装）
  ✓ 快捷方式：IconLocation（已写 26 个）

待补：
  · 回收站/此电脑/控制面板：写入 HKCR（当前用户可写）
  · 运行中应用的底栏图标：需替换 exe 或改 AUMID

本脚本补 HKCR 并做完整验证。
"""
import sys
import io
import os
import time
import ctypes
import subprocess
import winreg
import uuid
from ctypes import wintypes, POINTER

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICO = r"C:\Users\Lenovo\zsIcons"
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"

shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32
u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32

# 系统命名空间 -> ICO
SYS_ICONS = {
    "回收站": ("{645FF040-5081-101B-9F08-00AA002F954E}", "zs_bin_v14.ico"),
    "此电脑": ("{20D04FE0-3AEA-1069-A2D8-08002B30309D}", "zs_pc_v9.ico"),
    "控制面板": ("{26EE0668-A00A-44D7-9371-BEB064C98683}", "zs_panel_v14.ico"),
    "用户文件夹": ("{59031a47-3f72-44a7-89c5-5595fe6b30ee}", "zs_user_v19.ico"),
}


class SHFILEINFO(ctypes.Structure):
    _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]


def grab(path, size=140):
    ole32.CoInitialize(None)
    iid = uuid.UUID("{46EB5926-582E-4017-9FDF-E8998DAA0950}").bytes_le
    h = ctypes.c_void_p()
    shell32.SHGetImageList(4, iid, ctypes.byref(h))
    vt = ctypes.cast(h, POINTER(POINTER(ctypes.c_void_p)))[0]
    GI = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
                            ctypes.c_uint, POINTER(wintypes.HICON))(vt[10])
    fi = SHFILEINFO()
    if not shell32.SHGetFileInfoW(path, 0, ctypes.byref(fi), ctypes.sizeof(fi),
                                  0x4000 | 0x8000):
        return None
    hi = wintypes.HICON()
    if GI(h, fi.iIcon, 1, ctypes.byref(hi)) != 0:
        return None
    hdc = u32.GetDC(0)
    md = g32.CreateCompatibleDC(hdc)
    bm = g32.CreateCompatibleBitmap(hdc, size, size)
    g32.SelectObject(md, bm)
    br = g32.CreateSolidBrush(0x00202020)
    rc = wintypes.RECT(0, 0, size, size)
    u32.FillRect(md, ctypes.byref(rc), br)
    g32.DeleteObject(br)
    u32.DrawIconEx(md, 0, 0, hi, size, size, 0, None, 3)

    class BI(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bi = BI()
    bi.biSize = ctypes.sizeof(BI)
    bi.biWidth = size
    bi.biHeight = -size
    bi.biPlanes = 1
    bi.biBitCount = 32
    bits = ctypes.c_void_p()
    sd = g32.CreateCompatibleDC(hdc)
    dib = g32.CreateDIBSection(sd, ctypes.byref(bi), 0, ctypes.byref(bits), None, 0)
    o2 = g32.SelectObject(sd, dib)
    g32.BitBlt(sd, 0, 0, size, size, md, 0, 0, 0x00CC0020)
    buf = ctypes.string_at(bits, size * size * 4)
    g32.SelectObject(sd, o2)
    g32.DeleteObject(dib)
    g32.DeleteDC(sd)
    g32.DeleteObject(bm)
    g32.DeleteDC(md)
    u32.ReleaseDC(0, hdc)
    u32.DestroyIcon(hi)
    im = Image.frombytes("RGBA", (size, size), buf)
    b_, g_, r_, a_ = im.split()
    return Image.merge("RGBA", (r_, g_, b_, a_))


def write_hkcr():
    """写入 HKCU 下的 Classes 与 Explorer CLSID"""
    for name, (guid, ico) in SYS_ICONS.items():
        p = os.path.join(ICO, ico)
        if not os.path.exists(p):
            print("  ✗ 缺", ico)
            continue
        val = p + ",0"
        # Explorer\CLSID
        k1 = r"Software\Microsoft\Windows\CurrentVersion\Explorer\CLSID\%s\DefaultIcon" % guid
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, k1, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, val)
                if name == "回收站":
                    for v in ("Empty", "Full"):
                        winreg.SetValueEx(k, v, 0, winreg.REG_SZ, val)
            print("  ✓ Explorer\\CLSID", name)
        except Exception as e:
            print("  ✗", name, e)
        # Classes\CLSID
        k2 = r"Software\Classes\CLSID\%s\DefaultIcon" % guid
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, k2, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, val)
                if name == "回收站":
                    for v in ("Empty", "Full"):
                        winreg.SetValueEx(k, v, 0, winreg.REG_SZ, val)
            print("  ✓ Classes\\CLSID", name)
        except Exception as e:
            print("  ✗", name, e)


def main():
    print("=== 写入系统位置图标 ===")
    write_hkcr()

    shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    subprocess.run(["ie4uinit.exe", "-show"], capture_output=True)
    time.sleep(2)

    print("\n=== 验证 ===")
    cases = [
        ("回收站", "::" + "{645FF040-5081-101B-9F08-00AA002F954E}"),
        ("此电脑", "::" + "{20D04FE0-3AEA-1069-A2D8-08002B30309D}"),
        ("控制面板", "::" + "{26EE0668-A00A-44D7-9371-BEB064C98683}"),
        ("用户文件夹", r"C:\Users\Lenovo"),
        ("桌面文件夹", r"D:\Desktop\总文件夹"),
    ]
    rows = []
    for n, p in cases:
        im = grab(p)
        if im:
            rows.append((n, im))
            print("  %-12s ✓" % n)
        else:
            print("  %-12s 取图失败" % n)

    if rows:
        Z = 150
        F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 12)
        sh = Image.new("RGB", (len(rows) * (Z + 10) + 10, Z + 42), (18, 19, 26))
        d = ImageDraw.Draw(sh)
        d.text((10, 5), "系统位置图标", font=ImageFont.truetype(
            r"C:\Windows\Fonts\msyh.ttc", 15), fill=(255, 255, 255))
        for i, (n, im) in enumerate(rows):
            x = 10 + i * (Z + 10)
            bg = Image.new("RGBA", im.size, (226, 220, 238, 255))
            bg.alpha_composite(im)
            sh.paste(bg.convert("RGB").resize((Z, Z), Image.LANCZOS), (x, 26))
            d.text((x + 2, 26 + Z + 1), n, font=F, fill=(170, 255, 190))
        sh.save(os.path.join(ROOT, "_sys_positions.png"))
        print("-> _sys_positions.png")


if __name__ == "__main__":
    main()
