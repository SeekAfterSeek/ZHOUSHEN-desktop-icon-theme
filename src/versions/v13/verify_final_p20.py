# -*- coding: utf-8 -*-
"""独立校验：桌面 shell 实际渲染 vs 设计母版（不依赖其他模块）"""
import ctypes
import os
import sys
import io
import uuid
from ctypes import wintypes, POINTER

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "v12_verify")
os.makedirs(OUT, exist_ok=True)

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32
ole32 = ctypes.windll.ole32


class SHFILEINFO(ctypes.Structure):
    _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int),
                ("dwAttributes", wintypes.DWORD),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]


class BMIH(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def himl():
    ole32.CoInitialize(None)
    iid = uuid.UUID("{46EB5926-582E-4017-9FDF-E8998DAA0950}").bytes_le
    h = ctypes.c_void_p()
    if shell32.SHGetImageList(0x4, iid, ctypes.byref(h)) != 0:
        return None
    return h


def grab(h, lnk, out, size=256):
    fi = SHFILEINFO()
    if not shell32.SHGetFileInfoW(lnk, 0, ctypes.byref(fi), ctypes.sizeof(fi),
                                  0x4000 | 0x8000):
        return False
    vt = ctypes.cast(h, POINTER(POINTER(ctypes.c_void_p)))[0]
    GetIcon = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
                                 ctypes.c_uint, POINTER(wintypes.HICON))(vt[10])
    hi = wintypes.HICON()
    if GetIcon(h, fi.iIcon, 1, ctypes.byref(hi)) != 0 or not hi:
        return False
    hdc = u32.GetDC(0)
    md = g32.CreateCompatibleDC(hdc)
    bm = g32.CreateCompatibleBitmap(hdc, size, size)
    old = g32.SelectObject(md, bm)
    br = g32.CreateSolidBrush(0x00202020)
    rc = wintypes.RECT(0, 0, size, size)
    u32.FillRect(md, ctypes.byref(rc), br)
    g32.DeleteObject(br)
    u32.DrawIconEx(md, 0, 0, hi, size, size, 0, None, 3)

    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH)
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
    g32.SelectObject(md, old)
    g32.DeleteObject(bm)
    g32.DeleteDC(md)
    u32.ReleaseDC(0, hdc)
    u32.DestroyIcon(hi)
    im = Image.frombytes("RGBA", (size, size), buf)
    b_, g_, r_, a_ = im.split()
    Image.merge("RGBA", (r_, g_, b_, a_)).convert("RGB").save(out)
    return True


DESKTOPS = [r"C:\Users\Public\Desktop", r"D:\Desktop",
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")]


def find(name):
    for d in DESKTOPS:
        p = os.path.join(d, name + ".lnk")
        if os.path.exists(p):
            return p
    return None


CASES = [
    ("个人 - Edge", "design_v12/个人 - Edge.png"),
    ("联想电脑管家", "design_v12/联想电脑管家.png"),
    ("Visual Studio Code", "design_v12/Visual Studio Code.png"),
    ("哔哩哔哩", "design_v12/哔哩哔哩.png"),
    ("哔哩哔哩 2", "_p20_out/P4_bili_哔哩哔哩.png"),
    ("DeepSeek Harness", "design_v12/DeepSeek Harness.png"),
    ("互传", "design_v12/互传.png"),
    ("ToDesk", "design_v12/ToDesk.png"),
    ("QQ音乐", "design_v12/QQ音乐.png"),
]

h = himl()
rows = []
print("%-22s %-8s %-8s %s" % ("APP", "全图差", "中心差", "判定"))
print("-" * 54)
for app, ref_rel in CASES:
    lnk = find(app)
    if not lnk:
        print("%-22s 无快捷方式" % app)
        continue
    out = os.path.join(OUT, "chk_" + app.replace(" ", "_") + ".png")
    if not grab(h, lnk, out):
        print("%-22s 取图失败" % app)
        continue
    ref = Image.open(os.path.join(ROOT, ref_rel)).convert("RGBA")
    if ref.size != (256, 256):
        ref = ref.resize((256, 256), Image.LANCZOS)
    bg = Image.new("RGBA", (256, 256), (32, 32, 32, 255))
    a = np.asarray(Image.alpha_composite(bg, ref).convert("RGB"), np.int16)
    b = np.asarray(Image.open(out).convert("RGB"), np.int16)
    d = np.abs(a - b)
    c = d[51:205, 51:205]
    ok = c.mean() < 8
    print("%-22s %-8.1f %-8.1f %s" % (app, d.mean(), c.mean(),
                                      "✓ 一致" if ok else "✗ 不一致"))
    rows.append((app, out, ok))

# 拼图
S = 200
F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)
sheet = Image.new("RGB", (len(rows) * (S + 12) + 14, S + 60), (18, 19, 26))
d = ImageDraw.Draw(sheet)
d.text((14, 10), "桌面实况（Windows shell 渲染）", font=FB, fill=(255, 255, 255))
for i, (app, p, ok) in enumerate(rows):
    x = 14 + i * (S + 12)
    im = Image.open(p).convert("RGB").resize((S, S), Image.LANCZOS)
    sheet.paste(im, (x, 38))
    d.text((x + 2, 38 + S + 2), app[:12], font=F,
           fill=(150, 255, 175) if ok else (255, 130, 130))
sheet.save(os.path.join(ROOT, "_p20_final_check.png"))
print("\n拼图 ->", os.path.join(ROOT, "_p20_final_check.png"))
