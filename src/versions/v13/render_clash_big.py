# -*- coding: utf-8 -*-
"""Clash Verge：人脸占比放大（兔耳必须完整）"""
import sys
import io
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
from facedet import detect_face
import render_p20 as RP

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
OUT = os.path.join(ROOT, "_clash_big")
os.makedirs(OUT, exist_ok=True)
S = RP.S
SRC = os.path.join(LIB, "fc2_src__f2_0169.jpg")
APP = "Clash Verge"
ACCENT = RP.ACCENT[APP]

_im = Image.open(SRC).convert("RGB")
_W, _H = _im.size
_D = detect_face(_im) or {"fx": .5, "fy": .30, "fw": .22, "fh": .22}


def crop_at(tf, ay):
    face_h = _D["fh"] * _H
    crop = face_h / tf
    crop = max(S * 0.6, min(crop, float(min(_W, _H))))
    sc = S / crop
    nw, nh = max(S, int(round(_W * sc))), max(S, int(round(_H * sc)))
    im2 = _im.resize((nw, nh), Image.LANCZOS)
    cx, cy = _D["fx"] * nw, _D["fy"] * nh
    left = max(0, min(int(round(cx - S * 0.50)), nw - S))
    top = max(0, min(int(round(cy - S * ay)), nh - S))
    return im2.crop((left, top, left + S, top + S))


def ear_ratio(crop):
    """兔耳/粉色毛绒是否完整（白色毛绒 + 粉色）"""
    a = np.asarray(crop)
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # 白色绒毛：高亮低饱和
    white = ((v >= 170) & (s <= 60)).astype(np.uint8)
    white[int(S * .40):, :] = 0
    ys = np.where(white.any(axis=1))[0]
    return int(ys.min()) if len(ys) else -1


def render(tf, ay, seed=1, circle=True):
    ar = RP.hexrgb(ACCENT)
    rnd = random.Random(seed)
    crop = crop_at(tf, ay)
    cv = crop.convert("RGBA")
    cv = ImageEnhance.Brightness(cv).enhance(1.05)
    cv = ImageEnhance.Contrast(cv).enhance(1.07)
    cv = ImageEnhance.Color(cv).enhance(1.04)

    ins = int(S * 0.016)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse([ins, ins, S - 1 - ins, S - 1 - ins], fill=255)

    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(cv, (0, 0), mask)
    cv = cut

    glow = Image.new("RGBA", (S, S), ar + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .030)))
                  .point(lambda v: int(v * .40)))
    cv = Image.alpha_composite(glow, cv)

    ring = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.2))
    ring = ring.point(lambda v: 255 if v > 40 else 0)
    edge = Image.new("RGBA", (S, S), ar + (235,))
    edge.putalpha(ring)
    cv = Image.alpha_composite(cv, edge)

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

    BD = int(S * 0.360)
    bx = S - BD - RP.PAD_B
    by = S - BD - RP.PAD_B
    logo = Image.open(os.path.join(RP.ORIG_ICON, APP + ".png")).convert("RGBA")
    logo.thumbnail((int(BD * .66),) * 2, Image.LANCZOS)
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
    made = []
    for i, (tf, ay) in enumerate([(0.32, 0.44), (0.38, 0.46), (0.44, 0.47), (0.50, 0.48)]):
        big = render(tf, ay, seed=58000 + i * 73)
        sm = big.resize((256, 256), Image.LANCZOS)
        ear_y = ear_ratio(crop_at(tf, ay))
        name = "cl_tf%02d" % int(tf * 100)
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, sm, tf, ear_y))
        print("渲染 %s  毛绒顶沿 y=%d (0=被切)" % (name, ear_y))

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 250
    cur = Image.open(os.path.join(ROOT, "design_v12", "Clash Verge.png")).convert("RGBA")
    sheet = Image.new("RGB", ((len(made) + 1) * (S2 + 14) + 14, S2 + 100), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "Clash Verge 脸放大（最左=当前 32%）", font=FB, fill=(255, 255, 255))
    bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
    bg.alpha_composite(cur.resize((S2, S2), Image.LANCZOS))
    sheet.paste(bg.convert("RGB"), (14, 44))
    d.text((16, 44 + S2 + 4), "当前 32%", font=F, fill=(120, 220, 255))
    for i, (name, im, tf, ey) in enumerate(made):
        x = 14 + (i + 1) * (S2 + 14)
        bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
        bg.alpha_composite(im.resize((S2, S2), Image.LANCZOS))
        sheet.paste(bg.convert("RGB"), (x, 44))
        d.text((x + 2, 44 + S2 + 4), "%s 耳y=%d" % (name, ey), font=F,
               fill=(230, 236, 248) if ey > 4 else (255, 140, 140))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
