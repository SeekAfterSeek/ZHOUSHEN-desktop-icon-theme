# -*- coding: utf-8 -*-
"""P1-P20 图标渲染 v2

修复：
  1. 裁切框不再越界 → 彻底消除平均色补边造成的「假边框」
  2. 盾牌轮廓重做（联想电脑管家用），角标移到盾牌右上宽处，不悬空
  3. 低分辨率源图自动改用同图高清版（若存在）
"""
import sys, io, os, json, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from facedet import detect_face

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_p20_out")
os.makedirs(OUT, exist_ok=True)
ORIG_ICON = os.path.join(ROOT, "backup", "original-icons-256")

S = 512
PAD_B = int(S * 0.022)

ACCENT = {"微信": "#3EB575", "QQ音乐": "#F5C542", "哔哩哔哩": "#FF7FA5",
          "Google Chrome": "#E8B33C", "个人 - Edge": "#3FA9F5", "360安全浏览器": "#57C46B",
          "Visual Studio Code": "#2F8FE0", "Cursor": "#5A5A5A", "DeepSeek Harness": "#A8B8C8",
          "Cherry Studio": "#E05555", "WorkBuddy": "#4FC3B5", "WPS Office": "#D94B3A",
          "全能录屏助手": "#8A4038", "剪映专业版": "#5A5A5A", "百度网盘": "#7FB8E8",
          "飞书": "#4FB6E0", "Clash Verge": "#B07AE0", "PyCharm 2026.2.3": "#3E845F",
          "ToDesk": "#8FC4E8", "互传": "#7FB0E0", "网易邮箱大师": "#D9534F",
          "联想电脑管家": "#4A7FD9", "腾讯QQ": "#7F5547", "腾讯会议": "#4A85D9",
          "美团": "#FFC300"}

MAP = [
    ("P1_edge",    "个人 - Edge", False),
    ("P2_lenovo",  "联想电脑管家", True),
    ("P3_vsc",     "Visual Studio Code", False),
    ("P4_bili",    "哔哩哔哩", False),
    ("P5_wb",      "WorkBuddy", False),
    ("P6_meituan", "美团", False),
    ("P7_huchuan", "互传", False),
    ("P8_bili",    "哔哩哔哩", False),
    ("P9_bili",    "哔哩哔哩", False),
    ("P10_dsh",    "DeepSeek Harness", False),
    ("P11_dsh",    "DeepSeek Harness", False),
    ("P12_dsh",    "DeepSeek Harness", False),
    ("P13_dsh",    "DeepSeek Harness", False),
    ("P14_dsh",    "DeepSeek Harness", False),
    ("P15_wb",     "WorkBuddy", False),
    ("P16_dsh",    "DeepSeek Harness", False),
    ("P17_todesk", "ToDesk", False),
    ("P18_huchuan","互传", False),
    ("P19_todesk", "ToDesk", False),
    ("P20_qq",     "腾讯QQ", False),
]

LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
FIXED = {"P15_wb": os.path.join(LIB, "photos_2026__station_20260905_29652_1.jpg")}


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shield_mask(inset, app=None):
    """直接用原图标自身的 alpha 轮廓 —— 与管家原始图标形状完全一致"""
    if app:
        p = os.path.join(ORIG_ICON, app + ".png")
        if os.path.exists(p):
            src = Image.open(p).convert("RGBA").split()[3].resize((S, S), Image.LANCZOS)
            # 轻微腐蚀，让外发光有一圈
            er = max(3, int(S * 0.012)) * 2 + 1
            return src.filter(ImageFilter.MinFilter(er))
    # 兜底：手绘盾牌
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    x0, y0 = inset, inset
    x1, y1 = S - inset, S - inset
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2.0
    r = w * 0.075
    shoulder = y0 + h * 0.54
    pts = [(x0 + r, y0), (x1 - r, y0)]
    for i in range(9):
        a = -math.pi / 2 + (math.pi / 2) * i / 8
        pts.append((x1 - r + r * math.cos(a), y0 + r + r * math.sin(a)))
    pts.append((x1, y0 + r))
    pts.append((x1, shoulder))
    for i in range(1, 49):
        t = i / 48.0
        pts.append(((1 - t) ** 2 * x1 + 2 * (1 - t) * t * (x1 - w * 0.04) + t ** 2 * cx,
                    (1 - t) ** 2 * shoulder + 2 * (1 - t) * t * (y0 + h * 0.92) + t ** 2 * y1))
    for i in range(48, -1, -1):
        t = i / 48.0
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * (x0 + w * 0.04) + t ** 2 * cx,
                    (1 - t) ** 2 * shoulder + 2 * (1 - t) * t * (y0 + h * 0.92) + t ** 2 * y1))
    pts.append((x0, shoulder))
    pts.append((x0, y0 + r))
    for i in range(9):
        a = math.pi + (math.pi / 2) * i / 8
        pts.append((x0 + r + r * math.cos(a), y0 + r + r * math.sin(a)))
    d.polygon(pts, fill=255)
    return m


def squircle_mask(inset):
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [inset, inset, S - 1 - inset, S - 1 - inset],
        radius=int((S - 2 * inset) * 0.268), fill=255)
    return m


