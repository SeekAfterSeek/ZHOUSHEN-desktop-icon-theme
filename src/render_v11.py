# -*- coding: utf-8 -*-
"""第四版（v11）渲染器 v3 —— 带调色
   关键改动：照片按原图标真实配色做 HSL 调色，把配色拉向原图标
   * 保护人脸肤色
   * 黑/白倾向、色相旋转、缺失色背景补光
"""
import sys, io, os, json, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from facedet import detect_face
from grade_lib import grade, rgb2hsv

ROOT = HERE
DESIGN = os.path.join(ROOT, "design_v11")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
BIG = os.path.join(DESIGN, "icons")
os.makedirs(BIG, exist_ok=True)
S = 512
BADGE = int(S * 0.360)
PAD_B = int(S * 0.022)

ASG = json.load(open(os.path.join(DESIGN, "assign.json"), encoding="utf-8"))
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
ORDER = list(ASG)

ACCENT = {"微信": "#3EB575", "QQ音乐": "#F5C542", "哔哩哔哩": "#FF7FA5",
    "Google Chrome": "#E8B33C", "个人 - Edge": "#3FA9F5", "360安全浏览器": "#57C46B",
    "Visual Studio Code": "#2F8FE0", "Cursor": "#5A5A5A", "DeepSeek Harness": "#A8B8C8",
    "Cherry Studio": "#E05555", "WorkBuddy": "#4FC3B5", "WPS Office": "#D94B3A",
    "全能录屏助手": "#8A4038", "剪映专业版": "#5A5A5A", "百度网盘": "#7FB8E8",
    "飞书": "#4FB6E0", "Clash Verge": "#B07AE0", "PyCharm 2026.2.3": "#3E845F",
    "ToDesk": "#8FC4E8", "互传": "#7FB0E0", "网易邮箱大师": "#D9534F",
    "联想电脑管家": "#4A7FD9", "腾讯QQ": "#7F5547", "腾讯会议": "#4A85D9"}

CIRCLE = {"QQ音乐", "哔哩哔哩", "Clash Verge", "WorkBuddy", "网易邮箱大师"}
GOLD_RING = {"QQ音乐"}
TARGET_FACE = 0.46
GRADE_STR = {}          # 每个 APP 的调色强度（默认 1.0）
for _n in ORDER:
    GRADE_STR[_n] = 0.78
# 用 search_grade.py 实测的最优强度覆盖
_gs = os.path.join(DESIGN, "grade_strength.json")
if os.path.exists(_gs):
    GRADE_STR.update({k: float(v) for k, v in
                      json.load(open(_gs, encoding="utf-8")).items()})


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mask_for(shape, inset):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    if shape == "circle":
        d.ellipse([inset, inset, S - 1 - inset, S - 1 - inset], fill=255)
    else:
        d.rounded_rectangle([inset, inset, S - 1 - inset, S - 1 - inset],
                            radius=int((S - 2 * inset) * 0.268), fill=255)
    return m


