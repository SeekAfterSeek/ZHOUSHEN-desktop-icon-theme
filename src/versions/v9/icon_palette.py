# -*- coding: utf-8 -*-
"""按【原图标真实配色】+【衣服颜色】重新匹配 24 APP

1. 先用原图标像素统计出真实主色（暗/亮/各色相占比）
2. 再在素材池里按「衣服颜色」找最接近的
3. 全程记录置信度，便于核对
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
ORIG = os.path.join(ROOT,"backup","original-icons-256")
DESIGN = os.path.join(ROOT,"design_v8")

APPS = ["微信","QQ音乐","哔哩哔哩","Google Chrome","个人 - Edge","360安全浏览器",
        "Visual Studio Code","Cursor","DeepSeek Harness","Cherry Studio","WorkBuddy",
        "WPS Office","全能录屏助手","剪映专业版","百度网盘","飞书","Clash Verge",
        "PyCharm 2026.2.3","ToDesk","互传","网易邮箱大师","联想电脑管家","腾讯QQ","腾讯会议"]

def icon_palette(name):
    """统计原图标的真实配色分布"""
    p = os.path.join(ORIG, name + ".png")
    if not os.path.exists(p): return None
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im).astype(np.float32)/255.0
    alpha = a[...,3]
    rgb = a[...,:3]
    mask = alpha > 0.78
    if mask.sum() < 100: return None
    px = rgb[mask]
    mx = px.max(axis=1); mn = px.min(axis=1)
    l = (mx+mn)/2
    s = np.where(mx==mn, 0, (mx-mn)/np.maximum(1e-6, 1-np.abs(2*l-1)))
    r,g,b = px[:,0],px[:,1],px[:,2]
    dd = mx-mn+1e-6
    h = np.where(mx==r, ((g-b)/dd)%6, np.where(mx==g,(b-r)/dd+2,(r-g)/dd+4))*60
    n = len(px)
    ok = (s>=0.20)&(l>=0.12)&(l<=0.88)
    pal = {
        "black": float((l<0.16).sum()/n),
        "white": float((l>0.82).sum()/n),
        "gray":  float(((s<0.20)&(l>=0.16)&(l<=0.82)).sum()/n),
        "red":   float((((h<15)|(h>=345))&ok).sum()/n),
        "orange":float(((h>=15)&(h<40)&ok).sum()/n),
        "yellow":float(((h>=40)&(h<70)&ok).sum()/n),
        "green": float(((h>=70)&(h<165)&ok).sum()/n),
        "cyan":  float(((h>=165)&(h<200)&ok).sum()/n),
        "blue":  float(((h>=200)&(h<265)&ok).sum()/n),
        "purple":float(((h>=265)&(h<310)&ok).sum()/n),
        "pink":  float(((h>=310)&(h<345)&ok).sum()/n),
    }
    return pal

print("=== 原图标真实配色 ===")
PAL = {}
for n in APPS:
    p = icon_palette(n)
    PAL[n] = p
    if p:
        top = sorted(p.items(), key=lambda x:-x[1])[:3]
        print("  %-20s %s" % (n, "  ".join("%s %.0f%%"%(k,v*100) for k,v in top)))

json.dump(PAL, open(os.path.join(DESIGN,"icon_palette.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
