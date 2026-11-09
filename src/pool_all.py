# -*- coding: utf-8 -*-
"""全量候选池：扫磁盘所有源图（排除输出目录），提取
   衣服色 / 背景色 / 整图色 / 人脸bbox / 清晰度 / 构图指标
"""
import sys, io, os, json, time
import numpy as np
from PIL import Image
from multiprocessing import Pool as MPool

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
SRC_DIRS = ["picks", "xhs_all_picks", "forcharlie_picks", "studio_xhs_src",
            "xhs_new_src", "xhs_all", "photos_2026", "photos", "fc2_src",
            "xhs_src", "xhs_picks", "xhs_b_src", "xhs_b_picks",
            "forcharlie_src", "FINAL_200"]
EXTS = (".jpg", ".jpeg", ".png", ".webp")
HUES = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "pink"]


def _hsv(rgb):
    mx = rgb.max(axis=2); mn = rgb.min(axis=2); l = (mx + mn) / 2
    dd = mx - mn + 1e-6
    s = np.where(mx == mn, 0, dd / np.maximum(1e-6, 1 - np.abs(2 * l - 1)))
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / dd) % 6,
                 np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60
    return h, s, l


def _hist(rgb, skin=None):
    """返回 11 维颜色占比（统一分母 = 区域像素数）"""
    h, s, l = _hsv(rgb)
    n = float(rgb.shape[0] * rgb.shape[1])
    if skin is None:
        skin = np.zeros(rgb.shape[:2], bool)
    noskin = ~skin
    ev = {}
    ev["black"] = float(((l < 0.11) & noskin).sum() / n)
    ev["white"] = float(((l > 0.87) & noskin).sum() / n)
    ev["gray"] = float(((s < 0.19) & (l >= 0.11) & (l <= 0.87) & noskin).sum() / n)
    ok = (s >= 0.20) & (l >= 0.08) & (l <= 0.94) & noskin
    for k, (lo, hi) in zip(HUES, [(345, 15), (15, 40), (40, 70), (70, 165),
                                  (165, 200), (200, 265), (265, 310), (310, 345)]):
        m = (((h >= lo) | (h < hi)) & ok) if lo > hi else ((h >= lo) & (h < hi) & ok)
        ev[k] = float(m.sum() / n)
    return ev


def _skin_mask(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2); mn = a.min(axis=2)
    return ((r > 0.36) & (g > 0.15) & (b > 0.07) & (r > g) & (r > b)
            & ((mx - mn) > 0.055) & ((r - g) > 0.055) & ((r - b) > 0.09))


def _face_box(skin, R):
    """粗粒度聚类求人脸 bbox；失败返回 None"""
    n = skin.sum()
    if n < 30:
        return None
    G = R // 8                      # 16x16 细胞
    cells = skin[:G * 8, :G * 8].reshape(G, 8, G, 8).sum(axis=(1, 3)) / 64.0
    if cells.max() < 0.18:
        return None
    best = np.unravel_index(np.argmax(cells), cells.shape)
    thr = cells.max() * 0.45
    keep = cells >= thr
    # 从峰值细胞做 4 邻域扩张
    sel = np.zeros_like(keep)
    sel[best] = True
    for _ in range(60):
        nxt = sel.copy()
        nxt[1:, :] |= sel[:-1, :]; nxt[:-1, :] |= sel[1:, :]
        nxt[:, 1:] |= sel[:, :-1]; nxt[:, :-1] |= sel[:, 1:]
        nxt &= keep
        if (nxt == sel).all():
            break
        sel = nxt
    ys, xs = np.nonzero(sel)
    if len(ys) == 0:
        return None
    y0, y1 = ys.min() / G, (ys.max() + 1) / G
    x0, x1 = xs.min() / G, (xs.max() + 1) / G
    if (y1 - y0) < 0.05 or (x1 - x0) < 0.03:
        return None
    return float(x0), float(y0), float(x1), float(y1)


