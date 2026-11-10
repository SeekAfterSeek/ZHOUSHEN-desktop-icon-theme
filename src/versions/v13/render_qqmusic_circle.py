# -*- coding: utf-8 -*-
"""P6 美团构图 → 圆形图标 → 给 QQ音乐

用户要求：按截图构图（黄背景 + 黑衣 + 高举蓝麦克风），做成圆形
"""
import sys
import io
import os
import json
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from facedet import detect_face
import render_p20 as RP

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qqmusic_circle")
os.makedirs(OUT, exist_ok=True)

S = RP.S
SRC = os.path.join(r"D:\DSH\workspace\SMALL RESULT\周深原始照片库",
                   "picks__station_20260510_59173_0.jpg")
ACCENT = "#F5C542"      # QQ音乐金
APP = "QQ音乐"


def circle_mask(inset):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([inset, inset, S - 1 - inset, S - 1 - inset], fill=255)
    return m


def render_circle(src, tf, anchor_y, seed=1, bright=1.06, sat=1.06, contrast=1.07):
    ar = RP.hexrgb(ACCENT)
    rnd = random.Random(seed)
    im = Image.open(src).convert("RGB")
    W, H = im.size
    d = detect_face(im) or {"fx": .5, "fy": .30, "fw": .22, "fh": .22}

    face_h = d["fh"] * H
    crop = face_h / tf
    crop = max(S * 0.6, min(crop, float(min(W, H))))
    sc = S / crop
    nw, nh = max(S, int(round(W * sc))), max(S, int(round(H * sc)))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    cx, cy = d["fx"] * nw, d["fy"] * nh
    left = int(round(cx - S * 0.50))
    top = int(round(cy - S * anchor_y))
    left = max(0, min(left, nw - S))
    top = max(0, min(top, nh - S))
    cv = im2.crop((left, top, left + S, top + S)).convert("RGBA")

    cv = ImageEnhance.Brightness(cv).enhance(bright)
    cv = ImageEnhance.Contrast(cv).enhance(contrast)
    cv = ImageEnhance.Color(cv).enhance(sat)
    cv = cv.convert("RGBA")

    inset = int(S * 0.016)
    mask = circle_mask(inset)
    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(cv, (0, 0), mask)
    cv = cut

    glow = Image.new("RGBA", (S, S), ar + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .030)))
                  .point(lambda v: int(v * .44)))
    cv = Image.alpha_composite(glow, cv)

    # 金色圆环（QQ音乐原有特征）
    w = max(4, int(S * 0.026))
    ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    for k in range(w):
        t = k / max(1, w - 1)
        col = (255, int(206 + 34 * (1 - t)), int(70 + 120 * t))
        rd.ellipse([inset + k, inset + k, S - 1 - inset - k, S - 1 - inset - k],
                   outline=col + (255,), width=1)
    cv = Image.alpha_composite(cv, ring)
    cv = Image.alpha_composite(cv, ring)

    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([-S * .16, -S * .20, S * .66, S * .48],
                               fill=(255, 255, 255, 24))
    hi = hi.filter(ImageFilter.GaussianBlur(int(S * .055)))
    hi.putalpha(Image.composite(hi.split()[3], Image.new("L", (S, S), 0), mask))
    cv = Image.alpha_composite(cv, hi)

    sp = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for cx0, cy0 in rnd.sample([(.10, .12), (.90, .11), (.09, .84), (.91, .85)], 3):
        x = int(S * cx0 + rnd.uniform(-S * .03, S * .03))
        y = int(S * cy0 + rnd.uniform(-S * .03, S * .03))
        r1 = rnd.uniform(S * .017, S * .030)
        r2 = r1 * .28
        sd.polygon([(x, y - r1), (x + r2, y - r2), (x + r1, y), (x + r2, y + r2),
                    (x, y + r1), (x - r2, y + r2), (x - r1, y), (x - r2, y - r2)],
                   fill=(255, 255, 255, rnd.randint(85, 145)))
    sp.putalpha(Image.composite(sp.split()[3], Image.new("L", (S, S), 0), mask))
    cv = Image.alpha_composite(cv, sp)

    # QQ音乐角标（圆形）
    op = os.path.join(RP.ORIG_ICON, APP + ".png")
    if os.path.exists(op):
        BD = int(S * 0.360)
        bx = S - BD - RP.PAD_B
        by = S - BD - RP.PAD_B
        logo = Image.open(op).convert("RGBA")
        logo.thumbnail((int(BD * .68),) * 2, Image.LANCZOS)
        bd = Image.new("RGBA", (BD, BD), (0, 0, 0, 0))
        ImageDraw.Draw(bd).ellipse([0, 0, BD - 1, BD - 1],
                                   fill=(255, 255, 255, 246),
                                   outline=(16, 28, 50, 205), width=max(3, int(BD * .030)))
        bd.paste(logo, ((BD - logo.width) // 2, (BD - logo.height) // 2), logo)
        sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", bd.size, (0, 0, 0, 115)),
                 (bx + int(S * .008), by + int(S * .013)), bd.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(int(S * .011)))
        cv = Image.alpha_composite(cv, sh)
        cv.paste(bd, (bx, by), bd)

    soft = mask.filter(ImageFilter.GaussianBlur(int(S * .014))).point(lambda v: min(255, v * 2))
    cv.putalpha(Image.composite(cv.split()[3],
                                Image.eval(soft, lambda v: int(v * .5)),
                                Image.eval(mask, lambda v: 255 if v > 200 else 0)))
    return cv


if __name__ == "__main__":
    print("源图:", SRC, os.path.exists(SRC))
    variants = [(0.26, 0.42), (0.30, 0.44), (0.34, 0.45), (0.38, 0.46)]
    made = []
    for i, (tf, ay) in enumerate(variants):
        big = render_circle(SRC, tf, ay, seed=31000 + i * 11)
        sm = big.resize((256, 256), Image.LANCZOS)
        fn = "qq_tf%02d.png" % int(tf * 100)
        sm.save(os.path.join(OUT, fn))
        big.save(os.path.join(OUT, "big_" + fn))
        made.append((fn, tf, sm))
        print("渲染", fn)
    from PIL import ImageFont
    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    sh = Image.new("RGB", (len(made) * 230 + 20, 290), (20, 21, 29))
    d = ImageDraw.Draw(sh)
    d.text((12, 8), "QQ音乐（原美团构图，圆形+金边）", font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16),
           fill=(255, 255, 255))
    for i, (fn, tf, im) in enumerate(made):
        x = 12 + i * 230
        ic = im.resize((215, 215), Image.LANCZOS)
        sh.paste(ic, (x, 36), ic)
        d.text((x + 4, 258), fn, font=F, fill=(220, 230, 245))
    sh.save(os.path.join(OUT, "preview.png"))
    print("->", OUT)
