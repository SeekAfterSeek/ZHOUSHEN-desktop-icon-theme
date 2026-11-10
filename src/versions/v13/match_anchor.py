# -*- coding: utf-8 -*-
"""人脸锚点归一化匹配 —— 快且对裁剪/缩放免疫

思路：
  截图是原图的局部裁剪，但两者的「人脸尺度」比例是确定的。
  以人脸为锚点，取 3.0×脸高 的方形区域归一化到 96×96，
  截图与原图的同一块区域就会对齐，再做归一化互相关即可。
  同时用该区域的色彩直方图区分不同服装/背景。

速度：YuNet 检测 4346 张 ≈ 十几秒（8 进程），比对 20×4346 纯 numpy ≈ 数秒。
"""
import sys, io, os, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import cv2
from multiprocessing import Pool

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
LIB = r"D:\DSH\workspace\SMALL RESULT\周深原始照片库"
ATT = r"C:\Users\Lenovo\.dsh\attachments\v1\objects"
CACHE = os.path.join(ROOT, "_face_anchor.json")

sys.path.insert(0, ROOT)
from facedet import detect_face

SHOTS = {
    "P1_edge":    "c2d007c4a19475c04308e66fcd72e6026b4e495a944370a42ab81a645511c7c3",
    "P2_lenovo":  "e09385f809e296940380860a52154b1d4a1738ac6f192f0245948aad77d3563f",
    "P3_vsc":     "8137dd779848cc3152812139c0fd31d14316ffc19353e08700bcd1f387a74403",
    "P4_bili":    "5e05a62c320920a93fa47efe1295cecf6a5a8064102df6c62383688c8aceeb11",
    "P5_wb":      "45bd7a06e06c5e52121f53049ca52065acd2bdd9ae85b2ad60131e77c4622f39",
    "P6_meituan": "3e1b22b06d35e759425d6679c9deffba0148d2cff5b77bdd8d1ca415b65dff69",
    "P7_huchuan": "982ecfbdc1808e5c4f499d4bb8c5375c0b4a36687627af53dae2619245667e8d",
    "P8_bili":    "0e4dfa43692b5ee9aa9b5d1a0c0adcf47a3d9bea3c49114bb09e7f9de6343bc1",
    "P9_bili":    "235313dc9b9d036811fac29ed13e6013bdf89e84477da7e144605ce36776d10f",
    "P10_dsh":    "ad33735de0bc6c29031f9d25703f8ea0cac05f2b82a68aecc80c3c740422189b",
    "P11_dsh":    "a8f66283746325f1a6aded57730afc2d0b536d5114df548b23a948d4f854e226",
    "P12_dsh":    "8ccda653d15ff83f5f548c22d22d273b4ef23603b755b4249044d528a25f43a5",
    "P13_dsh":    "7804e5998cddf7ae57cd3aa7f245ff01107df1ed131959b976a88b7c6ec8b94c",
    "P14_dsh":    "916c9b6bd31ee5260277422b20d9e31da1efd8fe8fd576867a6b5f7194ea9906",
    "P15_wb":     "ef290b5af402c62cba5ad70bd3d68d84f9e5be7d860c7831ec2a7474da150cef",
    "P16_dsh":    "80a84c81d0e358f48d7e0fddeb7af7c049a690c2f299291f0ec1f25c31283a28",
    "P17_todesk": "102187882598535f39c66fb792946847a980acea3b8bdb1c8e47848f9a928caf",
    "P18_huchuan":"f9790ffc776703d2417016978c76b123343125be2a927519b343bb4a647eed0d",
    "P19_todesk": "e271db85bb1b9d90b1a9047f276612b411fa4a5555025742d43096bad3d08405",
    "P20_qq":     "979695cdd419f5c398dd98c0a443b72f083ec8cd0371726f1b4e751fcf38dc57",
}

PATCH = 96          # 归一化补丁边长
SIDE_K = 3.0        # 补丁边长 = 3.0 × 脸高


def imread_bgr(p):
    try:
        b = np.fromfile(p, np.uint8)
        return cv2.imdecode(b, cv2.IMREAD_COLOR) if b.size else None
    except Exception:
        return None


def find_att(sha):
    p = os.path.join(ATT, sha[:2], sha[2:4], sha)
    if os.path.exists(p):
        return p
    for dp, dn, fn in os.walk(ATT):
        for f in fn:
            if f.startswith(sha[:20]):
                return os.path.join(dp, f)
    return None


