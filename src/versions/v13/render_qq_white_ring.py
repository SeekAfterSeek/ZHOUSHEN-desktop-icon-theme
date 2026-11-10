# -*- coding: utf-8 -*-
"""1) 腾讯QQ：沿轮廓加白色描边（参考 QQ音乐 金边的做法，改在轮廓内侧）
   2) Clash Verge：人脸占比放大，同时确认兔耳不被裁
"""
import sys
import io
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
from facedet import detect_face
import render_p20 as RP
import render_qq_circle2 as C2

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
OUT = os.path.join(ROOT, "_qq_white_ring")
os.makedirs(OUT, exist_ok=True)
S = RP.S


def inner_ring(mask, width_px):
    """轮廓内侧的环带"""
    er = mask.filter(ImageFilter.MinFilter(width_px * 2 + 1))
    return ImageChops.subtract(mask, er)


def render_qq_white(seed=1, ring_ratio=0.024, ring_alpha=245, fill=1.0):
    """fill: 保留耳尖探出的裁切比例（1.0 = 用 v4c 的原始布局）"""
    import render_ear_circle4 as E4
    ar = RP.hexrgb(C2.ACCENT)
    rnd = random.Random(seed)
    crop = C2.crop_at(0.40, 0.52)
    photo = crop.convert("RGBA")
    photo = ImageEnhance.Brightness(photo).enhance(1.06)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.06)

    # 复用 v4c 的遮罩，再按宽度铺满（圆宽 0.93）
    ear = E4.ear_mask_of(crop, smin=112, ymax=0.45)
    import cv2
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))
    ear = cv2.dilate(ear, k)
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (0.5 - 0.455), S * (0.545 - 0.455), S * (0.5 + 0.455), S * (0.545 + 0.455)],
        fill=255)
    m = Image.fromarray(np.maximum(np.asarray(base), (ear * 255)).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: 255 if v > 111 else 0)
    m = m.filter(ImageFilter.GaussianBlur(1.6))

    # 按宽度铺满（与 v4c 一致）
    bbox = m.getbbox()
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    sc = (S * 0.93) / w
    nw, nh = int(round(w * sc)), int(round(h * sc))
    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    p2 = photo.resize((int(photo.width * sc * (S / photo.width)), S), Image.LANCZOS)
    sub = photo.crop(bbox).resize((nw, nh), Image.LANCZOS)
    msub = m.crop(bbox).resize((nw, nh), Image.LANCZOS)
    px, py = (S - nw) // 2, S - nh
    cv = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cv.paste(sub, (px, py))
    mask = Image.new("L", (S, S), 0)
    mask.paste(msub, (px, py))

    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(cv, (0, 0), mask)
    cv = cut

    glow = Image.new("RGBA", (S, S), ar + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .030)))
                  .point(lambda v: int(v * .40)))
    cv = Image.alpha_composite(glow, cv)

    # 白色描边（内侧环带）
    wpx = max(3, int(S * ring_ratio))
    ring = inner_ring(mask, wpx)
    ring_soft = ring.filter(ImageFilter.GaussianBlur(0.8))
    wr = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    wr.putalpha(ring_soft.point(lambda v: int(v / 255 * ring_alpha)))
    cv = Image.alpha_composite(cv, wr)

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
    made = []
    for i, (rr, ra) in enumerate([(0.018, 245), (0.024, 245), (0.030, 245)]):
        big = render_qq_white(seed=57000 + i * 71, ring_ratio=rr, ring_alpha=ra)
        sm = big.resize((256, 256), Image.LANCZOS)
        name = "ring%d" % int(rr * 1000)
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, sm))
        print("渲染", name)

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 250
    ref = Image.open(os.path.join(ROOT, "design_v12", "QQ音乐.png")).convert("RGBA")
    sheet = Image.new("RGB", ((len(made) + 1) * (S2 + 14) + 14, S2 + 100), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((14, 10), "腾讯QQ 白描边（最左=QQ音乐 金边参照）", font=FB, fill=(255, 255, 255))
    bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
    bg.alpha_composite(ref.resize((S2, S2), Image.LANCZOS))
    sheet.paste(bg.convert("RGB"), (14, 44))
    d.text((16, 44 + S2 + 4), "QQ音乐 金边", font=F, fill=(255, 220, 120))
    for i, (name, im) in enumerate(made):
        x = 14 + (i + 1) * (S2 + 14)
        bg = Image.new("RGBA", (S2, S2), (32, 32, 32, 255))
        bg.alpha_composite(im.resize((S2, S2), Image.LANCZOS))
        sheet.paste(bg.convert("RGB"), (x, 44))
        d.text((x + 2, 44 + S2 + 4), name, font=F, fill=(230, 236, 248))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
