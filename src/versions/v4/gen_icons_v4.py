# -*- coding: utf-8 -*-
"""周深主题 v4 · 配色匹配版

规则：
  1. 每个 APP 按其**原图标主色**，从周深真人照片库里挑一张配色最接近的
  2. 24 个 APP 用 24 张**互不相同**的照片
  3. 照片必须含周深本人
  4. 结构沿用 v3：照片满铺 + 右下角原 APP 小角标
"""
import os, json, colorsys
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
PHOTOS = os.path.join(ROOT, "photos")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
OUT = os.path.join(ROOT, "icons_v4")
os.makedirs(OUT, exist_ok=True)
S = 256
BADGE = 72
PAD = 8

# APP -> 原图标主色（来自 analyze 结果）
APP_COLORS = {
    "微信":               ["green"],
    "QQ音乐":             ["yellow", "cyan"],
    "哔哩哔哩":           ["pink"],
    "Google Chrome":      ["yellow", "green", "red", "blue"],
    "个人 - Edge":        ["blue", "cyan"],
    "360安全浏览器":      ["green"],
    "Visual Studio Code": ["blue"],
    "Cursor":             ["yellow"],
    "DeepSeek Harness":   ["black", "gray"],
    "Cherry Studio":      ["red"],
    "WorkBuddy":          ["cyan", "green"],
    "WPS Office":         ["red"],
    "全能录屏助手":       ["gray", "red"],
    "剪映专业版":         ["black", "gray"],
    "百度网盘":           ["gray", "blue"],
    "飞书":               ["blue", "cyan"],
    "Clash Verge":        ["purple", "pink"],
    "PyCharm 2026.2.3":   ["gray", "blue", "yellow"],
    "ToDesk":             ["gray", "blue"],
    "互传":               ["blue"],
    "网易邮箱大师":       ["red"],
    "联想电脑管家":       ["blue"],
    "腾讯QQ":             ["gray", "red"],
    "腾讯会议":           ["blue"],
}

APPS = list(APP_COLORS.keys())

def hue_profile(path):
    im = Image.open(path).convert("RGB").resize((64, 64))
    h_counts = {k: 0 for k in ["red","orange","yellow","green","cyan","blue","purple","pink","gray","black","white"]}
    px = list(im.getdata())
    for r, g, b in px:
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        if l < 0.10: h_counts["black"] += 1; continue
        if l > 0.90: h_counts["white"] += 1; continue
        if s < 0.12: h_counts["gray"] += 1; continue
        d = h * 360
        if d < 15 or d >= 345: h_counts["red"] += 1
        elif d < 40: h_counts["orange"] += 1
        elif d < 70: h_counts["yellow"] += 1
        elif d < 165: h_counts["green"] += 1
        elif d < 200: h_counts["cyan"] += 1
        elif d < 265: h_counts["blue"] += 1
        elif d < 310: h_counts["purple"] += 1
        else: h_counts["pink"] += 1
    tot = sum(h_counts.values()) or 1
    return {k: v / tot for k, v in h_counts.items()}

