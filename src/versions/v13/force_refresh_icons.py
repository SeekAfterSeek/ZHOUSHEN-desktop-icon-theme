# -*- coding: utf-8 -*-
"""强制刷新桌面图标缓存

Windows 对 .lnk 的图标按「路径 + 时间戳」缓存。只换 ICO 内容、不碰时间戳，
桌面会继续显示旧图 —— 这正是「文件都对了但桌面没变」的原因。

做法：
  1. 触碰全部 ICO 与 .lnk 的修改时间
  2. SHChangeNotify 广播（全局 + 逐个文件）
  3. 清 iconcache/thumbcache 并重启 explorer
  4. 回读校验
"""
import sys
import io
import os
import time
import json
import ctypes
import uuid
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
ICO_DIR = r"C:\Users\Lenovo\zsIcons"
NAME_MAP = json.load(open(os.path.join(ROOT, "name_map.json"), encoding="utf-8"))

APPS = {
    "个人 - Edge": "edge",
    "联想电脑管家": "lenovopc",
    "Visual Studio Code": "vscode",
    "哔哩哔哩": "bilibili",
    "哔哩哔哩 2": "bilibili2",
    "DeepSeek Harness": "deepseek",
    "互传": "huchuan",
    "ToDesk": "todesk",
    "QQ音乐": "qqmusic",
}

DESKTOPS = [r"C:\Users\Public\Desktop", r"D:\Desktop",
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")]

shell32 = ctypes.windll.shell32
SHCNE_ASSOCCHANGED = 0x08000000
SHCNE_UPDATEITEM = 0x00002000
SHCNF_IDLIST = 0x0000
SHCNF_PATHW = 0x0005

now = time.time() + 2
touched = []
skipped = []
for app, icn in APPS.items():
    ico = os.path.join(ICO_DIR, icn + ".ico")
    if os.path.exists(ico):
        try:
            os.utime(ico, (now, now))
            touched.append(ico)
        except Exception:
            skipped.append(ico)
    for d in DESKTOPS:
        lnk = os.path.join(d, app + ".lnk")
        if os.path.exists(lnk):
            try:
                os.utime(lnk, (now, now))
                touched.append(lnk)
            except Exception:
                skipped.append(lnk)
print("已触碰 %d 个文件时间戳（%d 个无权限，已跳过）" % (len(touched), len(skipped)))

# 逐个通知
for p in touched:
    shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW,
                           ctypes.c_wchar_p(p), None)
# 全局重建
shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
print("已发送 SHChangeNotify")

# 清缓存 + 重启 explorer
cd = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Explorer")
subprocess.run(["taskkill", "/f", "/im", "explorer.exe"],
               capture_output=True, text=True)
time.sleep(3)
for f in os.listdir(cd):
    if f.lower().startswith(("iconcache", "thumbcache")) and f.lower().endswith(".db"):
        try:
            os.remove(os.path.join(cd, f))
        except Exception:
            pass
time.sleep(1)
subprocess.Popen(["explorer.exe"])
time.sleep(12)
print("explorer 已重启")

# 回读校验
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_desktop import get_himl, grab, find_lnk  # noqa

himl = get_himl()
V = os.path.join(ROOT, "v12_verify")
os.makedirs(V, exist_ok=True)
print("\n%-22s %-8s %-8s %s" % ("APP", "全图差", "中心差", "判定"))
print("-" * 52)
for app in APPS:
    lnk = find_lnk(app)
    if not lnk:
        print("%-22s 无快捷方式" % app); continue
    out = os.path.join(V, "p20_" + app.replace(" ", "_") + ".png")
    if not grab(himl, lnk, out):
        print("%-22s 取图失败" % app); continue
    refp = os.path.join(ROOT, "design_v12", app + ".png")
    if app == "哔哩哔哩 2":
        refp = os.path.join(ROOT, "_p20_out", "P4_bili_哔哩哔哩.png")
    ref = Image.open(refp).convert("RGBA")
    bg = Image.new("RGBA", (256, 256), (32, 32, 32, 255))
    a = np.asarray(Image.alpha_composite(bg, ref).convert("RGB"), np.int16)
    b = np.asarray(Image.open(out).convert("RGB"), np.int16)
    d = np.abs(a - b)
    c = d[51:205, 51:205]
    print("%-22s %-8.1f %-8.1f %s" % (app, d.mean(), c.mean(),
                                      "✓ 一致" if c.mean() < 8 else "✗ 不一致"))
