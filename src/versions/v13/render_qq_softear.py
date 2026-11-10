# -*- coding: utf-8 -*-
"""耳朵轮廓改为「软 alpha」，保留照片本身的渐变

原做法：橙色阈值 + 膨胀 → 硬边，把耳朵周围的暗场也框进来，形成一圈黑边。
新做法：alpha 由像素自身的饱和度/亮度连续决定，边缘自然淡出，
        保留橙→暗的原图渐变，不再有人为黑框。
"""
import sys
import io
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import render_p20 as RP
import render_qq_circle2 as C2
import render_qq_glow as G

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "_qq_softear")
os.makedirs(OUT, exist_ok=True)
S = RP.S
TF, AY = 0.40, 0.52


def soft_ear_alpha(crop, ymax=0.42, s_lo=45, s_hi=150, v_lo=45, v_hi=185, blur=7):
    a = np.asarray(crop.convert("RGB"))
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # 橙色/棕色毛发（含白色绒毛的高亮）
    hue_ok = (((h >= 2) & (h <= 34)) | (s < 40)).astype(np.float32)
    ws = np.clip((s - s_lo) / (s_hi - s_lo), 0, 1)
    wv = np.clip((v - v_lo) / (v_hi - v_lo), 0, 1)
    w = hue_ok * np.maximum(ws, wv * 0.9)
    # 只保留上半部
    w[int(S * ymax):, :] = 0
    w = (w * 255).astype(np.uint8)
    img = Image.fromarray(w).filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(img).astype(np.float32) / 255.0


def build_mask(crop, cy=0.545, r=0.455, ear_gain=1.0, ymax=0.42):
    base = Image.new("L", (S, S), 0)
    ImageDraw.Draw(base).ellipse(
        [S * (.5 - r), S * (cy - r), S * (.5 + r), S * (cy + r)], fill=255)
    ear = soft_ear_alpha(crop, ymax=ymax)
    ear_img = Image.fromarray((np.clip(ear * ear_gain, 0, 1) * 255).astype(np.uint8))
    m = Image.fromarray(np.maximum(np.asarray(base), np.asarray(ear_img)).astype(np.uint8))
    return m


if __name__ == "__main__":
    crop = C2.crop_at(TF, AY)
    made = []
    for i, (n, kw) in enumerate([
        ("s1", dict(ear_gain=1.0, ymax=0.42, blur=7)),
        ("s2", dict(ear_gain=1.15, ymax=0.44, blur=9)),
        ("s3", dict(ear_gain=1.3, ymax=0.46, blur=11)),
    ]):
        blur = kw.pop("blur")
        # 自定义 soft_ear_alpha 参数
        base = Image.new("L", (S, S), 0)
        ImageDraw.Draw(base).ellipse(
            [S * (.5 - 0.455), S * (0.545 - 0.455), S * (.5 + 0.455), S * (0.545 + 0.455)],
            fill=255)
        ear = soft_ear_alpha(crop, ymax=kw["ymax"], blur=blur)
        ear_img = Image.fromarray((np.clip(ear * kw["ear_gain"], 0, 1) * 255).astype(np.uint8))
        m = Image.fromarray(np.maximum(np.asarray(base), np.asarray(ear_img)).astype(np.uint8))

        bb = m.getbbox()
        w = bb[2] - bb[0]
        sc = (S * 0.93) / w
        big = G.render(crop, m, bb, sc, seed=68000 + i * 127,
                       glow_alpha=115, glow_blur=0.020,
                       glow_grow=1.008, hairline=0, hairline_alpha=0,
                       content_scale=1.085)
        sm = big.resize((256, 256), Image.LANCZOS)
        sm.save(os.path.join(OUT, n + ".png"))
        big.save(os.path.join(OUT, "big_" + n + ".png"))
        made.append((n, sm))
        print("渲染", n)

    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 13)
    Z = 240
    sh = Image.new("RGB", (len(made) * (Z + 12) + 12, Z * 2 + 110), (20, 21, 29))
    d = ImageDraw.Draw(sh)
    d.text((12, 10), "软 alpha：保留耳朵原始渐变（上=整体，下=耳朵放大）",
           font=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16), fill=(255, 255, 255))
    for i, (n, im) in enumerate(made):
        x = 12 + i * (Z + 12)
        bg = Image.new("RGBA", (Z, Z), (226, 220, 238, 255))
        bg.alpha_composite(im.resize((Z, Z), Image.LANCZOS))
        sh.paste(bg.convert("RGB"), (x, 40))
        d.text((x + 2, 40 + Z + 2), n, font=F, fill=(230, 236, 248))
        sub = im.convert("RGBA").crop((70, 15, 205, 95)).resize((Z, Z), Image.LANCZOS)
        bg2 = Image.new("RGBA", (Z, Z), (226, 220, 238, 255))
        bg2.alpha_composite(sub)
        sh.paste(bg2.convert("RGB"), (x, 40 + Z + 40))
    sh.save(os.path.join(OUT, "preview.png"))
    print("-> preview.png")
