# -*- coding: utf-8 -*-
"""为每个 APP 搜索最优调色强度：在最终图标上实测余弦/齐全度，选综合最优
   同时给出“该不该换图”的判据
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from facedet import detect_face
from grade_lib import grade

ROOT = HERE
DESIGN = os.path.join(ROOT, "design_v11")
ORIG = os.path.join(ROOT, "backup", "original-icons-256")
ASG = json.load(open(os.path.join(DESIGN, "assign.json"), encoding="utf-8"))
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))}
PA = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))}

S = 512
BADGE = int(S * 0.360)
BX = S - BADGE - int(S * 0.022)
HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]
TARGET_FACE = 0.46
STRENGTHS = [0.0, 0.22, 0.38, 0.52, 0.66, 0.80, 0.92, 1.0]


def hist_of(rgb, mask):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    l = (mx + mn) / 2
    dd = mx - mn + 1e-6
    s = np.where(mx == mn, 0, dd / np.maximum(1e-6, 1 - np.abs(2 * l - 1)))
    h = np.where(mx == r, ((g - b) / dd) % 6,
                 np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60
    n = float(mask.sum()) or 1.0
    ev = {"black": float(((l < 0.11) & mask).sum() / n),
          "white": float(((l > 0.87) & mask).sum() / n),
          "gray": float(((s < 0.19) & (l >= 0.11) & (l <= 0.87) & mask).sum() / n)}
    ok = (s >= 0.20) & (l >= 0.08) & (l <= 0.94) & mask
    for k, (lo, hi) in zip(HUES[3:], [(345, 15), (15, 40), (40, 70), (70, 165),
                                      (165, 200), (200, 265), (265, 310), (310, 345)]):
        mm = (((h >= lo) | (h < hi)) & ok) if lo > hi else ((h >= lo) & (h < hi) & ok)
        ev[k] = float(mm.sum() / n)
    return ev


def cos(a, b):
    va = np.array([a.get(k, 0) for k in HUES], float)
    vb = np.array([b.get(k, 0) for k in HUES], float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return 0.0 if na < 1e-9 or nb < 1e-9 else float(va.dot(vb) / (na * nb))


def complete(pal, act):
    main = [k for k, w in pal.items() if w >= 0.10] or [max(pal, key=pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


def skin_mask_of(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    return ((r > 0.34) & (g > 0.14) & (b > 0.06) & (r > g) & (r > b)
            & ((mx - mn) > 0.05) & ((r - g) > 0.05) & ((r - b) > 0.08))


def head_protect(S_, d, grow=1.55):
    yy, xx = np.mgrid[0:S_, 0:S_]
    cx = d["fx"] * S_
    cy = d["fy"] * S_ - max(d["fh"] * S_ * grow * 0.72, S_ * 0.13) * 0.18
    rw = max(d["fw"] * S_ * grow * 0.60, S_ * 0.11)
    rh = max(d["fh"] * S_ * grow * 0.72, S_ * 0.13)
    return ((xx - cx) / rw) ** 2 + ((yy - cy) / rh) ** 2 <= 1.0


def crop_for(name, info):
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
    dx = (d["fx"] * nw - left) / S
    dy = (d["fy"] * nh - top) / S
    dh = {"fx": dx, "fy": dy, "fw": d["fw"] * nw / S, "fh": d["fh"] * nh / S}
    return cv, dh


def measure(rgb, pal):
    """rgb: uint8 HxWx3，只统计主体区（排除角标）"""
    a = rgb.astype(np.float32) / 255.0
    m = np.ones(a.shape[:2], bool)
    m[BX - 6:BX + BADGE + 6, BX - 6:BX + BADGE + 6] = False
    act = hist_of(a, m)
    return act, cos(act, pal), complete(pal, act)


best, report = {}, []
for n, info in ASG.items():
    pal = PAL[n]
    cv, dh = crop_for(n, info)
    arr = np.asarray(cv, dtype=np.float32) / 255.0
    prot = skin_mask_of(arr) | head_protect(S, dh)
    src = info["file"]
    rec = PF.get(src) or PA.get(src)
    cloth = rec["cloth"] if rec else {}

    rows = []
    for st in STRENGTHS:
        a2 = arr if st <= 0 else grade(arr, pal, skin_mask=prot, strength=st)
        rgb = (np.clip(a2, 0, 1) * 255).astype(np.uint8)
        act, cs, cp = measure(rgb, pal)
        lum = float(rgb.mean())
        rows.append({"strength": st, "cos": cs, "complete": cp, "lum": lum, "act": act})

    def sc(r):
        pen = 0.0
        if r["lum"] < 62:
            pen += (62 - r["lum"]) / 160.0
        if r["lum"] > 205:
            pen += (r["lum"] - 205) / 260.0
        return 0.62 * r["cos"] + 0.38 * r["complete"] - pen

    rows.sort(key=lambda r: -sc(r))
    b = rows[0]
    best[n] = round(b["strength"], 2)
    base = next(r for r in rows if r["strength"] == 0)
    report.append((n, base["cos"], base["complete"], b["strength"], b["cos"],
                   b["complete"], b["lum"]))
    print("%-20s 不调色 cos%.2f 齐全%.2f | 最优强度%.2f -> cos%.2f 齐全%.2f 亮度%.0f"
          % (n, base["cos"], base["complete"], b["strength"], b["cos"],
             b["complete"], b["lum"]))

json.dump(best, open(os.path.join(DESIGN, "grade_strength.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("\n=== 仍不达标（cos<0.60 或 齐全<0.66）需换图 ===")
for n, c0, p0, st, c1, p1, l in report:
    if c1 < 0.60 or p1 < 0.66:
        print("  %-20s cos%.2f 齐全%.2f" % (n, c1, p1))
