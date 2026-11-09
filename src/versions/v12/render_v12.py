# -*- coding: utf-8 -*-
"""第十二版（v12）：混搭 + 全部方形

规则：
  1. 指定的 12 个 APP 换成 Plan C 的照片
  2. 其余 12 个保持 v11 的照片不变
  3. 形状：全部圆角方形
  4. 唯一例外：QQ音乐保留圆形 + 第一版黄色圆边
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
OUT = os.path.join(ROOT, "design_v12")
os.makedirs(os.path.join(OUT, "icons"), exist_ok=True)
ORIG = os.path.join(ROOT, "backup", "original-icons-256")

V11 = json.load(open(os.path.join(ROOT, "design_v11", "assign.json"), encoding="utf-8"))
PLANC = json.load(open(os.path.join(ROOT, "planC_assign.json"), encoding="utf-8"))
PLANB = json.load(open(os.path.join(ROOT, "planB_assign.json"), encoding="utf-8"))
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))}

ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

# 这 12 个换成 Plan C
SWITCH_TO_C = {
    "PyCharm 2026.2.3", "哔哩哔哩", "互传", "飞书", "腾讯QQ",
    "个人 - Edge", "腾讯会议", "联想电脑管家",
    "Visual Studio Code", "剪映专业版",
}
# 这 2 个换成 Plan B
SWITCH_TO_B = {"DeepSeek Harness", "ToDesk"}

# 这 2 个手工指定（原图标都是亮蓝+白，要背景亮蓝、衣服白/浅、表情生动）
MANUAL = {
    "腾讯会议":     "c929b_90b313ea59.png",     # 浅蓝衬衫+亮蓝背景+开怀大笑
    "联想电脑管家": "station_20260923_47687_2.jpg",  # 蓝色亮片西装，脸 650px
}

ACCENT = {"微信": "#3EB575", "QQ音乐": "#F5C542", "哔哩哔哩": "#FF7FA5",
    "Google Chrome": "#E8B33C", "个人 - Edge": "#3FA9F5", "360安全浏览器": "#57C46B",
    "Visual Studio Code": "#2F8FE0", "Cursor": "#5A5A5A", "DeepSeek Harness": "#A8B8C8",
    "Cherry Studio": "#E05555", "WorkBuddy": "#4FC3B5", "WPS Office": "#D94B3A",
    "全能录屏助手": "#8A4038", "剪映专业版": "#5A5A5A", "百度网盘": "#7FB8E8",
    "飞书": "#4FB6E0", "Clash Verge": "#B07AE0", "PyCharm 2026.2.3": "#3E845F",
    "ToDesk": "#8FC4E8", "互传": "#7FB0E0", "网易邮箱大师": "#D9534F",
    "联想电脑管家": "#4A7FD9", "腾讯QQ": "#7F5547", "腾讯会议": "#4A85D9"}

S = 512
BADGE = int(S * 0.360)
PAD_B = int(S * 0.022)
TARGET_FACE = 0.46

# 只有这两项保留圆形：QQ音乐（同时保留金边）、Clash Verge
CIRCLE_ONLY = {"QQ音乐", "Clash Verge"}
GOLD_RING = {"QQ音乐"}
# 调色强度沿用 v11 的自动搜索结果
_v11_strength_path = os.path.join(ROOT, "design_v11", "grade_strength.json")
GRADE_STR = {}
if os.path.exists(_v11_strength_path):
    GRADE_STR = {k: float(v) for k, v in
                 json.load(open(_v11_strength_path, encoding="utf-8")).items()}
for n in ORDER:
    GRADE_STR.setdefault(n, 0.72)


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


def render(name, info, seed):
    accent = ACCENT.get(name, "#8899AA")
    ar = hexrgb(accent)
    shape = "circle" if name in CIRCLE_ONLY else "squircle"
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

    # 调色（保护人头）
    arr = np.asarray(cv, dtype=np.float32) / 255.0
    dx = (d["fx"] * nw - left) / S
    dy = (d["fy"] * nh - top) / S
    dh = {"fx": dx, "fy": dy, "fw": d["fw"] * nw / S, "fh": d["fh"] * nh / S}
    protect = skin_mask_of(arr) | head_protect(S, dh)
    arr2 = grade(arr, PAL[name], skin_mask=protect, strength=GRADE_STR.get(name, 0.72))
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

    cv.save(os.path.join(OUT, "icons", name + ".png"))
    small = cv.resize((256, 256), Image.LANCZOS)
    small.save(os.path.join(OUT, name + ".png"))
    return small


# ---- 组装分配 ----
assign = {}
for n in ORDER:
    if n in MANUAL:
        src, tag = PF[MANUAL[n]], "new"
    elif n in SWITCH_TO_B:
        src, tag = PLANB[n], "PlanB"
    elif n in SWITCH_TO_C:
        src, tag = PLANC[n], "PlanC"
    else:
        src, tag = V11[n], "v11"
    assign[n] = dict(src)
    assign[n]["from"] = tag

json.dump(assign, open(os.path.join(OUT, "assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("=== 第十二版分配 ===")
imgs = {}
for i, n in enumerate(ORDER):
    imgs[n] = render(n, assign[n], 7000 + i * 83)
    shape = "圆形" if n in CIRCLE_ONLY else "方形"
    tag = assign[n]["from"]
    print("  %-20s %-6s %-6s %s" % (n, tag, shape, assign[n]["file"]))

print("\nrendered:", len(imgs))

# 总览
F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
FB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 22)
cell, cols = 200, 6
rows = (len(ORDER) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell, rows * (cell + 32) + 60), (26, 26, 34))
dr = ImageDraw.Draw(sheet)
dr.text((16, 14), "第十二版 · 12 项换 Plan C 照片 + 全部方形（QQ音乐除外）",
        font=FB, fill=(255, 255, 255))
dr.text((16, 42), "tag 标注来源：PlanC = 本次替换，v11 = 保持不变",
        font=F, fill=(150, 200, 235))
for i, n in enumerate(ORDER):
    x = (i % cols) * cell
    y = 66 + (i // cols) * (cell + 32)
    ic = imgs[n].resize((172, 172), Image.LANCZOS)
    sheet.paste(ic, (x + 14, y), ic)
    bb = dr.textbbox((0, 0), n, font=F)
    dr.text((x + (cell - (bb[2] - bb[0])) // 2, y + 176), n, font=F, fill=(232, 238, 250))
sheet.save(os.path.join(OUT, "preview_v12.png"))
print("DONE ->", OUT)