def anchor_patch(bgr):
    """以人脸为锚点取归一化补丁，返回 (gray96, hsv_hist)"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    from PIL import Image as I
    d = detect_face(I.fromarray(rgb))
    if not d:
        return None, None
    H, W = bgr.shape[:2]
    fh = d["fh"] * H
    cx = (d["fx"] + d["fw"] / 2) * W
    cy = (d["fy"] + d["fh"] * 0.55) * H
    side = max(24, SIDE_K * fh)
    x0, y0 = int(cx - side / 2), int(cy - side / 2)
    x1, y1 = int(x0 + side), int(y0 + side)
    # 越界补边（复制边缘）
    padx0 = max(0, -x0); pady0 = max(0, -y0)
    padx1 = max(0, x1 - W); pady1 = max(0, y1 - H)
    crop = bgr[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    if crop.size == 0:
        return None, None
    crop = cv2.copyMakeBorder(crop, pady0, pady1, padx0, padx1, cv2.BORDER_REPLICATE)
    crop = cv2.resize(crop, (PATCH, PATCH), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [18, 8], [0, 180, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return gray.astype(np.float32), hist


def _lib_worker(p):
    bgr = imread_bgr(p)
    if bgr is None:
        return None
    g, h = anchor_patch(bgr)
    if g is None:
        return None
    return p, g.astype(np.float16), h.astype(np.float16)


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-6 or nb < 1e-6:
        return 0.0
    return float((a * b).sum() / (na * nb))


def main():
    t0 = time.time()
    # 1. 截图补丁
    shots = {}
    for k, sha in SHOTS.items():
        p = find_att(sha)
        if not p:
            print("✗", k); continue
        bgr = imread_bgr(p)
        if bgr is None:
            print("✗ 解码", k); continue
        g, h = anchor_patch(bgr)
        if g is None:
            print("✗ 无脸", k); continue
        shots[k] = {"path": p, "g": g, "h": h, "size": (bgr.shape[1], bgr.shape[0])}
        print("✓ %-12s %dx%d 补丁OK" % (k, bgr.shape[1], bgr.shape[0]), flush=True)
    print("\n截图 %d\n" % len(shots), flush=True)

    # 2. 库补丁（缓存）
    files = []
    for dp, dn, fn in os.walk(LIB):
        for f in fn:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                files.append(os.path.join(dp, f))
    files.sort()
    print("库文件 %d" % len(files), flush=True)

    if os.path.exists(CACHE):
        cached = json.load(open(CACHE, encoding="utf-8"))
        if cached.get("n") == len(files):
            print("载入缓存 %d" % len(cached["paths"]), flush=True)
            G = np.load(os.path.join(ROOT, "_anchor_g.npy"))
            Hh = np.load(os.path.join(ROOT, "_anchor_h.npy"))
            paths = cached["paths"]
        else:
            cached = None
    else:
        cached = None

    if not cached:
        t1 = time.time()
        paths, Gs, Hs = [], [], []
        with Pool(8) as mp:
            for i, r in enumerate(mp.imap_unordered(_lib_worker, files, chunksize=6)):
                if r is not None:
                    p, g, h = r
                    if g.shape != (PATCH, PATCH):
                        continue
                    paths.append(p); Gs.append(g); Hs.append(h)
                if (i + 1) % 500 == 0:
                    print("  %d/%d 有效%d %.0fs" % (i + 1, len(files), len(paths),
                                                    time.time() - t1), flush=True)
        G = np.stack(Gs).astype(np.float32)
        Hh = np.stack(Hs).astype(np.float32)
        np.save(os.path.join(ROOT, "_anchor_g.npy"), G.astype(np.float16))
        np.save(os.path.join(ROOT, "_anchor_h.npy"), Hh.astype(np.float16))
        json.dump({"paths": paths, "n": len(files)},
                  open(CACHE, "w", encoding="utf-8"))
        print("库补丁完成 %d 张 %.0fs" % (len(paths), time.time() - t1), flush=True)
    else:
        G = G.astype(np.float32)
        Hh = Hh.astype(np.float32)

    # 3. 比对
    Gz = G - G.mean(axis=(1, 2), keepdims=True)
    Gn = np.linalg.norm(Gz.reshape(len(G), -1), axis=1)
    Gn[Gn < 1e-6] = 1e-6
    Gn = Gn.reshape(-1, 1, 1)

    result = {}
    print("\n=== 比对 ===")
    for k, s in shots.items():
        q = s["g"] - s["g"].mean()
        qn = np.linalg.norm(q)
        sims = (Gz * q[None]).sum(axis=(1, 2)) / (Gn.ravel() * qn)
        # 直方图相似
        hsim = 1.0 - 0.5 * np.abs(Hh - s["h"][None]).sum(axis=1)
        score = 0.62 * sims + 0.38 * hsim
        idx = np.argsort(-score)[:8]
        lst = []
        for i in idx:
            lst.append({"score": round(float(score[i]), 4),
                        "ncc": round(float(sims[i]), 4),
                        "hist": round(float(hsim[i]), 4),
                        "path": paths[i],
                        "file": os.path.basename(paths[i]),
                        "dir": os.path.basename(os.path.dirname(paths[i]))})
        result[k] = {"shot": s["path"], "size": list(s["size"]), "top": lst}
        print("\n[%s] %s" % (k, s["size"]))
        for r in lst[:5]:
            print("   %.4f (ncc %.3f hist %.3f)  %s" % (
                r["score"], r["ncc"], r["hist"], r["file"][:46]))

    json.dump(result, open(os.path.join(ROOT, "_shot_anchor.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n总耗时 %.0fs -> _shot_anchor.json" % (time.time() - t0))


if __name__ == "__main__":
    main()
