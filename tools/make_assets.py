# -*- coding: utf-8 -*-
"""生成 README 用的展示图：hero / 三方案对比 / 全版本 / 配色原理"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
DST = r"D:\DSH\workspace\SMALL RESULT\zs-icon-theme-release\assets"
os.makedirs(DST, exist_ok=True)

ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)
FM = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
FS = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 12)

# ---------- 1) hero_v11：v11 的 24 图标，横版 ----------
CELL, COLS = 190, 8
GW = 164
rows = (len(ORDER) + COLS - 1) // COLS
W, H = COLS * CELL, 96 + rows * (CELL + 26)
g = Image.new("RGB", (W, H), (17, 18, 26))
d = ImageDraw.Draw(g)
for i in range(96):
    t = i / 96
    d.line([(0, i), (W, i)], fill=(int(18 + 14 * t), int(20 + 9 * t), int(30 + 20 * t)))
d.text((20, 14), "周深桌面图标主题 · 第十一版", font=FB, fill=(255, 255, 255))
d.text((20, 50), "24 个应用 ｜ 只改图标不改壁纸 ｜ 一键回退", font=FM, fill=(150, 205, 240))
for i, n in enumerate(ORDER):
    p = os.path.join(SRC, "design_v11", n + ".png")
    if not os.path.exists(p):
        continue
    x = (i % COLS) * CELL
    y = 92 + (i // COLS) * (CELL + 26)
    ic = Image.open(p).convert("RGBA").resize((GW, GW), Image.LANCZOS)
    sh = Image.new("RGBA", (GW + 12, GW + 12), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", (GW, GW), (0, 0, 0, 120)), (6, 8), ic.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    g.paste(Image.alpha_composite(
        Image.new("RGBA", (GW + 12, GW + 12), (17, 18, 26, 255)), sh).convert("RGB"),
        (x + 10, y + 2))
    g.paste(ic, (x + 15, y + 4), ic)
g.save(os.path.join(DST, "hero_v11.png"))
print("hero_v11.png", g.size)

# ---------- 2) compare_3plans：v11 / planB / planC（横向，每方案 8 列 3 行）----------
VERS = [("第十一版 v11", "design_v11"), ("Plan B", "planB"), ("Plan C", "planC")]
IC2, GC = 118, 10
COLS2 = 6
PBLOCK = COLS2 * (IC2 + GC) + 34      # 每个方案的宽度
W2 = 20 + len(VERS) * PBLOCK
ROWS2 = 4
H2 = 118 + ROWS2 * (IC2 + 16) + 34
c = Image.new("RGB", (W2, H2), (16, 17, 24))
dc = ImageDraw.Draw(c)
for i in range(H2):
    t = i / H2
    dc.line([(0, i), (W2, i)], fill=(int(18 + 12 * t), int(20 + 8 * t), int(32 + 16 * t)))
dc.text((20, 12), "三套方案对比", font=FB, fill=(255, 255, 255))
dc.text((20, 48), "Plan B / Plan C 用到的照片与 v11 及彼此零重叠", font=FS, fill=(150, 205, 240))

for j, (label, dd) in enumerate(VERS):
    bx = 20 + j * PBLOCK
    dc.text((bx + 4, 88), label, font=FM,
            fill=(255, 215, 120) if j == 0 else (130, 200, 255))
    for i, n in enumerate(ORDER):
        r, cc = i // COLS2, i % COLS2
        x = bx + cc * (IC2 + GC)
        y = 118 + r * (IC2 + 16)
        p = os.path.join(SRC, dd, n + ".png")
        if not os.path.exists(p):
            continue
        ic = Image.open(p).convert("RGBA").resize((IC2, IC2), Image.LANCZOS)
        c.paste(ic, (x, y), ic)
    # 方案之间的分隔线
    if j:
        dc.line([(bx - 18, 80), (bx - 18, H2 - 16)], fill=(40, 44, 58))

c.save(os.path.join(DST, "compare_3plans.png"))
print("compare_3plans.png", c.size)

# ---------- 3) all_versions：12 版横向（缩小版） ----------
V12 = [("icons", "v1"), ("icons_v2", "v2"), ("icons_v3", "v3"), ("icons_v4", "v4"),
       ("icons_v5", "v5"), ("design_v7", "v7"), ("design_v8", "v8"),
       ("design_v9", "v9"), ("design_v10", "v10"), ("design_v11", "v11"),
       ("planB", "B"), ("planC", "C")]
S3, G3 = 96, 8
LBL = 132
W3 = LBL + len(V12) * (S3 + G3) + 12
H3 = 66 + len(ORDER) * (S3 + 22) + 10
a = Image.new("RGB", (W3, H3), (16, 17, 24))
da = ImageDraw.Draw(a)
for i in range(66):
    t = i / 66
    da.line([(0, i), (W3, i)], fill=(int(18 + 12 * t), int(20 + 8 * t), int(30 + 16 * t)))
da.text((16, 10), "12 个版本的演化", font=FB, fill=(255, 255, 255))
da.text((16, 42), "异形 → 方圆，扁平 → 写真，人工挑图 → 算法分配", font=FS, fill=(150, 205, 240))
for j, (folder, nm) in enumerate(V12):
    x = LBL + j * (S3 + G3)
    da.text((x + 26, 42), nm, font=FS, fill=(255, 215, 120) if nm == "v11" else (170, 180, 200))
for i, n in enumerate(ORDER):
    y = 70 + i * (S3 + 22)
    da.text((12, y + S3 // 2 - 7), n[:10], font=FS, fill=(226, 232, 244))
    for j, (folder, nm) in enumerate(V12):
        p = os.path.join(SRC, folder, n + ".png")
        x = LBL + j * (S3 + G3)
        if not os.path.exists(p):
            continue
        ic = Image.open(p).convert("RGBA").resize((S3, S3), Image.LANCZOS)
        a.paste(ic, (x, y), ic)
a.save(os.path.join(DST, "all_versions.png"))
print("all_versions.png", a.size)

# ---------- 4) color_matching：配色匹配原理示意 ----------
S4 = 210
apps = ["微信", "Google Chrome", "Cursor", "网易邮箱大师"]
W4 = len(apps) * (S4 * 3 + 40) + 40
H4 = S4 + 130
m = Image.new("RGB", (W4, H4), (17, 18, 26))
dm = ImageDraw.Draw(m)
for i in range(H4):
    t = i / H4
    dm.line([(0, i), (W4, i)], fill=(int(18 + 10 * t), int(20 + 8 * t), int(30 + 14 * t)))
dm.text((20, 12), "配色匹配原理：原图标 → 候选照片 → 调色后成品", font=FB, fill=(255, 255, 255))
dm.text((20, 48), "实拍照片的配色不可能等于扁平 logo，所以要多一层调色把它掰向靶心",
        font=FS, fill=(150, 205, 240))
import json
ASG = {}
for dd, tag in (("design_v11", "v11"),):
    p = os.path.join(SRC, dd, "assign.json")
    if os.path.exists(p):
        ASG = json.load(open(p, encoding="utf-8"))

for i, app in enumerate(apps):
    bx = 20 + i * (S4 * 3 + 40)
    y0 = 78
    # 原图标
    op = os.path.join(SRC, "backup", "original-icons-256", app + ".png")
    if os.path.exists(op):
        ic = Image.open(op).convert("RGBA").resize((S4, S4), Image.LANCZOS)
        m.paste(ic, (bx, y0), ic)
    dm.text((bx + 6, y0 + S4 + 6), "原图标", font=FS, fill=(180, 190, 210))
    # 照片
    info = ASG.get(app, {})
    sp = info.get("path")
    if sp and os.path.exists(sp):
        src = Image.open(sp).convert("RGB")
        w, h = src.size
        sc = S4 / min(w, h)
        src = src.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
        l = max(0, (src.width - S4) // 2)
        t = max(0, (src.height - S4) // 2)
        m.paste(src.crop((l, t, l + S4, t + S4)), (bx + S4 + 20, y0))
    dm.text((bx + S4 + 26, y0 + S4 + 6), "源照片", font=FS, fill=(180, 190, 210))
    # 成品
    rp = os.path.join(SRC, "design_v11", app + ".png")
    if os.path.exists(rp):
        ic = Image.open(rp).convert("RGBA").resize((S4, S4), Image.LANCZOS)
        m.paste(ic, (bx + S4 * 2 + 40, y0), ic)
    dm.text((bx + S4 * 2 + 46, y0 + S4 + 6), "调色后成品", font=FS, fill=(255, 215, 120))
m.save(os.path.join(DST, "color_matching.png"))
print("color_matching.png", m.size)
