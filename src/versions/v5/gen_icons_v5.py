# -*- coding: utf-8 -*-
"""周深主题 v5 · 氛围异形版

在 v4（配色匹配 + 人工策展照片）基础上迭代：
  1. 脸部定位裁剪：肤色质心估计人脸位置，裁剪让人脸占比更大
  2. 异形轮廓：每个图标一种有机形状（拱形/鹅卵石/波浪圆/超椭圆），随机微扰不重样
  3. 氛围感：APP 主色霓虹描边 + 外发光 + 暗角 + 星点 + 内高光（对标 QQ音乐联名图标质感）
  4. 角标加大到 96px
历史版本 icons_v3 / icons_v4 全部保留。
"""
import os, re, json, math, random, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
PHOTOS = os.path.join(ROOT, "photos")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
OUT = os.path.join(ROOT, "icons_v5")
os.makedirs(OUT, exist_ok=True)
S = 256
BADGE = 96
PAD = 8

APP_COLORS = {
    "微信":               (["green"], "#3EB575"),
    "QQ音乐":             (["yellow", "cyan"], "#F5C542"),
    "哔哩哔哩":           (["pink"], "#FF7FA5"),
    "Google Chrome":      (["yellow", "green", "red"], "#E8B33C"),
    "个人 - Edge":        (["blue", "cyan"], "#3FA9F5"),
    "360安全浏览器":      (["green"], "#57C46B"),
    "Visual Studio Code": (["blue"], "#2F8FE0"),
    "Cursor":             (["yellow"], "#F0C24B"),
    "DeepSeek Harness":   (["black", "gray"], "#8A9BB0"),
    "Cherry Studio":      (["red"], "#E05555"),
    "WorkBuddy":          (["cyan", "green"], "#4FC3B5"),
    "WPS Office":         (["red"], "#D94B3A"),
    "全能录屏助手":       (["gray", "red"], "#C96A6A"),
    "剪映专业版":         (["black", "gray"], "#9AA5B1"),
    "百度网盘":           (["gray", "blue"], "#6FA8DC"),
    "飞书":               (["blue", "cyan"], "#4FB6E0"),
    "Clash Verge":        (["purple", "pink"], "#B07AE0"),
    "PyCharm 2026.2.3":   (["gray", "blue"], "#7E93AD"),
    "ToDesk":             (["gray", "blue"], "#5E8FBF"),
    "互传":               (["blue"], "#4A90D9"),
    "网易邮箱大师":       (["red"], "#D9534F"),
    "联想电脑管家":       (["blue"], "#4A7FD9"),
    "腾讯QQ":             (["gray", "red"], "#BF6A5A"),
    "腾讯会议":           (["blue"], "#4A85D9"),
}
APPS = list(APP_COLORS.keys())

def load_curated():
    out = {}
    path = os.path.join(ROOT, "curate_v4.txt")
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        app, rest = line.split("=", 1)
        out[app.strip()] = os.path.join(PHOTOS, rest.split("#")[0].strip())
    return out

# ---------- 脸部定位（肤色质心） ----------
def face_focus(path):
    """返回 (fx, fy)：照片中人脸的相对位置（0~1），找不到就默认中上"""
    try:
        im = Image.open(path).convert("RGB").resize((128, 128))
    except Exception:
        return 0.5, 0.38
    a = np.asarray(im, dtype=np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2); mn = a.min(axis=2)
    skin = (r > 95) & (g > 40) & (b > 20) & (r > g) & (r > b) & \
           ((mx - mn) > 15) & ((r - g) > 15) & (np.abs(r - g) > 10)
    # 只看上部 60%（人像脸在上部）
    skin[int(128 * 0.60):, :] = False
    ys, xs = np.nonzero(skin)
    if len(ys) < 40:
        return 0.5, 0.34
    # 用 30%~70% 分位抗离群，y 再往上收（肤色块下缘常含脖子，脸心更高）
    x0, x1 = np.percentile(xs, [30, 70])
    y0, y1 = np.percentile(ys, [25, 65])
    fx = float(np.clip((x0 + x1) / 2 / 128, 0.15, 0.85))
    fy = float(np.clip((y0 * 0.75 + y1 * 0.25) / 128, 0.10, 0.55))
    return fx, fy