def face_score(path):
    """粗略检测照片是否含人物：肤色像素占比 + 边缘复杂度（排除纯 logo/文字/海报图）"""
    try:
        im = Image.open(path).convert("RGB")
        im = im.resize((96, 96))
    except Exception:
        return 0.0
    px = list(im.getdata())
    skin = 0
    for r, g, b in px:
        if r > 95 and g > 40 and b > 20 and r > g and r > b \
           and (max(r, g, b) - min(r, g, b)) > 15 and abs(r - g) > 15:
            skin += 1
    skin_ratio = skin / len(px)

    gray = im.convert("L")
    w, h = gray.size
    gd = list(gray.getdata())
    edges = 0
    for y in range(1, h-1, 2):
        for x in range(1, w-1, 2):
            i = y*w + x
            if abs(gd[i] - gd[i-1]) > 22 or abs(gd[i] - gd[i-w]) > 22:
                edges += 1
    edge_ratio = edges / ((w//2) * (h//2))

    if skin_ratio < 0.012:
        return 0.0
    return skin_ratio * 2.0 + min(edge_ratio, 1.0) * 0.5

def load_photos():
    items = []
    # 已人工确认合格的图（避免被算法误选，也避免重复踩坑）
    BLOCKLIST = set()
    bl_path = os.path.join(ROOT, "photo_blocklist.txt")
    if os.path.exists(bl_path):
        BLOCKLIST = {l.strip() for l in open(bl_path, encoding="utf-8") if l.strip()}
    for f in sorted(os.listdir(PHOTOS)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        if f.startswith("test") or f in BLOCKLIST:
            continue
        p = os.path.join(PHOTOS, f)
        try:
            im = Image.open(p)
            w, h = im.size
            if min(w, h) < 500:
                continue
            prof = hue_profile(p)
            fs = face_score(p)
            if fs <= 0.01:
                continue
            items.append((p, im.size, prof, fs))
        except Exception:
            pass
    return items

def score(profile, targets):
    """配色匹配分：目标色占比越高越好"""
    return sum(profile.get(t, 0) for t in targets)

def combined_score(profile, targets, fs):
    """配色分 + 人物分（人物不明显直接压到很低）"""
    if fs <= 0.01:
        return -1.0
    return score(profile, targets) + min(fs, 2.0) * 0.55

def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
    return m

def make_badge(orig_img, dia=BADGE):
    logo = orig_img.copy().convert("RGBA")
    logo.thumbnail((int(dia*0.68), int(dia*0.68)), Image.LANCZOS)
    canvas = Image.new("RGBA", (dia, dia), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse([0, 0, dia-1, dia-1], fill=(255,255,255,245), outline=(18,32,56,190), width=2)
    canvas.paste(logo, ((dia-logo.width)//2, (dia-logo.height)//2), logo)
    return canvas

def center_crop_square(im, zoom=1.06, fx=0.5, fy=0.5):
    w, h = im.size
    scale = max(S/w, S/h) * zoom
    nw, nh = int(w*scale), int(h*scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = max(0, min(int((nw-S)*fx), nw-S))
    top = max(0, min(int((nh-S)*fy), nh-S))
    return im.crop((left, top, left+S, top+S))

def load_curated():
    """读取人工策展清单：APP = 文件名 # 备注"""
    path = os.path.join(ROOT, "curate_v4.txt")
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        app, rest = line.split("=", 1)
        fn = rest.split("#")[0].strip()
        out[app.strip()] = os.path.join(PHOTOS, fn)
    return out

def main():
    photos = load_photos()
    print(f"photos available: {len(photos)}")
    used = set()
    assignment = {}

    curated = load_curated()
    if curated:
        print(f"using curated list: {len(curated)} apps")
        for app, p in curated.items():
            if os.path.exists(p):
                assignment[app] = p
                used.add(p)
            else:
                print("curated missing, fallback:", app, os.path.basename(p))

    # 未策展的 APP 走自动匹配
    rest_apps = [a for a in APPS if a not in assignment]
    if rest_apps:
        def best_for(app, pool):
            targets = APP_COLORS[app]
            cands = sorted(pool, key=lambda x: -combined_score(x[2], targets, x[3]))
            return cands[0] if cands else None
        order = sorted(rest_apps, key=lambda a: max(
            (combined_score(p[2], APP_COLORS[a], p[3]) for p in photos), default=0))
        for app in order:
            targets = APP_COLORS[app]
            pool = [p for p in photos if p[0] not in used]
            if not pool:
                print("NO PHOTO LEFT for", app); continue
            best = best_for(app, pool)
            assignment[app] = best[0]
            used.add(best[0])
            print(f"{app:20s} <- {os.path.basename(best[0])} (auto)")

    # 生成
    ok = 0
    for app, photo in assignment.items():
        orig_p = os.path.join(ORIG, app + ".png")
        if not os.path.exists(orig_p):
            print("missing orig:", app); continue
        im = Image.open(photo).convert("RGB")
        canvas = center_crop_square(im, zoom=1.08).convert("RGBA")

        # 底部渐暗，托住角标
        grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for yy in range(S-90, S):
            a = int(105 * (yy-(S-90))/90)
            gd.line([(0, yy), (S, yy)], fill=(4, 10, 26, a))
        canvas = Image.alpha_composite(canvas, grad)

        badge = make_badge(Image.open(orig_p))
        bx, by = S-BADGE-PAD, S-BADGE-PAD
        shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        shadow.paste(Image.new("RGBA", badge.size, (0,0,0,115)), (bx+2, by+4), badge.split()[3])
        shadow = shadow.filter(ImageFilter.GaussianBlur(5))
        canvas = Image.alpha_composite(canvas, shadow)
        canvas.paste(badge, (bx, by), badge)

        mask = rounded_mask(S, int(S*0.235))
        canvas.putalpha(Image.composite(canvas.split()[3], Image.new("L", (S,S), 0), mask))

        canvas.save(os.path.join(OUT, app + ".ico"), format="ICO", bitmap_format="bmp",
                    sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
        canvas.save(os.path.join(OUT, app + ".png"))
        ok += 1

    json.dump({k: os.path.basename(v) for k, v in assignment.items()},
              open(os.path.join(ROOT, "assignment_v4.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"DONE {ok} icons -> {OUT}")

if __name__ == "__main__":
    main()