def crop_face(im, d, target_face, anchor_y=0.42):
    """裁切框严格不越界：过大就缩小裁切框，绝不补边"""
    W, H = im.size
    face_h = d["fh"] * H
    crop = face_h / target_face
    crop = max(S * 0.6, min(crop, float(min(W, H))))
    sc = S / crop
    nw, nh = max(S, int(round(W * sc))), max(S, int(round(H * sc)))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    cx, cy = d["fx"] * nw, d["fy"] * nh
    left = int(round(cx - S * 0.50))
    top = int(round(cy - S * anchor_y))
    left = max(0, min(left, nw - S))
    top = max(0, min(top, nh - S))
    return im2.crop((left, top, left + S, top + S)).convert("RGBA")


def render(src, app, shield=False, tf=0.46, seed=1):
    ar = hexrgb(ACCENT.get(app, "#8899AA"))
    rnd = random.Random(seed)
    im = Image.open(src).convert("RGB")
    d = detect_face(im)
    if not d:
        d = {"fx": .5, "fy": .30, "fw": .22, "fh": .22}

    cv = crop_face(im, d, tf)
    cv = ImageEnhance.Brightness(cv).enhance(1.05)
    cv = ImageEnhance.Contrast(cv).enhance(1.07)
    cv = ImageEnhance.Color(cv).enhance(1.06)
    cv = cv.convert("RGBA")

    inset = int(S * 0.016)
    mask = shield_mask(inset, app) if shield else squircle_mask(inset)
    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(cv, (0, 0), mask)
    cv = cut

    glow = Image.new("RGBA", (S, S), ar + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .030)))
                  .point(lambda v: int(v * .42)))
    cv = Image.alpha_composite(glow, cv)

    # 描边
    if shield:
        ring = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.0))
        ring = ring.point(lambda v: 255 if v > 40 else 0)
        edge = Image.new("RGBA", (S, S), ar + (230,))
        edge.putalpha(ring)
        cv = Image.alpha_composite(cv, edge)
    else:
        edge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ed = ImageDraw.Draw(edge)
        w = max(2, int(S * 0.010))
        for k in range(w):
            a = int(205 * (1 - k / max(1, w)))
            ed.rounded_rectangle([inset + k, inset + k, S - 1 - inset - k, S - 1 - inset - k],
                                 radius=int((S - 2 * inset) * .268),
                                 outline=ar + (a,), width=1)
        cv = Image.alpha_composite(cv, edge)

    # 高光
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([-S * .16, -S * .20, S * .66, S * .48],
                               fill=(255, 255, 255, 24))
    hi = hi.filter(ImageFilter.GaussianBlur(int(S * .055)))
    hi.putalpha(Image.composite(hi.split()[3], Image.new("L", (S, S), 0), mask))
    cv = Image.alpha_composite(cv, hi)

    # 星点
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

    # 角标
    op = os.path.join(ORIG_ICON, app + ".png")
    if os.path.exists(op):
        if shield:
            BD = int(S * 0.265)
            bx = int(S * 0.735 - BD / 2)
            by = int(S * 0.135 - BD / 2) + int(S*0.02)
        else:
            BD = int(S * 0.360)
            bx = S - BD - PAD_B
            by = S - BD - PAD_B
        logo = Image.open(op).convert("RGBA")
        logo.thumbnail((int(BD * .68),) * 2, Image.LANCZOS)
        bd = Image.new("RGBA", (BD, BD), (0, 0, 0, 0))
        ImageDraw.Draw(bd).ellipse([0, 0, BD - 1, BD - 1],
                                   fill=(255, 255, 255, 246),
                                   outline=(16, 28, 50, 205), width=max(3, int(BD * .030)))
        bd.paste(logo, ((BD - logo.width) // 2, (BD - logo.height) // 2), logo)
        sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", bd.size, (0, 0, 0, 115)),
                 (bx + int(S * .006), by + int(S * .011)), bd.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(int(S * .010)))
        cv = Image.alpha_composite(cv, sh)
        cv.paste(bd, (bx, by), bd)

    soft = mask.filter(ImageFilter.GaussianBlur(int(S * .014))).point(lambda v: min(255, v * 2))
    cv.putalpha(Image.composite(cv.split()[3],
                                Image.eval(soft, lambda v: int(v * .5)),
                                Image.eval(mask, lambda v: 255 if v > 200 else 0)))
    return cv


def main():
    D = json.load(open(os.path.join(ROOT, "_shot_final3.json"), encoding="utf-8"))
    # 高清替代（若存在）
    hires = {}
    hp = os.path.join(ROOT, "_hires_map.json")
    if os.path.exists(hp):
        hires = json.load(open(hp, encoding="utf-8"))

    made = []
    for i, (key, app, shield) in enumerate(MAP):
        if key in FIXED:
            p = os.path.abspath(FIXED[key])
        else:
            p = D[key]["top"][0]["path"]
        if key in hires and os.path.exists(hires[key]):
            p = hires[key]
        if not os.path.exists(p):
            print("缺文件", key); continue
        big = render(p, app, shield=shield, tf=0.46, seed=20000 + i * 7)
        sm = big.resize((256, 256), Image.LANCZOS)
        fn = "%s_%s.png" % (key, app.replace(" ", "").replace("-", ""))
        sm.save(os.path.join(OUT, fn))
        big.save(os.path.join(OUT, "big_" + fn))
        made.append({"key": key, "app": app, "file": fn, "src": p,
                     "corr": (D[key]["top"][0]["corr"] if key not in FIXED else 0.972),
                     "shield": shield})
        print("%-12s -> %-20s %s" % (key, app, os.path.basename(p)[:46]))

    json.dump(made, open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n共 %d 个 -> %s" % (len(made), OUT))


if __name__ == "__main__":
    main()
