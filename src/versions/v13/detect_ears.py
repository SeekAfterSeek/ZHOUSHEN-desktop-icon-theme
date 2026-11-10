# -*- coding: utf-8 -*-
"""检测裁剪画面里两只毛绒耳朵的位置，用于生成贴合耳朵的轮廓"""
import sys
import io
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from facedet import detect_face
import render_p20 as RP

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
OUT = os.path.join(ROOT, "_ear_mask")
os.makedirs(OUT, exist_ok=True)
SRC = os.path.join(LIB, "photos_2026__station_20261017_31971_5.jpg")
S = RP.S


def make_crop(tf=0.28, anchor_y=0.52):
    im = Image.open(SRC).convert("RGB")
    W, H = im.size
    d = detect_face(im) or {"fx": .5, "fy": .30, "fw": .22, "fh": .22}
    face_h = d["fh"] * H
    crop = face_h / tf
    crop = max(S * 0.6, min(crop, float(min(W, H))))
    sc = S / crop
    nw, nh = max(S, int(round(W * sc))), max(S, int(round(H * sc)))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    cx, cy = d["fx"] * nw, d["fy"] * nh
    left = max(0, min(int(round(cx - S * 0.50)), nw - S))
    top = max(0, min(int(round(cy - S * anchor_y)), nh - S))
    return im2.crop((left, top, left + S, top + S))


def detect_ears(crop):
    """橙色毛绒区域 → 左右两只耳朵的包围盒（归一化）"""
    a = np.asarray(crop.convert("RGB"))
    hsv = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    # 橙/棕毛色：H 3-30(度*2 → 0-180制约 5-40)，饱和够、不过暗
    m = ((h >= 4) & (h <= 32) & (s >= 70) & (v >= 70)).astype(np.uint8)
    # 只看上半部（耳朵区域）
    m[int(S * 0.42):, :] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(m, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, hh, area = stats[i]
        if area < S * S * 0.004:
            continue
        boxes.append((x / S, y / S, w / S, hh / S, area))
    boxes.sort(key=lambda b: -b[4])
    left = [b for b in boxes if b[0] + b[2] / 2 < 0.52]
    right = [b for b in boxes if b[0] + b[2] / 2 >= 0.48]
    out = []
    for grp in (left, right):
        if not grp:
            out.append(None); continue
        x0 = min(b[0] for b in grp); y0 = min(b[1] for b in grp)
        x1 = max(b[0] + b[2] for b in grp); y1 = max(b[1] + b[3] for b in grp)
        out.append((x0, y0, x1, y1))
    return out, m


if __name__ == "__main__":
    crop = make_crop()
    boxes, m = detect_ears(crop)
    print("左耳:", boxes[0])
    print("右耳:", boxes[1])

    # 可视化
    vis = crop.convert("RGB").copy()
    dd = ImageDraw.Draw(vis)
    for b in boxes:
        if b:
            dd.rectangle([b[0] * S, b[1] * S, b[2] * S, b[3] * S], outline=(0, 255, 120), width=3)
    vis.save(os.path.join(OUT, "ears_vis.png"))
    Image.fromarray((m * 255)).save(os.path.join(OUT, "ears_mask.png"))
    crop.save(os.path.join(OUT, "crop.png"))
    print("-> ears_vis.png")