def analyze(path):
    try:
        im = Image.open(path)
        W, H = im.size
        # JPEG 快速解码到 1/4
        try:
            im.draft("RGB", (max(64, W // 4), max(64, H // 4)))
        except Exception:
            pass
        im = im.convert("RGB")
    except Exception:
        return None
    if min(W, H) < 360:
        return None
    R = 160
    imr = im.resize((R, R), Image.BILINEAR)
    a = np.asarray(imr, dtype=np.float32) / 255.0

    skin = _skin_mask(a)
    skin[int(R * 0.66):, :] = False
    fb = _face_box(skin, R)

    # ---- 人脸 ----
    if fb:
        x0, y0, x1, y1 = fb
        fx, fy = (x0 + x1) / 2, (y0 + y1) / 2
        fw, fh = x1 - x0, y1 - y0
        farea = max(0.0, fw * fh)
    else:
        # 退化：用蒙版质心
        ys, xs = np.nonzero(skin)
        if len(ys) < 25:
            return None
        fx = float(np.clip(np.median(xs) / R, .12, .88))
        fy = float(np.clip(np.median(ys) / R, .08, .60))
        fw = fh = 0.10
        farea = 0.01

    # ---- 衣服区：下巴以下 ----
    chin = (y1 if fb else fy + fh * .5)
    ty0 = int(np.clip((chin + 0.015) * R, 0, R - 10))
    ty1 = int(np.clip((chin + 0.50) * R, ty0 + 10, R - 1)) if fb else int(R * .95)
    half = max(fw * 0.95, 0.135)
    tx0 = int(np.clip((fx - half) * R, 0, R - 12))
    tx1 = int(np.clip((fx + half) * R, tx0 + 12, R))
    if ty1 - ty0 < 10 or tx1 - tx0 < 10:
        ty0, ty1 = int(R * .35), int(R * .85)
        tx0, tx1 = int(R * .25), int(R * .75)
    cloth_rgb = a[ty0:ty1, tx0:tx1]
    cloth_skin = _skin_mask(cloth_rgb)
    cloth = _hist(cloth_rgb, cloth_skin)

    # ---- 背景：外框 9% 环 ----
    B = max(4, int(R * 0.09))
    ring = np.ones((R, R), bool)
    ring[B:R - B, B:R - B] = False
    bg_rgb = a[ring]
    bg = _hist(bg_rgb.reshape(-1, 1, 3)) if bg_rgb.size else cloth

    # ---- 整图 ----
    full = _hist(a, skin)

    # ---- 清晰度（拉普拉斯方差）----
    g = np.asarray(im.convert("L"), dtype=np.float32)
    if g.shape[0] > 400:
        g = g[::max(1, g.shape[0] // 400), ::max(1, g.shape[1] // 400)]
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1]
                 - g[1:-1, :-2] - g[1:-1, 2:])
    sharp = float(lap.mean())
    bright = float(g.mean())

    # ---- 构图 ----
    g64 = np.asarray(im.convert("L").resize((128, 128)), dtype=np.float32)
    hl = int((np.abs(np.diff(g64, axis=0)).mean(axis=1) > 60).sum())
    vl = int((np.abs(np.diff(g64, axis=1)).mean(axis=0) > 60).sum())

    # 顶部/底部纯色条（海报、拼图、截图特征）
    top_bar = float(np.asarray(im.convert("L").resize((64, 64)), dtype=np.float32)[:6].std())
    bot_bar = float(np.asarray(im.convert("L").resize((64, 64)), dtype=np.float32)[-6:].std())

    dom = max(cloth, key=cloth.get)
    return {
        "path": path, "file": os.path.basename(path),
        "dir": os.path.basename(os.path.dirname(path)),
        "w": W, "h": H,
        "cloth": {k: round(v, 3) for k, v in cloth.items()},
        "bg": {k: round(v, 3) for k, v in bg.items()},
        "all": {k: round(v, 3) for k, v in full.items()},
        "dom": dom, "conf": round(cloth[dom], 3),
        "fx": round(fx, 3), "fy": round(fy, 3),
        "fw": round(fw, 3), "fh": round(fh, 3),
        "farea": round(farea, 4),
        "chin": round(chin, 3),
        "sharp": round(sharp, 1), "bright": round(bright, 1),
        "hlines": hl, "vlines": vl,
        "topstd": round(top_bar, 1), "botstd": round(bot_bar, 1),
        "hasface": bool(fb),
    }


def _work(p):
    try:
        return analyze(p)
    except Exception:
        return None


if __name__ == "__main__":
    t0 = time.time()
    files = []
    for d in SRC_DIRS:
        dd = os.path.join(ROOT, d)
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd)):
            if f.lower().endswith(EXTS):
                files.append(os.path.join(dd, f))
    # 按 (basename, size) 去重：同一文件可能被复制到多目录
    uniq, seen = [], {}
    for p in files:
        try:
            sz = os.path.getsize(p)
        except Exception:
            continue
        k = (os.path.basename(p), sz)
        if k in seen:
            continue
        seen[k] = 1
        uniq.append(p)
    print("files on disk:", len(files), "-> unique:", len(uniq), flush=True)

    with MPool(8) as mp:
        res = []
        for i, r in enumerate(mp.imap_unordered(_work, uniq, chunksize=8)):
            if r:
                res.append(r)
            if (i + 1) % 400 == 0:
                print("  %d/%d  kept=%d  %.0fs" % (i + 1, len(uniq), len(res), time.time() - t0), flush=True)

    # 感知哈希去重（8x8 均值哈希）
    def ahash(p):
        try:
            im = Image.open(p)
            im.draft("L", (16, 16))
            g = np.asarray(im.convert("L").resize((8, 8)), dtype=np.float32)
            return (g > g.mean()).flatten().astype(np.uint8)
        except Exception:
            return None

    from collections import defaultdict
    out, buckets = [], defaultdict(list)
    for r in res:
        h = ahash(r["path"])
        if h is None:
            continue
        key = int("".join(map(str, h.tolist())), 2)
        dup = False
        for prev in buckets.get(key, [])[:40]:
            if bin(prev ^ key).count("1") <= 3:
                dup = True
                break
        if dup:
            continue
        buckets[key].append(key)
        out.append(r)

    print("analyzed:", len(res), " after phash dedupe:", len(out),
          "  %.0fs" % (time.time() - t0), flush=True)
    json.dump(out, open(os.path.join(ROOT, "pool_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    from collections import Counter
    print("dir mix:", dict(Counter(r["dir"] for r in out).most_common()))
    print("cloth dom:", dict(Counter(r["dom"] for r in out).most_common()))
    print("with face:", sum(1 for r in out if r["hasface"]))
    print("DONE %.0fs" % (time.time() - t0))
