# -*- coding: utf-8 -*-
"""周深主题 · 深海之境 —— Windows 桌面图标包生成器
风格：深海蓝渐变底板 + 白色扁平字形 + 星光/鳞光 IP 图层
"""
import os, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "icons")
os.makedirs(OUT, exist_ok=True)
SIZE = 256

# ---- 色板：深海之境 ----
TOP   = (13, 36, 71)      # 深海底色
BOT   = (25, 55, 109)     # 海面过渡
WHITE = (232, 244, 250)   # 鳞光白（主图形）
AQUA  = (79, 195, 217)    # 波光青（点缀1）
PALE  = (155, 227, 255)   # 星光蓝（点缀2）
SILV  = (205, 233, 245)   # 银白（点缀2备选）

FONT_L = "C:\\Windows\\Fonts\\arialbd.ttf"
try:
    FONT_B = "C:\\Windows\\Fonts\\msyhbd.ttc"
except Exception:
    FONT_B = FONT_L

def base_canvas():
    """渐变底板 + 顶部柔光 + 鳞光波弧 + 星光（统一 IP 图层）"""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    grad = Image.new("RGBA", (SIZE, SIZE))
    gd = ImageDraw.Draw(grad)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        c = tuple(int(TOP[i] + (BOT[i] - TOP[i]) * t) for i in range(3)) + (255,)
        gd.line([(0, y), (SIZE, y)], fill=c)
    # 超椭圆圆角方底板
    mask = Image.new("L", (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([2, 2, SIZE - 3, SIZE - 3], radius=int(SIZE * 0.24), fill=255)
    img.paste(grad, (0, 0), mask)

    ov = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    # 左上柔光
    od.ellipse([-40, -50, 150, 110], fill=(120, 190, 235, 40))
    # 底部鳞光波弧
    od.arc([-10, 150, SIZE + 10, 268], start=200, end=340, fill=(155, 227, 255, 90), width=4)
    od.arc([10, 168, SIZE - 10, 286], start=205, end=335, fill=(155, 227, 255, 55), width=3)
    # 右上四角星光
    sx, sy, r1, r2 = SIZE - 44, 40, 13, 3.5
    od.polygon([(sx, sy - r1), (sx + r2, sy - r2), (sx + r1, sy), (sx + r2, sy + r2),
                (sx, sy + r1), (sx - r2, sy + r2), (sx - r1, sy), (sx - r2, sy - r2)],
               fill=(215, 242, 255, 210))
    ov = ov.filter(ImageFilter.GaussianBlur(1.2))
    img = Image.alpha_composite(img, ov)

    d = ImageDraw.Draw(img)
    k = SIZE / 100.0
    return img, d, k

def make_icon(name, glyph):
    img, d, k = base_canvas()
    cx = cy = SIZE / 2

    def T(px, py):
        return (cx + (px - 50) * k, cy + (py - 50) * k)
    def E(x0, y0, x1, y1, fill=None, outline=None, w=4):
        d.ellipse([T(x0, y0), T(x1, y1)], fill=fill, outline=outline, width=max(1, int(w * k)))
    def L(pts, color=WHITE, w=5):
        d.line([T(*p) for p in pts], fill=color, width=max(1, int(w * k)), joint="curve")
    def P(pts, fill=WHITE):
        d.polygon([T(*p) for p in pts], fill=fill)
    def RR(x0, y0, x1, y1, r, outline=None, fill=None, w=4):
        d.rounded_rectangle([T(x0, y0), T(x1, y1)], radius=r * k, outline=outline, fill=fill, width=max(1, int(w * k)))
    def TXT(s, font_path, size, fill=WHITE, dy=0):
        f = ImageFont.truetype(font_path, int(size * k))
        bb = d.textbbox((0, 0), s, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1] + dy * k), s, font=f, fill=fill)

    glyph(d, E, L, P, RR, TXT, T, k)
    img.save(os.path.join(OUT, name + ".ico"), format="ICO",
             bitmap_format="bmp",
             sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    img.save(os.path.join(OUT, name + ".png"))

def note(d, E, L, P, RR, TXT, T, k, x=50, y=50, s=1.0, color=WHITE):
    """单音符字形（QQ音乐 / WorkBuddy 用）"""
    def t(px, py): return T(x + (px - 50) * s, y + (py - 50) * s)
    E(x - 22 * s, y + 8 * s, x + 2 * s, y + 30 * s, fill=color)
    d.line([t(50, 22), t(50, 56)], fill=color, width=max(1, int(6 * s * k)))
    P([(50, 22), (72, 28), (50, 44)], fill=color)

# ============ 各应用字形 ============
GLYPHS = {
    "微信": lambda d, E, L, P, RR, TXT, T, k: (
        E(22, 28, 62, 62, fill=WHITE),
        P([(30, 58), (30, 70), (42, 60)], fill=WHITE),
        E(52, 46, 80, 70, fill=AQUA),
        P([(74, 68), (74, 78), (82, 70)], fill=AQUA),
        E(32, 40, 38, 46, fill=TOP), E(46, 40, 52, 46, fill=TOP)),
    "QQ音乐": lambda d, E, L, P, RR, TXT, T, k: (
        note(d, E, L, P, RR, TXT, T, k, x=46, y=48, s=1.5),
        L([(28, 74), (40, 70), (52, 74), (64, 70), (74, 74)], color=PALE, w=3.5)),
    "哔哩哔哩": lambda d, E, L, P, RR, TXT, T, k: (
        RR(22, 36, 78, 70, 12, outline=WHITE, w=5),
        L([(36, 24), (48, 36)], w=5), L([(64, 24), (52, 36)], w=5),
        L([(40, 48), (40, 60)], w=5), L([(60, 48), (60, 60)], w=5)),
    "Google Chrome": lambda d, E, L, P, RR, TXT, T, k: (
        E(20, 20, 80, 80, outline=WHITE, w=6),
        E(41, 41, 59, 59, fill=PALE),
        d.arc(T_b := [T(26, 26), T(74, 74)], start=200, end=320, fill=AQUA, width=int(6 * k))),
    "个人 - Edge": lambda d, E, L, P, RR, TXT, T, k: (
        d.arc([T(20, 20), T(80, 80)], start=130, end=40, fill=WHITE, width=int(6.5 * k)),
        E(38, 38, 62, 62, outline=AQUA, w=5)),
    "360安全浏览器": lambda d, E, L, P, RR, TXT, T, k: TXT("360", FONT_L, 30),
    "Visual Studio Code": lambda d, E, L, P, RR, TXT, T, k: (
        L([(34, 32), (18, 50), (34, 68)], w=6.5),
        L([(66, 32), (82, 50), (66, 68)], w=6.5),
        L([(56, 26), (44, 74)], color=AQUA, w=6.5)),
    "Cursor": lambda d, E, L, P, RR, TXT, T, k: (
        P([(36, 22), (36, 72), (52, 57), (62, 74), (71, 68), (61, 52), (76, 50)], fill=WHITE)),
    "DeepSeek Harness": lambda d, E, L, P, RR, TXT, T, k: (
        E(20, 42, 66, 70, fill=WHITE),
        P([(62, 42), (84, 30), (78, 52), (86, 60), (62, 62)], fill=WHITE),
        L([(34, 34), (44, 44), (54, 36)], color=PALE, w=3.5),
        E(30, 50, 38, 58, fill=TOP)),
    "Cherry Studio": lambda d, E, L, P, RR, TXT, T, k: (
        L([(40, 58), (52, 28)], w=4.5), L([(62, 58), (52, 28)], w=4.5),
        E(24, 52, 46, 74, fill=PALE), E(56, 52, 78, 74, fill=AQUA)),
    "WorkBuddy": lambda d, E, L, P, RR, TXT, T, k: (
        note(d, E, L, P, RR, TXT, T, k, x=50, y=48, s=1.4, color=WHITE),
        E(64, 28, 76, 40, outline=PALE, w=3)),
    "WPS Office": lambda d, E, L, P, RR, TXT, T, k: TXT("W", FONT_B, 40),
    "全能录屏助手": lambda d, E, L, P, RR, TXT, T, k: (
        E(24, 24, 76, 76, outline=WHITE, w=5.5), E(41, 41, 59, 59, fill=AQUA)),
    "剪映专业版": lambda d, E, L, P, RR, TXT, T, k: (
        RR(24, 24, 76, 76, 16, outline=WHITE, w=5),
        P([(42, 38), (42, 62), (64, 50)], fill=AQUA)),
    "百度网盘": lambda d, E, L, P, RR, TXT, T, k: (
        E(24, 34, 52, 58, fill=WHITE), E(44, 26, 76, 54, fill=WHITE),
        RR(30, 46, 72, 60, 8, fill=WHITE),
        P([(50, 62), (50, 72), (42, 72), (50, 84), (58, 72), (50, 72)], fill=AQUA)),
    "飞书": lambda d, E, L, P, RR, TXT, T, k: (
        P([(22, 52), (80, 26), (50, 54)], fill=WHITE),
        P([(50, 54), (80, 26), (62, 74)], fill=PALE),
        P([(50, 54), (62, 74), (46, 66)], fill=AQUA)),
    "Clash Verge": lambda d, E, L, P, RR, TXT, T, k: (
        P([(56, 20), (36, 54), (50, 54), (42, 80), (68, 44), (54, 44)], fill=WHITE)),
    "PyCharm 2026.2.3": lambda d, E, L, P, RR, TXT, T, k: TXT("Py", FONT_L, 34),
    "ToDesk": lambda d, E, L, P, RR, TXT, T, k: (
        RR(22, 30, 78, 62, 8, outline=WHITE, w=5),
        L([(50, 62), (50, 72)], w=5), L([(36, 74), (64, 74)], w=5)),
    "互传": lambda d, E, L, P, RR, TXT, T, k: (
        P([(20, 42), (52, 42), (52, 32), (68, 46), (52, 60), (52, 50), (20, 50)], fill=WHITE),
        P([(80, 58), (48, 58), (48, 68), (32, 54), (48, 40), (48, 50), (80, 50)], fill=AQUA)),
    "网易邮箱大师": lambda d, E, L, P, RR, TXT, T, k: (
        RR(22, 32, 78, 68, 8, outline=WHITE, w=5),
        L([(24, 34), (50, 54), (76, 34)], w=5)),
    "联想电脑管家": lambda d, E, L, P, RR, TXT, T, k: (
        P([(50, 20), (76, 30), (74, 54), (50, 80), (26, 54), (24, 30)], fill=WHITE),
        L([(38, 50), (47, 60), (64, 40)], color=AQUA, w=6)),
    "腾讯QQ": lambda d, E, L, P, RR, TXT, T, k: (
        E(30, 36, 70, 80, fill=WHITE),
        E(34, 20, 66, 52, fill=WHITE),
        P([(46, 38), (54, 38), (50, 44)], fill=AQUA),
        RR(34, 56, 66, 63, 3, fill=AQUA)),
    "腾讯会议": lambda d, E, L, P, RR, TXT, T, k: (
        RR(22, 34, 60, 66, 10, fill=WHITE),
        P([(60, 42), (80, 32), (80, 68), (60, 58)], fill=PALE)),
}

def main():
    for name, g in GLYPHS.items():
        make_icon(name, g)
        print("OK", name)
    print("DONE", len(GLYPHS), "icons ->", OUT)

if __name__ == "__main__":
    main()
