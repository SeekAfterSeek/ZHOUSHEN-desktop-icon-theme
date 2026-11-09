# -*- coding: utf-8 -*-
"""稳健人脸检测（无 OpenCV）：连通域 + 形态学 + 形状/位置/密度/眼区多重打分
   替代早期「峰值细胞 4 邻域扩张」的过扩张写法
"""
import numpy as np
from PIL import Image


def _skin_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2); mn = a.min(axis=2)
    return ((r > 0.34) & (g > 0.14) & (b > 0.06)
            & (r > g) & (r > b)
            & ((mx - mn) > 0.05) & ((r - g) > 0.05) & ((r - b) > 0.08))


def _dilate(m, k=1):
    out = m.copy()
    for _ in range(k):
        o = out.copy()
        o[1:, :] |= out[:-1, :]; o[:-1, :] |= out[1:, :]
        o[:, 1:] |= out[:, :-1]; o[:, :-1] |= out[:, 1:]
        out = o
    return out


def _erode(m, k=1):
    return ~_dilate(~m, k)


def _components(mask, max_n=400):
    """4 邻域连通域标记，返回 [(bbox, area, pix)]"""
    H, W = mask.shape
    seen = np.zeros_like(mask, bool)
    comps = []
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys, xs):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        pix = []
        while stack:
            y, x = stack.pop()
            pix.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(pix) < 24:
            continue
        py = np.array([p[0] for p in pix]); px = np.array([p[1] for p in pix])
        y0, y1, x0, x1 = py.min(), py.max(), px.min(), px.max()
        comps.append(((x0, y0, x1, y1), len(pix), pix))
        if len(comps) >= max_n:
            break
    return comps


def _eye_score(gray, x0, y0, x1, y1):
    """眼/眉区：脸框内上部应存在暗横结构"""
    w = x1 - x0; h = y1 - y0
    if w < 6 or h < 6:
        return 0.0
    # 上部 30%~62% 高度（眼位）
    ya = y0 + int(h * 0.30); yb = y0 + int(h * 0.62)
    band = gray[ya:yb, x0:x1]
    if band.size == 0:
        return 0.0
    thr = np.percentile(band, 18)
    dark = (band <= thr).mean()
    return float(np.clip(dark / 0.22, 0, 1))


def detect_face(im, R=176):
    """返回 dict(fx,fy,fw,fh,chin,farea,conf) 或 None"""
    W, H = im.size
    a = np.asarray(im.convert("RGB").resize((R, R), Image.BILINEAR),
                   dtype=np.float32) / 255.0
    gray = np.asarray(im.convert("L").resize((R, R), Image.BILINEAR), dtype=np.float32)

    m = _skin_mask(a)
    m[int(R * 0.78):, :] = False          # 只看上半/中部
    m = _dilate(m, 1)
    m = _erode(m, 1)

    comps = _components(m)
    if not comps:
        return None

    best, best_s = None, 0.0
    for (x0, y0, x1, y1), area, pix in comps:
        w = (x1 - x0 + 1) / R
        h = (y1 - y0 + 1) / R
        if w <= 0 or h <= 0:
            continue
        area_f = area / (R * R)
        if area_f < 0.0012 or area_f > 0.23:
            continue
        asp = w / h
        if asp < 0.42 or asp > 1.85:       # 手臂/横幅排除
            continue
        cy = (y0 + y1) / 2 / R
        cx = (x0 + x1) / 2 / R
        if cy > 0.72:
            continue
        fill = area / max(1.0, (x1 - x0 + 1) * (y1 - y0 + 1))
        if fill < 0.42:                     # 脸是实心团块
            continue
        # 打分
        s_area = float(np.clip((area_f / 0.055) ** 0.5, 0, 1.35))
        s_fill = float(np.clip((fill - 0.42) / 0.40, 0, 1))
        s_asp = float(np.clip(1.0 - abs(asp - 0.86) / 0.95, 0, 1))
        s_eye = _eye_score(gray, x0, y0, x1, y1)
        s_pos = float(np.clip(1.25 - cy, 0, 1))
        s_cen = float(np.clip(1.0 - abs(cx - 0.5) * 1.15, 0, 1))
        s = (1.30 * s_area + 0.95 * s_fill + 0.85 * s_asp
             + 0.90 * s_eye + 0.55 * s_pos + 0.35 * s_cen)
        if s > best_s:
            best_s, best = s, ((x0 + x1) / 2 / R, (y0 + y1) / 2 / R,
                               w, h, y1 / R, area_f)

    if best is None:
        return None
    fx, fy, fw, fh, chin, farea = best
    # 下巴略低于皮肤块底部
    chin = min(0.99, chin + fh * 0.16)
    return {"fx": float(np.clip(fx, 0.04, 0.96)),
            "fy": float(np.clip(fy, 0.03, 0.80)),
            "fw": float(fw), "fh": float(fh),
            "chin": float(chin), "farea": float(farea),
            "face_conf": round(float(best_s), 3)}
