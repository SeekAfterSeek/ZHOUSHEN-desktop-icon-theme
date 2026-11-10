# -*- coding: utf-8 -*-
"""圆形 + 耳轮廓 合并版，脸大小沿用 tf=0.40

对 tf=0.40 的裁切重新检测耳朵区域（肤色饱和低，用高饱和阈值区分毛色）
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
import render_qq_circle2 as C2

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qq_earcircle")
os.makedirs(OUT, exist_ok=True)
S = RP.S
TF = 0.40
AY = 0.52


def ear_mask_of(crop, smin=115, ymax=0.45):
    a = np.asarray(crop)
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    m = ((h >= 4) & (h <= 30) & (s >= smin) & (v >= 90)).astype(np.uint8)
    m[int(S * ymax):, :] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    return m


def build_mask(crop, cy, r, dilate, smin, ymax, blur, thr):
    ear = ear_mask_of(crop, smin=smin, ymax=ymax)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1,) * 2)
    ear = cv2.dilate(ear, k)
    ear_img = Image.fromarray((ear * 255).astype(np.uint8))
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (0.5 - r), S * (cy - r), S * (0.5 + r), S * (cy + r)], fill=255)
    m = Image.fromarray(np.maximum(np.asarray(base), np.asarray(ear_img)).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    m = m.point(lambda v: 255 if v > thr else 0)
    return m.filter(ImageFilter.GaussianBlur(1.6))


def render(mask, seed=1):
    ar = RP.hexrgb(C2.ACCENT)
    import random
    rnd = random.Random(seed)
    crop = C2.crop_at(TF, AY)
    cv = crop.convert("RGBA")
    cv = ImageEnhance.Brightness(cv).enhance(1.06)
    cv = ImageEnhance.Contrast(cv).enhance(1.08)
    cv = ImageEnhance.Color(cv).enhance(1.06)

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
    logo = Image.open(C2.QP).convert("RGBA")
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
    crop = C2.crop_at(TF, AY)
    crop.save(os.path.join(OUT, "crop40.png"))
    em = ear_mask_of(crop)
    Image.fromarray((em * 255)).save(os.path.join(OUT, "ears40.png"))
    ys = np.where(em.any(axis=1))[0]
    xs = np.where(em.any(axis=0))[0]
    print("tf=0.40 耳朵区域: y[%d..%d] x[%d..%d] 占比 y%.2f-%.2f x%.2f-%.2f" % (
        ys.min(), ys.max(), xs.min(), xs.max(),
        ys.min() / S, ys.max() / S, xs.min() / S, xs.max() / S))

    variants = [
        ("ec1", dict(cy=0.60, r=0.395, dilate=10, smin=115, ymax=0.45, blur=7, thr=110)),
        ("ec2", dict(cy=0.61, r=0.385, dilate=14, smin=110, ymax=0.46, blur=8, thr=108)),
        ("ec3", dict(cy=0.615, r=0.375, dilate=8, smin=120, ymax=0.44, blur=6, thr=112)),
    ]
    made = []
    for i, (name, kw) in enumerate(variants):
        msk = build_mask(crop, **kw)
        msk.save(os.path.join(OUT, name + "_mask.png"))
        big = render(msk, seed=51000 + i * 47)
        sm = big.resize((256, 256), Image.LANCZOS)
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, sm))
        print("渲染", name)

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 250
    sheet = Image.new("RGB", ((len(made) + 1) * (S2 + 14) + 14, S2 + 92), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "圆形+耳轮廓（脸 tf=0.40）", font=FB, fill=(255, 255, 255))
    sheet.paste(crop.resize((S2, S2), Image.LANCZOS), (14, 44))
    d.text((16, 44 + S2 + 4), "裁切(脸40%)", font=F, fill=(120, 220, 255))
    for i, (name, im) in enumerate(made):
        x = 14 + (i + 1) * (S2 + 14)
        ic = im.resize((S2, S2), Image.LANCZOS)
        sheet.paste(ic, (x, 44), ic)
        d.text((x + 2, 44 + S2 + 4), name, font=F, fill=(230, 236, 248))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
