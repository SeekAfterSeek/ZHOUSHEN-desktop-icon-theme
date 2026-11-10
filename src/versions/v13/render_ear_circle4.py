# -*- coding: utf-8 -*-
"""圆形+耳尖探出 v4

思路修正：上一版圆太小，是因为「整只耳朵都在圆外面」。
本版把圆放大到接近铺满（r≈0.45），耳朵主体落在圆内，
只有耳尖从圆的顶部探出 —— 既保住耳朵，圆也不变小。
"""
import sys
import io
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import render_p20 as RP
import render_qq_circle2 as C2
from render_ear_circle import ear_mask_of

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qq_earcircle4")
os.makedirs(OUT, exist_ok=True)
S = RP.S
TF, AY = 0.40, 0.52


def build(crop, cy, r, dilate, smin, ymax, blur, thr):
    ear = ear_mask_of(crop, smin=smin, ymax=ymax)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1,) * 2)
    ear = cv2.dilate(ear, k)
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (0.5 - r), S * (cy - r), S * (0.5 + r), S * (cy + r)], fill=255)
    m = Image.fromarray(np.maximum(np.asarray(base), (ear * 255)).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    m = m.point(lambda v: 255 if v > thr else 0)
    return m.filter(ImageFilter.GaussianBlur(1.6))


def render(mask, seed=1):
    ar = RP.hexrgb(C2.ACCENT)
    rnd = random.Random(seed)
    crop = C2.crop_at(TF, AY)
    photo = crop.convert("RGBA")
    photo = ImageEnhance.Brightness(photo).enhance(1.06)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.06)

    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(photo, (0, 0), mask)
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
    cases = [
        ("v4a", dict(cy=0.552, r=0.448, dilate=12, smin=110, ymax=0.46, blur=6, thr=110)),
        ("v4b", dict(cy=0.560, r=0.440, dilate=16, smin=108, ymax=0.46, blur=7, thr=108)),
        ("v4c", dict(cy=0.545, r=0.455, dilate=9, smin=112, ymax=0.45, blur=5, thr=111)),
    ]
    made = []
    for i, (name, kw) in enumerate(cases):
        msk = build(crop, **kw)
        msk.save(os.path.join(OUT, name + "_mask.png"))
        big = render(msk, seed=56000 + i * 67)
        sm = big.resize((256, 256), Image.LANCZOS)
        a = np.asarray(sm)[:, :, 3]
        ys, xs = np.where(a > 20)
        cw, ch = (xs.max() - xs.min()) / 256, (ys.max() - ys.min()) / 256
        # 圆的实际宽度：取中段一行的宽度
        mid = (ys.min() + ys.max()) // 2
        row = np.where(a[mid] > 20)[0]
        cw_mid = (row.max() - row.min()) / 256 if len(row) else 0
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, sm, cw, ch, cw_mid))
        print("渲染 %s  总 %.2f×%.2f  圆宽 %.2f" % (name, cw, ch, cw_mid))

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 250
    ref = Image.open(os.path.join(ROOT, "_qq_circle2", "c_tf40_ay52.png")).convert("RGBA")
    sheet = Image.new("RGB", ((len(made) + 1) * (S2 + 14) + 14, S2 + 104), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "圆放大 + 耳尖探出（最左=纯圆对照）", font=FB, fill=(255, 255, 255))
    bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
    bg.alpha_composite(ref.resize((S2, S2), Image.LANCZOS))
    sheet.paste(bg.convert("RGB"), (14, 44))
    d.text((16, 44 + S2 + 4), "纯圆 圆宽0.97", font=F, fill=(120, 220, 255))
    for i, (name, im, cw, ch, cwm) in enumerate(made):
        x = 14 + (i + 1) * (S2 + 14)
        bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
        bg.alpha_composite(im.resize((S2, S2), Image.LANCZOS))
        sheet.paste(bg.convert("RGB"), (x, 44))
        d.text((x + 2, 44 + S2 + 4), "%s 圆宽%.2f" % (name, cwm), font=F,
               fill=(230, 236, 248))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