# ---------- 异形轮廓 ----------
def mask_for_shape(shape, seed):
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    rnd = random.Random(seed)
    if shape == "squircle":
        d.rounded_rectangle([6, 6, S - 7, S - 7], radius=int(S * 0.30), fill=255)
    elif shape == "circle":
        d.ellipse([8, 8, S - 9, S - 9], fill=255)
    elif shape == "arch":
        # 拱门形：上圆下方
        r = (S - 20) // 2
        d.pieslice([10, 10, 10 + 2 * r, 10 + 2 * r], 180, 360, fill=255)
        d.rectangle([10, 10 + r, 10 + 2 * r, S - 8], fill=255)
        d.rounded_rectangle([10, S - 30, 10 + 2 * r, S - 8], radius=10, fill=255)
    elif shape == "pebble":
        # 鹅卵石：横向椭圆
        d.ellipse([10, int(S * 0.16), S - 11, int(S * 0.84) + 20], fill=255)
    elif shape == "blob":
        # 有机波浪圆：极坐标扰动
        cx, cy = S / 2, S / 2
        base = S * 0.44
        harms = [(rnd.uniform(0.03, 0.08), rnd.randint(2, 4), rnd.uniform(0, 6.28)),
                 (rnd.uniform(0.02, 0.05), rnd.randint(5, 7), rnd.uniform(0, 6.28))]
        pts = []
        for i in range(120):
            th = i / 120 * 2 * math.pi
            rr = base * (1 + sum(a * math.sin(k * th + ph) for a, k, ph in harms))
            pts.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
        d.polygon(pts, fill=255)
    elif shape == "whale":
        # 大肥鲸：头朝左占满画面（约95%），脸对准鲸头；尾鳍占右上小角，右下留角标
        K4 = S * 4
        big = Image.new("L", (K4, K4), 0)
        bd = ImageDraw.Draw(big)
        k = K4 / 256.0
        def P(pts):
            bd.polygon([(x * k, y * k) for x, y in pts], fill=255)
        # 巨大圆滚的躯干（撑满画布）
        bd.ellipse([4 * k, 52 * k, 236 * k, 252 * k], fill=255)
        # 高耸的头部圆顶（脸的位置）
        bd.ellipse([6 * k, 30 * k, 168 * k, 210 * k], fill=255)
        # 前额凸起（大头像感）
        bd.ellipse([16 * k, 40 * k, 120 * k, 170 * k], fill=255)
        # 尾柄 + 上翘大尾鳍（右上角）
        P([(196,74),(226,26),(244,44),(252,20),(254,96),(224,120),(196,140)])
        # 侧鳍（下方小翅膀）
        P([(84,226),(120,254),(158,224),(120,242)])
        # 缩回 256 并轻微羽化
        m2 = big.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
        m.paste(m2, (0, 0))
    return m

# ---------- 生成 ----------
def center_crop(im, zoom, fx, fy):
    w, h = im.size
    scale = max(S / w, S / h) * zoom
    nw, nh = int(w * scale), int(h * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = max(0, min(int(nw * fx - S / 2), nw - S))
    top = max(0, min(int(nh * fy - S / 2), nh - S))
    return im.crop((left, top, left + S, top + S))

def hex_to_rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))

