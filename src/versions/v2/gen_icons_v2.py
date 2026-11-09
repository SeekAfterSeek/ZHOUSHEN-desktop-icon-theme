# -*- coding: utf-8 -*-
"""周深主题 v2 · 舞台写真版
每个图标 = 周深舞台/深海氛围背景裁片 + 原应用图标(256px)居中叠加 + 柔和投影
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
BG = os.path.join(ROOT, "bg")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
OUT = os.path.join(ROOT, "icons_v2")
os.makedirs(OUT, exist_ok=True)
S = 256

APPS = [
    "微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
    "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
    "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
    "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家", "腾讯QQ", "腾讯会议",
]

def crop_regions():
    """每张背景裁 6 个 1024 区域（避开右下角水印），共 24 个"""
    regions = []
    for i in range(1, 5):
        img = Image.open(os.path.join(BG, f"stage{i}.png")).convert("RGB")
        for (x, y) in [(0, 0), (768, 0), (1536, 0), (0, 208), (768, 208), (1536, 208)]:
            regions.append(img.crop((x, y, x + 1024, y + 1024)))
    return regions

def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m

def make_icon(name, bg_tile, orig_img):
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # 背景：裁片缩到 256，微调暗度让图形更突出
    bg = bg_tile.resize((S, S), Image.LANCZOS).convert("RGBA")
    dark = Image.new("RGBA", (S, S), (8, 18, 40, 88))
    bg = Image.alpha_composite(bg, dark)
    icon.paste(bg, (0, 0))

    # 原图标：等比缩放到 150px（约 60%），LANCZOS 高质量
    glyph = orig_img.copy().convert("RGBA")
    glyph.thumbnail((150, 150), Image.LANCZOS)

    # 柔和投影
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    alpha = glyph.split()[3]
    sh = Image.new("RGBA", glyph.size, (0, 0, 0, 160))
    shadow.paste(sh, ((S - glyph.width) // 2 + 3, (S - glyph.height) // 2 + 5), alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    icon = Image.alpha_composite(icon, shadow)

    # 图形居中
    icon.paste(glyph, ((S - glyph.width) // 2, (S - glyph.height) // 2), glyph)

    # 底部轻微压暗渐变（增加层次，贴近舞台照片质感）
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for yy in range(S - 60, S):
        a = int(70 * (yy - (S - 60)) / 60)
        gd.line([(0, yy), (S, yy)], fill=(5, 12, 30, a))
    icon = Image.alpha_composite(icon, grad)

    # 圆角裁切
    mask = rounded_mask(S, int(S * 0.24))
    icon.putalpha(Image.composite(icon.split()[3], Image.new("L", (S, S), 0), mask))

    icon.save(os.path.join(OUT, name + ".ico"), format="ICO", bitmap_format="bmp",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    icon.save(os.path.join(OUT, name + ".png"))

def main():
    regions = crop_regions()
    assert len(regions) >= len(APPS), f"regions {len(regions)} < apps {len(APPS)}"
    for idx, name in enumerate(APPS):
        orig_path = os.path.join(ORIG, name + ".png")
        if not os.path.exists(orig_path):
            print("NO ORIG:", name); continue
        orig = Image.open(orig_path)
        make_icon(name, regions[idx], orig)
        print("OK", name)
    print("DONE ->", OUT)

if __name__ == "__main__":
    main()
