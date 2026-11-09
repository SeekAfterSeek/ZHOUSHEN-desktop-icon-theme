# -*- coding: utf-8 -*-
"""生成未用候选总表（大图），供肉眼审核身份与质量"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
PF = json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))
USED = set(json.load(open(os.path.join(ROOT, "used_history.json"), encoding="utf-8")))

FREE = [r for r in PF if r["file"] not in USED
        and r["face_px"] >= 330 and r["sharp"] >= 9.5 and r["farea"] >= 0.030
        and r["hlines"] < 2 and r["vlines"] < 2
        and r["topstd"] >= 5.5 and r["botstd"] >= 5.5]
FREE.sort(key=lambda r: -(min(r["face_px"], 1100) / 1100 * 1.2
                          + min(r["sharp"], 26) / 26
                          + min(r["farea"], 0.18) * 2))
print("审核候选:", len(FREE))

F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 12)
FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)
S, COLS = 210, 7
per = 42
pages = (len(FREE) + per - 1) // per
for p in range(pages):
    chunk = FREE[p * per:(p + 1) * per]
    rows = (len(chunk) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (S + 8), rows * (S + 42) + 34), (20, 20, 28))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), "未用候选 第%d/%d页  共%d张" % (p + 1, pages, len(FREE)),
           font=FB, fill=(255, 215, 120))
    for i, r in enumerate(chunk):
        x = (i % COLS) * (S + 8)
        y = 34 + (i // COLS) * (S + 42)
        try:
            im = Image.open(r["path"]).convert("RGB")
        except Exception:
            continue
        w, h = im.size
        sc = S / min(w, h)
        im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
        l = max(0, (im.width - S) // 2)
        t = max(0, (im.height - S) // 2)
        sheet.paste(im.crop((l, t, l + S, t + S)), (x, y))
        gid = p * per + i
        d.text((x + 2, y + S + 1), "%d %s" % (gid, r["file"][:26]), font=F, fill=(228, 234, 246))
        d.text((x + 2, y + S + 15), "fpx%.0f sh%s %s" % (r["face_px"], r["sharp"], r["dom"]),
               font=F, fill=(255, 200, 90))
    sheet.save(os.path.join(ROOT, "review_%02d.png" % p))
    print("  review_%02d.png  %d 张" % (p, len(chunk)))

json.dump([r["file"] for r in FREE],
          open(os.path.join(ROOT, "review_order.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
