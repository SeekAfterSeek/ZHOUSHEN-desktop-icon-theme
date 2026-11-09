# -*- coding: utf-8 -*-
"""周深主题 v3 · 明星联名版（QQ音乐装扮中心同款结构）

结构参考 QQ音乐「明星」标签页的 APP 图标：
  - 整张图标 = 明星写真 / 专辑艺术图，满铺
  - 右下角一个小圆角标 = 该应用自己的 logo（QQ音乐系列用的是自家小音符）
  - 方形圆角裁切

这样既一眼是周深主题，又靠角标保留每个应用的辨识度。
"""
import os, random
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(ROOT, "bg")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
OUT = os.path.join(ROOT, "icons_v3")
os.makedirs(OUT, exist_ok=True)
S = 256
BADGE = 74          # 角标直径
BADGE_PAD = 9       # 角标距边

APPS = [
    "微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
    "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
    "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
    "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家", "腾讯QQ", "腾讯会议",
]

# 周深素材池（按"人物感"排序，主力是写真，艺术图穿插）
# fx/fy = 裁切焦点，向右/向下推要加大；stage* 图主体多在中间偏下
POOL = [
    ("zs_singer.png",   [(0.42, 0.08), (0.55, 0.02), (0.38, 0.14)]),   # 白衣闭眼演唱（人脸在中上部）
    ("zs_arms.png",     [(0.42, 0.12), (0.46, 0.06), (0.38, 0.18)]),   # 张开双臂星云
    ("zs_portrait.png", [(0.38, 0.06), (0.44, 0.12), (0.34, 0.0)]),    # 侧脸仰头暖光
    ("zs_note.png",     [(0.40, 0.10), (0.44, 0.04)]),                 # 深海发光音符
    ("stage1.png",      [(0.34, 0.18), (0.40, 0.10), (0.30, 0.22)]),   # 星海演唱会（舞台在中）
    ("stage2.png",      [(0.30, 0.10), (0.38, 0.16)]),                 # 深海鲸鱼（鲸鱼居中）
    ("stage3.png",      [(0.67, 1.0), (0.62, 0.92)]),                  # 海边白衣歌手（人物约在 0.61,0.72）
    ("stage4.png",      [(0.30, 0.06), (0.36, 0.12)]),                 # 荧光花海
]

def load_cover(path, zoom=1.0, fx=0.5, fy=0.5):
    """等比填充到 S×S，再按 zoom/fx/fy 做裁切偏移（避开流水印）"""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = max(S / w, S / h) * zoom
    nw, nh = int(w * scale), int(h * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = int((nw - S) * fx)
    top = int((nh - S) * fy)
    left = max(0, min(left, nw - S))
    top = max(0, min(top, nh - S))
    return img.crop((left, top, left + S, top + S))

def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m

def circle_mask(size):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    return m

def make_badge(orig_img, dia=BADGE):
    """把原应用 logo 做成右下角小圆标：白色描边 + 投影 + 细描边圈（防止白底 logo 糊在一起）"""
    logo = orig_img.copy().convert("RGBA")
    logo.thumbnail((int(dia * 0.68), int(dia * 0.68)), Image.LANCZOS)
    canvas = Image.new("RGBA", (dia, dia), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    # 白底圆 + 深色细边，保证白底 App（Chrome/微信）也分得清边界
    d.ellipse([0, 0, dia - 1, dia - 1], fill=(255, 255, 255, 245),
              outline=(18, 32, 56, 190), width=2)
    # logo 居中贴上
    canvas.paste(logo, ((dia - logo.width) // 2, (dia - logo.height) // 2), logo)
    return canvas

def make_icon(name, src_path, fx, fy, orig_img, zoom=1.0):
    canvas = load_cover(src_path, zoom=zoom, fx=fx, fy=fy).convert("RGBA")

    # 整体轻压暗一点点，让下方角标有对比（保持写真通透，不压死）
    shade = Image.new("RGBA", (S, S), (6, 14, 34, 30))
    canvas = Image.alpha_composite(canvas, shade)

    # 右下角柔化暗部，托住角标
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([S - 130, S - 130, S + 40, S + 40], fill=(4, 10, 26, 80))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    canvas = Image.alpha_composite(canvas, glow)

    # 角标 + 投影
    badge = make_badge(orig_img)
    bx = S - BADGE - BADGE_PAD
    by = S - BADGE - BADGE_PAD
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sh = Image.new("RGBA", badge.size, (0, 0, 0, 120))
    shadow.paste(sh, (bx + 2, by + 4), badge.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    canvas = Image.alpha_composite(canvas, shadow)
    canvas.paste(badge, (bx, by), badge)

    # 圆角裁切
    mask = rounded_mask(S, int(S * 0.235))
    canvas.putalpha(Image.composite(canvas.split()[3], Image.new("L", (S, S), 0), mask))

    canvas.save(os.path.join(OUT, name + ".ico"), format="ICO", bitmap_format="bmp",
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    canvas.save(os.path.join(OUT, name + ".png"))

def main():
    # 打散素材池顺序，让相邻图标不重样
    rng = random.Random(20260807)
    combos = []
    for src, offsets in POOL:
        for (fx, fy) in offsets:
            combos.append((src, fx, fy))
    # 24 个图标轮流取，尽量不连续重复同一张源图
    rng.shuffle(combos)
    picks = []
    while len(picks) < len(APPS):
        batch = combos[:]
        rng.shuffle(batch)
        for c in batch:
            if len(picks) >= len(APPS):
                break
            if picks and picks[-1][0] == c[0] and len(combos) > 3:
                continue
            picks.append(c)

    for name, (src, fx, fy) in zip(APPS, picks):
        orig_path = os.path.join(ORIG, name + ".png")
        src_path = os.path.join(BG, src)
        if not os.path.exists(orig_path):
            print("NO ORIG:", name); continue
        if not os.path.exists(src_path):
            print("NO BG:", src); continue
        # zoom>1 裁掉源图边缘（水印在右下角，放大后自然被裁掉）
        # stage3 是很宽的海边远景，人物偏小，需要额外放大
        if src == "stage3.png":
            zoom = 1.55
        elif src.startswith("zs_"):
            zoom = 1.18
        else:
            zoom = 1.08
        make_icon(name, src_path, fx, fy, Image.open(orig_path), zoom=zoom)
        print(f"OK {name:20s} <- {src} ({fx},{fy})")
    print("DONE ->", OUT)

if __name__ == "__main__":
    main()
