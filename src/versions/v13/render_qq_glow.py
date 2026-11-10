# -*- coding: utf-8 -*-
"""腾讯QQ：白色描边 → 白色柔光（外发光），与壁纸融合

对比档位：
  g1 纯外发光
  g2 外发光 + 内侧极细高光
  g3 更宽更淡的外发光
并在深/浅两种背景上合成，检验融合度
"""
import sys
import io
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
import render_p20 as RP
import render_qq_circle2 as C2
import render_ear_circle4 as E4

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qq_glow")
os.makedirs(OUT, exist_ok=True)
S = RP.S
TF, AY = 0.40, 0.52


def build_mask():
    crop = C2.crop_at(TF, AY)
    ear = E4.ear_mask_of(crop, smin=112, ymax=0.45)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))
    ear = cv2.dilate(ear, k)
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (0.5 - 0.455), S * (0.545 - 0.455), S * (0.5 + 0.455), S * (0.545 + 0.455)],
        fill=255)
    m = Image.fromarray(np.maximum(np.asarray(base), (ear * 255)).astype(np.uint8))
    m = m.filter(ImageFilter.GaussianBlur(5)).point(lambda v: 255 if v > 111 else 0)
    m = m.filter(ImageFilter.GaussianBlur(1.6))
    # 按宽度铺满（圆宽 0.93）
    bbox = m.getbbox()
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    sc = (S * 0.93) / w
    nw, nh = int(round(w * sc)), int(round(h * sc))
    msub = m.crop(bbox).resize((nw, nh), Image.LANCZOS)
    mask = Image.new("L", (S, S), 0)
    mask.paste(msub, ((S - nw) // 2, S - nh))
    return crop, mask, bbox, sc


def render(crop, mask, bbox, sc, seed=1,
           glow_alpha=130, glow_blur=0.030, glow_grow=1.010,
           hairline=0, hairline_alpha=0, content_scale=1.0):
    ar = RP.hexrgb(C2.ACCENT)
    rnd = random.Random(seed)
    photo = crop.convert("RGBA")
    photo = ImageEnhance.Brightness(photo).enhance(1.06)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    photo = ImageEnhance.Color(photo).enhance(1.06)

    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    nw, nh = int(round(w * sc)), int(round(h * sc))
    sub = photo.crop(bbox).resize((nw, nh), Image.LANCZOS)
    msub = mask.crop(bbox).resize((nw, nh), Image.LANCZOS)
    px, py = (S - nw) // 2, S - nh

    # 完整画布上重建遮罩，再贴照片
    mask_full = Image.new("L", (S, S), 0)
    mask_full.paste(msub, (px, py))
    mask = mask_full
    cv = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cv.paste(sub, (px, py), msub)

    # 内容整体缩放留边，让柔光有空间不被画布截断
    if content_scale < 1.0:
        def _shrink(img, k):
            w0, h0 = img.size
            nw0, nh0 = int(w0 * k), int(h0 * k)
            r0 = img.resize((nw0, nh0), Image.LANCZOS)
            mode = r0.mode
            base = Image.new(mode, (w0, h0), 0 if mode == "L" else (0, 0, 0, 0))
            base.paste(r0, ((w0 - nw0) // 2, (h0 - nh0) // 2))
            return base
        cv = _shrink(cv, content_scale)
        mask = _shrink(mask, content_scale).convert("L")

    # ---- 白色柔光（外发光）：贴近轮廓，限制扩散范围 ----
    # glow_grow 是比例（1.010 = 向外扩 1%），不能乘 10，否则遮罩会被撑满画布
    grow = max(1, int(S * (glow_grow - 1.0)))
    glow_mask = mask.filter(ImageFilter.MaxFilter(grow * 2 + 1)) if grow > 0 else mask
    glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(int(S * glow_blur)))
    # 关键：截断远端微弱值，避免整张画布泛白
    CUT = 30

    def _sh(v):
        if v <= CUT:
            return 0
        return int(min(255, (v - CUT) / (255.0 - CUT) * glow_alpha))
    glow = Image.new("RGBA", (S, S), (255, 255, 255, 0))
    glow.putalpha(glow_mask.point(_sh))
    out = Image.alpha_composite(glow, cv)

    # ---- 可选：内侧极细高光，给边缘一点存在感 ----
    if hairline > 0 and hairline_alpha > 0:
        wpx = max(1, int(S * hairline))
        er = mask.filter(ImageFilter.MinFilter(wpx * 2 + 1))
        ring = ImageChops.subtract(mask, er).filter(ImageFilter.GaussianBlur(0.6))
        hl = Image.new("RGBA", (S, S), (255, 255, 255, 0))
        hl.putalpha(ring.point(lambda v: int(v / 255 * hairline_alpha)))
        out = Image.alpha_composite(out, hl)

    # 高光 + 星点（与其它图标一致）
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([-S * .16, -S * .20, S * .66, S * .48],
                               fill=(255, 255, 255, 24))
    hi = hi.filter(ImageFilter.GaussianBlur(int(S * .055)))
    hi.putalpha(Image.composite(hi.split()[3], Image.new("L", (S, S), 0), mask))
    out = Image.alpha_composite(out, hi)

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
    out = Image.alpha_composite(out, sp)

    # 角标
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
    out = Image.alpha_composite(out, sh)
    out.paste(bd, (bx, by), bd)
    return out


if __name__ == "__main__":
    crop, mask, bbox, sc = build_mask()
    cases = [
        ("g1", dict(glow_alpha=130, glow_blur=0.030, glow_grow=1.012, hairline=0)),
        ("g2", dict(glow_alpha=120, glow_blur=0.032, glow_grow=1.014,
                    hairline=0.008, hairline_alpha=70)),
        ("g3", dict(glow_alpha=95, glow_blur=0.045, glow_grow=1.018, hairline=0)),
    ]
    made = []
    for i, (name, kw) in enumerate(cases):
        big = render(crop, mask, bbox, sc, seed=59000 + i * 79, **kw)
        sm = big.resize((256, 256), Image.LANCZOS)
        sm.save(os.path.join(OUT, name + ".png"))
        big.save(os.path.join(OUT, "big_" + name + ".png"))
        made.append((name, sm))
        print("渲染", name)

    # 在深/浅背景上检验融合
    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 12)
    FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    S2 = 220
    bgs = [("深色壁纸", (28, 34, 52)), ("浅色壁纸", (232, 236, 242))]
    W = (len(made) + 1) * (S2 + 12) + 12
    sheet = Image.new("RGB", (W, (S2 + 40) * len(bgs) + 52), (20, 21, 29))
    d = ImageDraw.Draw(sheet)
    d.text((12, 10), "白色柔光 vs 实心描边（深/浅背景对比）", font=FB, fill=(255, 255, 255))
    solid = Image.open(os.path.join(ROOT, "_qq_ring_alpha", "ra175.png")).convert("RGBA")
    for bi, (bn, col) in enumerate(bgs):
        y = 44 + bi * (S2 + 40)
        tile = Image.new("RGBA", (S2, S2), col + (255,))
        tile.alpha_composite(solid.resize((S2, S2), Image.LANCZOS))
        sheet.paste(tile.convert("RGB"), (12, y))
        d.text((14, y + S2 + 3), "实心描边", font=F,
               fill=(255, 255, 255) if sum(col) < 380 else (30, 30, 30))
        for i, (name, sm) in enumerate(made):
            x = 12 + (i + 1) * (S2 + 12)
            tile = Image.new("RGBA", (S2, S2), col + (255,))
            tile.alpha_composite(sm.resize((S2, S2), Image.LANCZOS))
            sheet.paste(tile.convert("RGB"), (x, y))
            d.text((x + 2, y + S2 + 3), name, font=F,
                   fill=(255, 255, 255) if sum(col) < 380 else (30, 30, 30))
        # 背景标签
        d.text((12, y - 16), bn, font=F, fill=(150, 200, 235))
    sheet.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
