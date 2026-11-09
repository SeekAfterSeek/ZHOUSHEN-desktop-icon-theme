# -*- coding: utf-8 -*-
"""Plan B / Plan C 渲染器
   B：圆角方形为主（少量圆形）
   C：圆形为主（少量圆角方形）
   其余视觉规范与 v11 一致
"""
import sys, io, os, json, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from facedet import detect_face
from grade_lib import grade

ROOT = HERE
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))

S = 512
BADGE = int(S * 0.360)
PAD_B = int(S * 0.022)
TARGET_FACE = 0.46

ACCENT = {"微信": "#3EB575", "QQ音乐": "#F5C542", "哔哩哔哩": "#FF7FA5",
    "Google Chrome": "#E8B33C", "个人 - Edge": "#3FA9F5", "360安全浏览器": "#57C46B",
    "Visual Studio Code": "#2F8FE0", "Cursor": "#5A5A5A", "DeepSeek Harness": "#A8B8C8",
    "Cherry Studio": "#E05555", "WorkBuddy": "#4FC3B5", "WPS Office": "#D94B3A",
    "全能录屏助手": "#8A4038", "剪映专业版": "#5A5A5A", "百度网盘": "#7FB8E8",
    "飞书": "#4FB6E0", "Clash Verge": "#B07AE0", "PyCharm 2026.2.3": "#3E845F",
    "ToDesk": "#8FC4E8", "互传": "#7FB0E0", "网易邮箱大师": "#D9534F",
    "联想电脑管家": "#4A7FD9", "腾讯QQ": "#7F5547", "腾讯会议": "#4A85D9"}

ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

# 形状分布：B 以方为主、C 以圆为主
CIRCLE_B = {"QQ音乐", "哔哩哔哩", "WorkBuddy", "网易邮箱大师", "Clash Verge"}
CIRCLE_C = set(ORDER) - {"Google Chrome", "Cursor", "Visual Studio Code",
                         "PyCharm 2026.2.3", "联想电脑管家"}


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
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    return ((r > 0.34) & (g > 0.14) & (b > 0.06) & (r > g) & (r > b)
            & ((mx - mn) > 0.05) & ((r - g) > 0.05) & ((r - b) > 0.08))


def head_protect(S_, d, grow=1.55):
    yy, xx = np.mgrid[0:S_, 0:S_]
    rh = max(d["fh"] * S_ * grow * 0.72, S_ * 0.13)
    rw = max(d["fw"] * S_ * grow * 0.60, S_ * 0.11)
    cx = d["fx"] * S_
    cy = d["fy"] * S_ - rh * 0.18
    return ((xx - cx) / rw) ** 2 + ((yy - cy) / rh) ** 2 <= 1.0


def render(name, info, seed, shape):
    accent = ACCENT.get(name, "#8899AA")
    ar = hexrgb(accent)
    rnd = random.Random(seed)

    im = Image.open(info["path"]).convert("RGB")
    W, H = im.size
    d = detect_face(im) or {"fx": .5, "fy": .32, "fw": .22, "fh": .22}

    face_h_px = max(8.0, d["fh"] * H)
    crop = max(min(face_h_px / TARGET_FACE, min(W, H)), S * 1.0)
    sc = S / crop
    nw, nh = max(S, int(round(W * sc))), max(S, int(round(H * sc)))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    cx, cy = d["fx"] * nw, d["fy"] * nh
    left = max(0, min(int(round(cx - S * .50)), nw - S))
    top = max(0, min(int(round(cy - S * .42)), nh - S))
    cv = im2.crop((left, top, left + S, top + S))

    arr = np.asarray(cv, dtype=np.float32) / 255.0
    dx = (d["fx"] * nw - left) / S
    dy = (d["fy"] * nh - top) / S
    dh = {"fx": dx, "fy": dy, "fw": d["fw"] * nw / S, "fh": d["fh"] * nh / S}
    protect = skin_mask_of(arr) | head_protect(S, dh)
    arr2 = grade(arr, PAL[name], skin_mask=protect, strength=0.72)
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
                  .point(lambda v: int(v * .40)))
    cv = Image.alpha_composite(glow, cv)

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
    small = cv.resize((256, 256), Image.LANCZOS)
    return cv, small


F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)

for tag, asg_file, circles in (("B", "planB_assign.json", CIRCLE_B),
                               ("C", "planC_assign.json", CIRCLE_C)):
    A = json.load(open(os.path.join(ROOT, asg_file), encoding="utf-8"))
    dest = os.path.join(ROOT, "plan%s" % tag)
    os.makedirs(os.path.join(dest, "icons"), exist_ok=True)
    imgs = {}
    for i, n in enumerate(ORDER):
        if n not in A:
            continue
        shape = "circle" if n in circles else "squircle"
        big, small = render(n, A[n], 6000 + i * 71, shape)
        big.save(os.path.join(dest, "icons", n + ".png"))
        small.save(os.path.join(dest, n + ".png"))
        imgs[n] = small
    print("Plan %s rendered %d" % (tag, len(imgs)))

    cell, cols = 200, 6
    rows = (len(ORDER) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 32) + 56), (26, 26, 34))
    dr = ImageDraw.Draw(sheet)
    dr.text((16, 14), "Plan %s · 周深桌面图标" % tag, font=FB, fill=(255, 255, 255))
    dr.text((16, 40),
            "全部照片均未在任何历史版本中出现过 ｜ 形状：%s ｜ 评分标准与第四版一致"
            % ("以圆形为主" if tag == "C" else "以圆角方形为主"),
            font=F, fill=(150, 200, 235))
    for i, n in enumerate(ORDER):
        if n not in imgs:
            continue
        x = (i % cols) * cell
        y = 62 + (i // cols) * (cell + 32)
        ic = imgs[n].resize((172, 172), Image.LANCZOS)
        sheet.paste(ic, (x + 14, y), ic)
        bb = dr.textbbox((0, 0), n, font=F)
        dr.text((x + (cell - (bb[2] - bb[0])) // 2, y + 176), n, font=F, fill=(232, 238, 250))
    sheet.save(os.path.join(dest, "preview_plan%s.png" % tag))
    print("  ->", os.path.join(dest, "preview_plan%s.png" % tag))
