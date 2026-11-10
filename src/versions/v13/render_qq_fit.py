# -*- coding: utf-8 -*-
"""按目标直径直接定位圆形（不再用包围盒适配）

目标：圆的底部与画布底边相切（成完整弧线，不被切平），
      圆径可精确指定，耳朵从顶部探出、按需裁剪。
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
import render_qq_softear as SE

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qq_fit")
os.makedirs(OUT, exist_ok=True)
S = RP.S
TF, AY = 0.40, 0.52
CY, CR = 0.545, 0.455          # 圆在遮罩坐标系中的圆心y与半径（比例）


def build_mask(crop):
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (.5 - CR), S * (CY - CR), S * (.5 + CR), S * (CY + CR)], fill=255)
    ear = SE.soft_ear_alpha(crop, ymax=0.42, blur=7)
    return Image.fromarray(np.maximum(np.asarray(base),
                                      (ear * 255).astype(np.uint8)).astype(np.uint8))


def render(crop, mask, D=0.97, seed=1, glow_alpha=115, glow_blur=0.020):
    """D: 目标圆直径（占画布比例）"""
    ar = RP.hexrgb(C2.ACCENT)
    rnd = random.Random(seed)
    photo = crop.convert("RGBA")
    photo = ImageEnhance.Brightness(photo).enhance(1.06)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.06)

    s = D / (2 * CR)                       # 缩放系数
    nw = int(round(S * s))
    ph = photo.resize((nw, nw), Image.LANCZOS)
    mh = mask.resize((nw, nw), Image.LANCZOS)

    # 圆心目标位置：水平居中、底部与画布相切
    cx_t, cy_t = S / 2.0, S - D * S / 2.0
    cx_s, cy_s = S * 0.5 * s, S * CY * s
    ox, oy = int(round(cx_t - cx_s)), int(round(cy_t - cy_s))

    canvas_p = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    canvas_p.paste(ph, (ox, oy))
    canvas_m = Image.new("L", (S, S), 0)
    canvas_m.paste(mh, (ox, oy))
    mask = canvas_m

    cv = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cv.paste(canvas_p, (0, 0), mask)

    glow_m = mask.filter(ImageFilter.GaussianBlur(int(S * glow_blur)))
    CUT = 30

    def _g(v):
        if v <= CUT:
            return 0
        return int(min(255, (v - CUT) / (255.0 - CUT) * glow_alpha))
    glow = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    glow.putalpha(glow_m.point(_g))
    cv = Image.alpha_composite(glow, cv)

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
    return cv


if __name__ == "__main__":
    crop = C2.crop_at(TF, AY)
    m = build_mask(crop)
    made = []
    for i, D in enumerate([0.95, 0.97, 0.99, 1.00]):
        big = render(crop, m, D=D, seed=70000 + i * 137)
        sm = big.resize((256, 256), Image.LANCZOS)
        n = "D%d" % int(D * 100)
        sm.save(os.path.join(OUT, n + ".png"))
        big.save(os.path.join(OUT, "big_" + n + ".png"))
        a = np.asarray(sm)[:, :, 3]
        ys, xs = np.where(a > 200)
        mid = (ys.min() + ys.max()) // 2
        row = np.where(a[mid] > 200)[0]
        bot = np.where(a[255] > 200)[0]
        print("%s 圆宽%.3f 底行宽%.3f 总高%.3f 顶被裁=%s" % (
            n, (row.max() - row.min() + 1) / 256,
            (bot.max() - bot.min() + 1) / 256 if len(bot) else 0,
            (ys.max() - ys.min() + 1) / 256, (a[0] > 200).any()))
        made.append((n, sm))

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    Z = 240
    sh = Image.new("RGB", (len(made) * (Z + 12) + 12, Z + 80), (20, 21, 29))
    d = ImageDraw.Draw(sh)
    d.text((12, 10), "底弧 + 逐步放大（D=直径占画布比例）",
           font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16), fill=(255, 255, 255))
    for i, (n, im) in enumerate(made):
        x = 12 + i * (Z + 12)
        bg = Image.new("RGBA", (Z, Z), (226, 220, 238, 255))
        bg.alpha_composite(im.resize((Z, Z), Image.LANCZOS))
        sh.paste(bg.convert("RGB"), (x, 40))
        d.text((x + 2, 40 + Z + 4), n, font=F, fill=(230, 236, 248))
    sh.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
