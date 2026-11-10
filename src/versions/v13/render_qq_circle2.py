# -*- coding: utf-8 -*-
"""圆形版：在耳朵不被裁的前提下，搜索最大人脸比例

判定：耳朵毛色区域落在圆形遮罩内的比例 >= 0.98
"""
import sys
import io
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from facedet import detect_face
import render_p20 as RP

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
OUT = os.path.join(ROOT, "_qq_circle2")
os.makedirs(OUT, exist_ok=True)
SRC = os.path.join(LIB, "photos_2026__station_20261017_31971_5.jpg")
APP = "腾讯QQ"
ACCENT = "#7F5547"
S = RP.S
QP = os.path.join(RP.ORIG_ICON, APP + ".png")

_im = Image.open(SRC).convert("RGB")
_W, _H = _im.size
_D = detect_face(_im) or {"fx": .5, "fy": .30, "fw": .22, "fh": .22}


def crop_at(tf, anchor_y):
    face_h = _D["fh"] * _H
    crop = face_h / tf
    crop = max(S * 0.6, min(crop, float(min(_W, _H))))
    sc = S / crop
    nw, nh = max(S, int(round(_W * sc))), max(S, int(round(_H * sc)))
    im2 = _im.resize((nw, nh), Image.LANCZOS)
    cx, cy = _D["fx"] * nw, _D["fy"] * nh
    left = max(0, min(int(round(cx - S * 0.50)), nw - S))
    top = max(0, min(int(round(cy - S * anchor_y)), nh - S))
    return im2.crop((left, top, left + S, top + S))


def circle_mask(inset_ratio=0.016):
    ins = int(S * inset_ratio)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([ins, ins, S - 1 - ins, S - 1 - ins], fill=255)
    return m


def ear_keep_ratio(crop, mask):
    a = np.asarray(crop)
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    m = ((h >= 4) & (h <= 30) & (s >= 95) & (v >= 80)).astype(np.uint8)
    m[int(S * 0.30):, :] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    if m.sum() == 0:
        return 0.0, 0
    inside = (m & (np.asarray(mask) > 128)).sum()
    return inside / float(m.sum()), int(m.sum())


def render(tf, anchor_y, seed=1):
    ar = RP.hexrgb(ACCENT)
    import random
    rnd = random.Random(seed)
    crop = crop_at(tf, anchor_y)
    cv = crop.convert("RGBA")
    cv = ImageEnhance.Brightness(cv).enhance(1.06)
    cv = ImageEnhance.Contrast(cv).enhance(1.08)
    cv = ImageEnhance.Color(cv).enhance(1.06)

    mask = circle_mask()
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

    BD = int(S * 0.300)
    bx = S - BD - RP.PAD_B
    by = S - BD - RP.PAD_B
    logo = Image.open(QP).convert("RGBA")
    logo.thumbnail((int(BD * .66),) * 2, Image.LANCZOS)
    bd = Image.new("RGBA", (BD, BD), (0, 0, 0, 0))
    ImageDraw.Draw(bd).ellipse([0, 0, BD - 1, BD - 1],
                               fill=(255, 255, 255, 250),
                               outline=(16, 28, 50, 235), width=max(3, int(BD * .032)))
    bd.paste(logo, ((BD - logo.width) // 2, (BD - logo.height) // 2), logo)
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", bd.size, (0, 0, 0, 120)),
             (bx + int(S * .008), by + int(S * .013)), bd.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(int(S * .011)))
    cv = Image.alpha_composite(cv, sh)
    cv.paste(bd, (bx, by), bd)

    soft = mask.filter(ImageFilter.GaussianBlur(int(S * .014))).point(lambda v: min(255, v * 2))
    photo_a = Image.composite(cv.split()[3],
                              Image.eval(soft, lambda v: int(v * .5)),
                              Image.eval(mask, lambda v: 255 if v > 200 else 0))
    badge_a = Image.new("L", (S, S), 0)
    badge_a.paste(bd.split()[3], (bx, by))
    final_a = Image.composite(photo_a, badge_a, mask.point(lambda v: 255 if v > 0 else 0))
    cv.putalpha(final_a)
    return cv


if __name__ == "__main__":
    mask = circle_mask()
    print("%-6s %-6s %-8s %s" % ("tf", "anchor", "耳保留率", "耳像素"))
    print("-" * 40)
    keep = []
    for tf in (0.28, 0.30, 0.32, 0.34, 0.36, 0.38, 0.40):
        for ay in (0.44, 0.48, 0.52):
            c = crop_at(tf, ay)
            r, px = ear_keep_ratio(c, mask)
            ok = r >= 0.98
            print("%-6.2f %-6.2f %-8.3f %-6d %s" % (tf, ay, r, px, "✓" if ok else ""))
            if ok:
                keep.append((tf, ay, r))
    keep.sort(key=lambda x: (-x[0], -x[2]))
    print("\n可用组合 %d 个，最大人脸比例 %.2f" % (len(keep), keep[0][0] if keep else 0))

    # 渲染前 4 个最优
    best = keep[:4]
    made = []
    for i, (tf, ay, r) in enumerate(best):
        big = render(tf, ay, seed=49000 + i * 43)
        sm = big.resize((256, 256), Image.LANCZOS)
        name = "c_tf%02d_ay%02d" % (int(tf * 100), int(ay * 100))
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, tf, ay, r, sm))
        print("渲染", name)

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 12)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 240
    sheet = Image.new("RGB", (len(made) * (S2 + 14) + 14, S2 + 96), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "圆形版：脸放大后仍保住耳朵", font=FB, fill=(255, 255, 255))
    for i, (name, tf, ay, r, im) in enumerate(made):
        x = 14 + i * (S2 + 14)
        ic = im.resize((S2, S2), Image.LANCZOS)
        sheet.paste(ic, (x, 44), ic)
        d.text((x + 2, 44 + S2 + 4), name, font=F, fill=(230, 236, 248))
        d.text((x + 2, 44 + S2 + 22), "耳保留 %.3f" % r, font=F, fill=(255, 200, 90))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