def draw_sparkles(d, rnd, n=3):
    """星点只放在四角区域，避免压脸"""
    corners = [(0.12, 0.12), (0.88, 0.12), (0.10, 0.78), (0.90, 0.80)]
    picked = rnd.sample(corners, min(n, len(corners)))
    for (cx, cy) in picked:
        x = int(S * cx + rnd.uniform(-12, 12))
        y = int(S * cy + rnd.uniform(-10, 10))
        r1 = rnd.uniform(6, 11); r2 = r1 * 0.28
        c = (255, 255, 255, rnd.randint(100, 170))
        d.polygon([(x, y - r1), (x + r2, y - r2), (x + r1, y), (x + r2, y + r2),
                   (x, y + r1), (x - r2, y + r2), (x - r1, y), (x - r2, y - r2)], fill=c)

def make_badge(orig_img, dia=BADGE):
    logo = orig_img.copy().convert("RGBA")
    logo.thumbnail((int(dia * 0.66), int(dia * 0.66)), Image.LANCZOS)
    canvas = Image.new("RGBA", (dia, dia), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse([0, 0, dia - 1, dia - 1], fill=(255, 255, 255, 248),
              outline=(16, 30, 54, 210), width=3)
    canvas.paste(logo, ((dia - logo.width) // 2, (dia - logo.height) // 2), logo)
    return canvas

def make_icon(name, photo, shape, seed, accent, dfx=0.0, dfy=0.0, dzoom=0.0):
    fx, fy = face_focus(photo)
    fx = float(np.clip(fx + dfx, 0.1, 0.9))
    fy = float(np.clip(fy + dfy, 0.08, 0.6))
    im = Image.open(photo).convert("RGB")
    zoom = 1.14 + (0.38 - fy) * 0.35 + dzoom
    zoom = max(1.02, min(1.32, zoom))
    canvas = center_crop(im, zoom, fx, fy).convert("RGBA")

    accent_rgb = hex_to_rgb(accent)
    rnd = random.Random(seed)

    # 提亮提饱和：还原图标本色（v5 用户反馈蒙暗）
    rgb_boost = canvas.convert("RGB")
    from PIL import ImageEnhance
    rgb_boost = ImageEnhance.Color(rgb_boost).enhance(1.28)     # 饱和度 +28%
    rgb_boost = ImageEnhance.Brightness(rgb_boost).enhance(1.16) # 亮度 +16%
    rgb_boost = ImageEnhance.Contrast(rgb_boost).enhance(1.05)   # 轻微对比
    canvas = rgb_boost.convert("RGBA")

    # 边缘轻暗角（只压四角，不罩中心）：给一点氛围但不蒙灰
    vig = Image.new("L", (S, S), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-S * 0.35, -S * 0.35, S * 1.35, S * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(46))
    # 椭圆外=0（压暗），内=255（不动）；最大压暗 22%
    dark = Image.new("RGBA", (S, S), (8, 14, 30, 56))
    dark_mask = vig.point(lambda v: 255 - v)
    canvas = Image.composite(canvas, Image.alpha_composite(canvas, dark), dark_mask)

    # 异形 mask + 霓虹描边 + 外发光
    mask = mask_for_shape(shape, seed)
    rgb = canvas.convert("RGB")
    cut = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cut.paste(rgb, (0, 0), mask)
    canvas = cut

    # 外发光（accent 色，blur 的 mask）
    glow_m = mask.filter(ImageFilter.GaussianBlur(10))
    glow = Image.new("RGBA", (S, S), accent_rgb + (0,))
    glow.putalpha(glow_m.point(lambda v: int(v * 0.55)))
    canvas = Image.alpha_composite(glow, canvas)

    # 描边
    edge = Image.new("RGBA", (S, S), accent_rgb + (0,))
    edge_m = mask.filter(ImageFilter.MaxFilter(5))
    edge_m = Image.composite(Image.new("L", (S, S), 255), Image.new("L", (S, S), 0),
                             Image.eval(Image.composite(edge_m, Image.new("L", (S, S), 0), mask),
                                        lambda v: 255 - v))
    edge.putalpha(edge_m.point(lambda v: int(v * 0.85)))
    canvas = Image.alpha_composite(canvas, edge)

    # 内侧高光（左上柔光）
    hi = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    hd.ellipse([-S * 0.2, -S * 0.25, S * 0.75, S * 0.55], fill=(255, 255, 255, 42))
    hi = hi.filter(ImageFilter.GaussianBlur(28))
    hi.putalpha(Image.composite(hi.split()[3], Image.new("L", (S, S), 0), mask))
    canvas = Image.alpha_composite(canvas, hi)

    # 星点
    sp = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw_sparkles(ImageDraw.Draw(sp), rnd)
    sp.putalpha(Image.composite(sp.split()[3], Image.new("L", (S, S), 0), mask))
    canvas = Image.alpha_composite(canvas, sp)

    # 底部轻渐暗（只托角标，压得轻）
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for yy in range(S - 70, S):
        a = int(60 * (yy - (S - 70)) / 70)
        gd.line([(0, yy), (S, yy)], fill=(4, 10, 26, a))
    grad.putalpha(Image.composite(grad.split()[3], Image.new("L", (S, S), 0), mask))
    canvas = Image.alpha_composite(canvas, grad)

    # 大角标
    badge = make_badge(Image.open(os.path.join(ORIG, name + ".png")))
    bx, by = S - BADGE - PAD, S - BADGE - PAD
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", badge.size, (0, 0, 0, 130)), (bx + 2, by + 5), badge.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    sh.putalpha(Image.composite(sh.split()[3], Image.new("L", (S, S), 0),
                                Image.eval(mask, lambda v: v)))
    canvas = Image.alpha_composite(canvas, sh)
    canvas.paste(badge, (bx, by), badge)

    # 最终透明区：mask 外全透明（含发光区保留一点）
    alpha = canvas.split()[3]
    soft = mask.filter(ImageFilter.GaussianBlur(8)).point(lambda v: min(255, v * 2))
    final_a = Image.composite(alpha, Image.eval(soft, lambda v: int(v * 0.5)),
                              Image.eval(mask, lambda v: 255 if v > 200 else 0))
    canvas.putalpha(final_a)

    canvas.save(os.path.join(OUT, name + ".ico"), format="ICO", bitmap_format="bmp",
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    canvas.save(os.path.join(OUT, name + ".png"))

SHAPES = ["squircle", "circle", "arch", "pebble", "blob"]

# 人工微调覆盖：APP -> (dfx, dfy, dzoom)  裁剪中心偏移 / 缩放修正
OVERRIDES = {
    "个人 - Edge":    (0.06, 0.00, -0.04),
    "互传":          (-0.06, 0.00, -0.04),
    "联想电脑管家":  (0.07, 0.02, -0.06),
    "全能录屏助手":  (0.00, -0.07, -0.10),
    "360安全浏览器": (0.05, 0.02, -0.08),
    "DeepSeek Harness": (0.10, -0.02, 0.34),   # 鲸形满幅，脸占主体，尾鳍落在暗背景
    "腾讯QQ":       (0.00, -0.03, -0.10),
}

# 指定异形：默认按 SHAPES 轮换，这里的覆盖优先
SHAPE_OVERRIDE = {
    "DeepSeek Harness": "whale",
}

def main():
    curated = load_curated()
    print("curated:", len(curated))
    for i, app in enumerate(APPS):
        photo = curated.get(app)
        if not photo or not os.path.exists(photo):
            print("NO PHOTO:", app); continue
        shape = SHAPE_OVERRIDE.get(app, SHAPES[i % len(SHAPES)])
        accent = APP_COLORS[app][1]
        ov = OVERRIDES.get(app, (0.0, 0.0, 0.0))
        make_icon(app, photo, shape, seed=1000 + i * 37, accent=accent,
                  dfx=ov[0], dfy=ov[1], dzoom=ov[2])
        print("OK %-18s %s" % (app, shape))
    print("DONE ->", OUT)

if __name__ == "__main__":
    main()