def skin_mask_of(rgb):
    """皮肤 + 头发 + 五官：以检测到的人脸为中心做椭圆保护，避免把头发染色"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    m = ((r > 0.34) & (g > 0.14) & (b > 0.06) & (r > g) & (r > b)
         & ((mx - mn) > 0.05) & ((r - g) > 0.05) & ((r - b) > 0.08))
    return m


def head_protect(S_, d, grow=1.45):
    """以人脸框为中心、放大 grow 倍的椭圆 = 整个人头（含头发）"""
    yy, xx = np.mgrid[0:S_, 0:S_]
    cx = d["fx"] * S_
    cy = d["fy"] * S_
    rw = max(d["fw"] * S_ * grow * 0.60, S_ * 0.11)
    rh = max(d["fh"] * S_ * grow * 0.72, S_ * 0.13)
    # 头部中心略高于人脸框中心
    cy = cy - rh * 0.18
    e = ((xx - cx) / rw) ** 2 + ((yy - cy) / rh) ** 2
    return e <= 1.0


def render(name, info, seed):
    accent = ACCENT.get(name, "#8899AA")
    ar = hexrgb(accent)
    shape = "circle" if name in CIRCLE else "squircle"
    rnd = random.Random(seed)

    im = Image.open(info["path"]).convert("RGB")
    W, H = im.size
    d = detect_face(im) or {"fx": .5, "fy": .32, "fw": .22, "fh": .22}

    face_h_px = max(8.0, d["fh"] * H)
    crop = min(face_h_px / TARGET_FACE, min(W, H))
    crop = max(crop, S * 1.0)
    scale = S / crop
    nw, nh = max(S, int(round(W * scale))), max(S, int(round(H * scale)))
    im2 = im.resize((nw, nh), Image.LANCZOS)

    cx, cy = d["fx"] * nw, d["fy"] * nh
    left = max(0, min(int(round(cx - S * .50)), nw - S))
    top = max(0, min(int(round(cy - S * .42)), nh - S))
    cv = im2.crop((left, top, left + S, top + S))

    # ---------- 调色（核心改动）----------
    arr = np.asarray(cv, dtype=np.float32) / 255.0
    sm = skin_mask_of(arr)
    # 人头保护：人脸框在裁剪坐标里的位置
    dx = (d["fx"] * nw - left) / S
    dy = (d["fy"] * nh - top) / S
    dh = {"fx": dx, "fy": dy, "fw": d["fw"] * nw / S, "fh": d["fh"] * nh / S}
    head = head_protect(S, dh, grow=1.55)
    protect = sm | head
    arr2 = grade(arr, PAL[name], skin_mask=protect, strength=GRADE_STR.get(name, 1.0))
    cv = Image.fromarray((np.clip(arr2, 0, 1) * 255).astype(np.uint8), "RGB")

    cv = ImageEnhance.Color(cv).enhance(1.04)
    cv = ImageEnhance.Contrast(cv).enhance(1.05)
    cv = cv.convert("RGBA")

    inset = int(S * 0.016)
    mask = mask_for(shape, inset)
    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(cv, (0, 0), mask)
    cv = cut

    glow = Image.new("RGBA", (S, S), ar + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .030)))
                  .point(lambda v: int(v * (.58 if name in GOLD_RING else .40))))
    cv = Image.alpha_composite(glow, cv)

    if name in GOLD_RING:
        w = max(4, int(S * 0.028))
        ring = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        for k in range(w):
            t = k / max(1, w - 1)
            col = (255, int(206 + 34 * (1 - t)), int(70 + 120 * t))
            box = [inset + k, inset + k, S - 1 - inset - k, S - 1 - inset - k]
            if shape == "circle":
                rd.ellipse(box, outline=col + (255,), width=1)
            else:
                rd.rounded_rectangle(box, radius=int((S - 2 * inset) * .268),
                                     outline=col + (255,), width=1)
        cv = Image.alpha_composite(cv, ring)
        cv = Image.alpha_composite(cv, ring)
        halo = Image.new("RGBA", (S, S), (255, 198, 62, 0))
        halo.putalpha(mask.filter(ImageFilter.GaussianBlur(int(S * .045)))
                      .point(lambda v: int(v * .52)))
        cv = Image.alpha_composite(halo, cv)
    else:
        w = max(2, int(S * 0.010))
        edge = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ed = ImageDraw.Draw(edge)
        for k in range(w):
            a = int(205 * (1 - k / max(1, w)))
            box = [inset + k, inset + k, S - 1 - inset - k, S - 1 - inset - k]
            if shape == "circle":
                ed.ellipse(box, outline=ar + (a,), width=1)
            else:
                ed.rounded_rectangle(box, radius=int((S - 2 * inset) * .268),
                                     outline=ar + (a,), width=1)
        cv = Image.alpha_composite(cv, edge)

    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hi).ellipse([-S * .16, -S * .20, S * .66, S * .48],
                               fill=(255, 255, 255, 28))
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

    op = os.path.join(ORIG, name + ".png")
    if os.path.exists(op):
        logo = Image.open(op).convert("RGBA")
        logo.thumbnail((int(BADGE * .68),) * 2, Image.LANCZOS)
        bd = Image.new("RGBA", (BADGE, BADGE), (0, 0, 0, 0))
        ImageDraw.Draw(bd).ellipse([0, 0, BADGE - 1, BADGE - 1],
                                   fill=(255, 255, 255, 246),
                                   outline=(16, 28, 50, 205), width=max(3, int(BADGE * .030)))
        bd.paste(logo, ((BADGE - logo.width) // 2, (BADGE - logo.height) // 2), logo)
        bx = S - BADGE - PAD_B
        by = S - BADGE - PAD_B
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

    cv.save(os.path.join(BIG, name + ".png"))
    small = cv.resize((256, 256), Image.LANCZOS)
    small.save(os.path.join(DESIGN, name + ".png"))
    return small


imgs = {}
for i, n in enumerate(ORDER):
    imgs[n] = render(n, ASG[n], 4000 + i * 61)
print("rendered:", len(imgs))

F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
cell, cols = 200, 6
rows = (len(ORDER) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell, rows * (cell + 32)), (26, 26, 34))
dr = ImageDraw.Draw(sheet)
for i, n in enumerate(ORDER):
    x, y = (i % cols) * cell, (i // cols) * (cell + 32)
    ic = imgs[n].resize((172, 172), Image.LANCZOS)
    sheet.paste(ic, (x + 14, y + 6), ic)
    bb = dr.textbbox((0, 0), n, font=F)
    dr.text((x + (cell - (bb[2] - bb[0])) // 2, y + cell + 2), n, font=F, fill=(232, 238, 250))
sheet.save(os.path.join(DESIGN, "preview_v11.png"))
print("DONE")
