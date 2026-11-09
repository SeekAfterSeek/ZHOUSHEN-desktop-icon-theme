# -*- coding: utf-8 -*-
"""全版本横向对比：每个 APP 一行，从左到右依次为 12 个版本
   每版保留它当时的最终形状与外观，不重绘
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "ALL_VERSIONS")
os.makedirs(OUT, exist_ok=True)

# 版本顺序：从第一版到最后
VERS = [
    ("icons",      "第一版",   "深蓝扁平",   "无照片"),
    ("icons_v2",   "第二版",   "舞台照+轮廓", "无照片"),
    ("icons_v3",   "第三版",   "写真满铺",   "拱形"),
    ("icons_v4",   "第四版",   "配色匹配",   "拱形"),
    ("icons_v5",   "第五版",   "氛围异形",   "波浪/鹅卵石"),
    ("design_v7",  "第七版",   "背景配色",   "圆角方形"),
    ("design_v8",  "第八版",   "衣服配色",   "圆形"),
    ("design_v9",  "第九版",   "图标色×衣服", "圆形"),
    ("design_v10", "第十版",   "衣服色终版",  "圆角方形"),
    ("design_v11", "第十一版",  "三标准加权",  "方圆各半"),
    ("planB",      "Plan B",  "全换新照",   "方形为主"),
    ("planC",      "Plan C",  "全换新照",   "圆形为主"),
]

ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

# 尺寸：与用户提供的参考图一致，图标约 210px
ICON = 210
GAP = 22
LBLW = 190          # 左侧 APP 名列宽
HEADH = 168         # 顶部表头高
ROWH = ICON + 62    # 每行高

FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)
FH = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)
FA = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
FS = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)

W = LBLW + len(VERS) * (ICON + GAP) + GAP
H = HEADH + len(ORDER) * ROWH + 20

canvas = Image.new("RGB", (W, H), (15, 16, 23))
d = ImageDraw.Draw(canvas)

# ---- 背景渐变 ----
for i in range(HEADH + 40):
    t = i / (HEADH + 40)
    d.line([(0, i), (W, i)],
           fill=(int(16 + 14 * t), int(18 + 9 * t), int(28 + 18 * t)))

# ---- 标题 ----
d.text((22, 14), "周深主题桌面图标 · 全版本对比（第一版 → Plan C）",
       font=FB, fill=(255, 255, 255))
d.text((22, 50), "每个 APP 一行；每一版保留它当时的最终形状与外观（异形版就是异形，方/圆版就是方/圆），不重绘",
       font=FH, fill=(150, 205, 240))
d.text((22, 76), "共 12 个版本 × 24 个应用 ｜ 图标 210px ｜ 用于精细挑选与修改",
       font=FS, fill=(130, 145, 168))

# ---- 表头：版本名 + 风格 + 形状 ----
for j, (folder, name, style, shape) in enumerate(VERS):
    x = LBLW + j * (ICON + GAP) + GAP // 2
    col = (255, 215, 120) if folder in ("design_v11",) else \
          ((120, 210, 255) if folder.startswith("plan") else (178, 188, 210))
    bb = d.textbbox((0, 0), name, font=FH)
    d.text((x + (ICON - (bb[2] - bb[0])) // 2, HEADH - 52), name, font=FH, fill=col)
    bb2 = d.textbbox((0, 0), shape, font=FS)
    d.text((x + (ICON - (bb2[2] - bb2[0])) // 2, HEADH - 30), shape, font=FS,
           fill=(120, 132, 155))
    # 列分隔线
    if j:
        d.line([(LBLW + j * (ICON + GAP) + GAP // 2 - GAP // 2, HEADH - 4),
                (LBLW + j * (ICON + GAP) + GAP // 2 - GAP // 2, H - 10)],
               fill=(30, 32, 44))

missing = []
for i, app in enumerate(ORDER):
    y = HEADH + i * ROWH
    # 行底色（隔行）
    if i % 2 == 0:
        d.rectangle([0, y - 6, W, y + ROWH - 10], fill=(20, 21, 30))
    # APP 名
    d.text((24, y + ICON // 2 - 16), app, font=FA, fill=(238, 242, 250))

    for j, (folder, name, style, shape) in enumerate(VERS):
        p = os.path.join(ROOT, folder, app + ".png")
        x = LBLW + j * (ICON + GAP) + GAP // 2
        if not os.path.exists(p):
            missing.append((folder, app))
            d.rectangle([x, y, x + ICON, y + ICON], outline=(52, 56, 70), width=1)
            bb = d.textbbox((0, 0), "—", font=FA)
            d.text((x + (ICON - (bb[2] - bb[0])) // 2, y + ICON // 2 - 10),
                   "—", font=FA, fill=(80, 85, 100))
            continue
        ic = Image.open(p).convert("RGBA")
        # 统一缩放到 ICON，保持原比例与透明
        if ic.size != (ICON, ICON):
            ic = ic.resize((ICON, ICON), Image.LANCZOS)
        canvas.paste(ic, (x, y), ic)

print("缺失组合:", len(missing))
if missing:
    for m in missing[:20]:
        print("   ", m)

canvas.save(os.path.join(OUT, "ALL_VERSIONS_x24.png"))
print("->", os.path.join(OUT, "ALL_VERSIONS_x24.png"), canvas.size)

# 同时输出分页版（每页 6 个 APP，便于放大查看）
PER = 6
pages = (len(ORDER) + PER - 1) // PER
for p in range(pages):
    chunk = ORDER[p * PER:(p + 1) * PER]
    hp = HEADH + len(chunk) * ROWH + 20
    page = Image.new("RGB", (W, hp), (15, 16, 23))
    dp = ImageDraw.Draw(page)
    for i in range(HEADH + 40):
        t = i / (HEADH + 40)
        dp.line([(0, i), (W, i)],
                fill=(int(16 + 14 * t), int(18 + 9 * t), int(28 + 18 * t)))
    dp.text((22, 14), "全版本对比 第%d/%d页" % (p + 1, pages), font=FB, fill=(255, 255, 255))
    dp.text((22, 50), "每行一个 APP，从左到右：第一版 → 第十一版 → Plan B → Plan C",
            font=FH, fill=(150, 205, 240))
    for j, (folder, name, style, shape) in enumerate(VERS):
        x = LBLW + j * (ICON + GAP) + GAP // 2
        col = (255, 215, 120) if folder == "design_v11" else \
              ((120, 210, 255) if folder.startswith("plan") else (178, 188, 210))
        bb = dp.textbbox((0, 0), name, font=FH)
        dp.text((x + (ICON - (bb[2] - bb[0])) // 2, HEADH - 52), name, font=FH, fill=col)
        bb2 = dp.textbbox((0, 0), shape, font=FS)
        dp.text((x + (ICON - (bb2[2] - bb2[0])) // 2, HEADH - 30), shape, font=FS,
                fill=(120, 132, 155))
        if j:
            dp.line([(LBLW + j * (ICON + GAP) + GAP // 2 - GAP // 2, HEADH - 4),
                     (LBLW + j * (ICON + GAP) + GAP // 2 - GAP // 2, hp - 10)],
                    fill=(30, 32, 44))
    for i, app in enumerate(chunk):
        y = HEADH + i * ROWH
        if i % 2 == 0:
            dp.rectangle([0, y - 6, W, y + ROWH - 10], fill=(20, 21, 30))
        dp.text((24, y + ICON // 2 - 16), app, font=FA, fill=(238, 242, 250))
        for j, (folder, name, style, shape) in enumerate(VERS):
            pth = os.path.join(ROOT, folder, app + ".png")
            x = LBLW + j * (ICON + GAP) + GAP // 2
            if not os.path.exists(pth):
                dp.rectangle([x, y, x + ICON, y + ICON], outline=(52, 56, 70), width=1)
                continue
            ic = Image.open(pth).convert("RGBA")
            if ic.size != (ICON, ICON):
                ic = ic.resize((ICON, ICON), Image.LANCZOS)
            page.paste(ic, (x, y), ic)
    page.save(os.path.join(OUT, "page_%d.png" % (p + 1)))
    print("  page_%d.png  %s" % (p + 1, chunk))
