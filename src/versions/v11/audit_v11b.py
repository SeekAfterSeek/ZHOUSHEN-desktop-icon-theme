# -*- coding: utf-8 -*-
"""审计 v2：修正评判口径
   1) 形状 IoU：与两种模板比较，通过线 0.93
   2) 原图标相似度：图标主色(>=5%)为靶心，算加权覆盖率（比整向量余弦更贴合“像不像”）
   3) 衣服和谐：衣服区颜色 vs 图标主色（主色权重最大）
   4) 颜色齐全：只算图标主色（>=10%），且照片允许 0.5 的“近似达标”
   5) 唯一性：只报“同一张照片”级别的重复（pHash<6），并另报同系列提示（6~10）
   6) 你的逐条指令：硬性色检查
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw
import cv2
from facedet import detect_face

ROOT = HERE
DESIGN = os.path.join(ROOT, "design_v11")
BIG = os.path.join(DESIGN, "icons")
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
ASG = json.load(open(os.path.join(DESIGN, "assign.json"), encoding="utf-8"))
PF = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))}
PA = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))}

ORDER = list(ASG)
S, BADGE = 512, int(512 * 0.360)
BX = S - BADGE - int(S * 0.022)
HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]

DIRECTIVE = {
    "微信": ["green"], "QQ音乐": ["yellow"], "哔哩哔哩": ["pink"],
    "Google Chrome": ["red", "blue"], "个人 - Edge": ["cyan", "blue"],
    "360安全浏览器": ["green"], "Visual Studio Code": ["blue"],
    "Cursor": ["black"], "DeepSeek Harness": ["white"],
    "Cherry Studio": ["red"], "WorkBuddy": ["green", "cyan"],
    "WPS Office": ["red"], "全能录屏助手": ["black", "red"],
    "剪映专业版": ["black"], "百度网盘": ["white"], "飞书": ["blue"],
    "Clash Verge": ["purple"], "PyCharm 2026.2.3": ["black", "blue"],
    "ToDesk": ["blue", "white"], "互传": ["blue"], "网易邮箱大师": ["red"],
    "联想电脑管家": ["blue"], "腾讯QQ": ["black", "red"],
    "腾讯会议": ["blue"],
}


def hist(rgb, mask):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(axis=2); mn = rgb.min(axis=2)
    l = (mx + mn) / 2; dd = mx - mn + 1e-6
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


def coverage(icon_pal, act):
    """加权覆盖率：图标每个颜色（权重=占比）在照片里出现了多少"""
    tot = sum(w for k, w in icon_pal.items() if w >= 0.05)
    if tot <= 0:
        return 0.0
    sc = 0.0
    for k, w in icon_pal.items():
        if w < 0.05:
            continue
        got = act.get(k, 0)
        # 目标占比 w，命中率按 min(1, got/(w*0.55)) —— 照片天生更分散
        sc += w * min(1.0, got / max(1e-6, w * 0.55))
    return float(sc / tot)


def completeness(icon_pal, act):
    main = [k for k, w in icon_pal.items() if w >= 0.10] or [max(icon_pal, key=icon_pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


def shape_iou(alpha, shape):
    t = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(t)
    ins = int(S * 0.016)
    if shape == "circle":
        d.ellipse([ins, ins, S - 1 - ins, S - 1 - ins], fill=255)
    else:
        d.rounded_rectangle([ins, ins, S - 1 - ins, S - 1 - ins],
                            radius=int((S - 2 * ins) * 0.268), fill=255)
    tt = np.asarray(t) > 128
    aa = alpha > 128
    return float((aa & tt).sum() / max(1, (aa | tt).sum()))


def phash(im):
    g = np.asarray(im.convert("L").resize((8, 8), Image.LANCZOS), dtype=np.float32)
    v = 0
    for bit in (g > g.mean()).flatten():
        v = (v << 1) | int(bit)
    return v


rows = []
for n in ORDER:
    p = os.path.join(BIG, n + ".png")
    im = Image.open(p).convert("RGBA")
    a = np.asarray(im, dtype=np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    body = alpha > 0.5
    bm = np.zeros_like(body)
    bm[BX - 6:BX + BADGE + 6, BX - 6:BX + BADGE + 6] = True
    core = body & (~bm)
    act = hist(rgb, core)
    lum = float(rgb.mean(axis=2)[core].mean() * 255)

    ic, isq = shape_iou(alpha * 255, "circle"), shape_iou(alpha * 255, "squircle")
    shape, iou = ("circle", ic) if ic > isq else ("squircle", isq)

    src = ASG[n]["file"]
    rec = PF.get(src) or PA.get(src)
    cloth = rec["cloth"] if rec else {}
    cloth_hist = hist_from = None
    # 衣服和谐：源照片衣服直方图 vs 图标
    if rec and isinstance(rec.get("cloth"), dict):
        cp = rec["cloth"]
        tot = sum(w for k, w in PAL[n].items() if w >= 0.05) or 1
        hh = sum(w * min(1.0, cp.get(k, 0) / max(1e-6, w * 0.55))
                 for k, w in PAL[n].items() if w >= 0.05)
        cloth_h = float(hh / tot)
    else:
        cloth_h = 0.0

    cov = coverage(PAL[n], act)
    comp = completeness(PAL[n], act)
    need = DIRECTIVE.get(n, [])
    got = {k: round(act.get(k, 0), 2) for k in need}
    dir_ok = all(act.get(k, 0) >= 0.05 for k in need)

    rows.append({"name": n, "file": src, "shape": shape, "iou": round(iou, 3),
                 "coverage": round(cov, 3), "cloth": round(cloth_h, 3),
                 "complete": round(comp, 3), "lum": round(lum, 1),
                 "need": need, "got": got, "dir_ok": dir_ok,
                 "face_px": rec.get("face_px", 0) if rec else 0,
                 "ph": phash(im), "act": {k: round(v, 3) for k, v in act.items()}})

print("=" * 126)
print("%-20s %-9s %-5s %-6s %-7s %-6s %-6s %-5s %s" % (
    "APP", "形状", "IoU", "配色覆盖", "衣服和谐", "齐全", "亮度", "指令", "指令实测值"))
print("=" * 126)
F = {"cov": [], "cloth": [], "comp": [], "lum": [], "dir": [], "shape": []}
for r in rows:
    print("%-20s %-9s %-5.2f %-6.2f %-7.2f %-6.2f %-6.0f %-5s %s" % (
        r["name"], r["shape"], r["iou"], r["coverage"], r["cloth"], r["complete"],
        r["lum"], "OK" if r["dir_ok"] else "NG",
        " ".join("%s=%.2f" % (k, v) for k, v in r["got"].items())))
    if r["coverage"] < 0.62: F["cov"].append(r["name"])
    if r["cloth"] < 0.45: F["cloth"].append(r["name"])
    if r["complete"] < 0.60: F["comp"].append(r["name"])
    if r["lum"] < 70: F["lum"].append(r["name"])
    if not r["dir_ok"]: F["dir"].append(r["name"])
    if r["iou"] < 0.93: F["shape"].append(r["name"])

avg = lambda L: sum(L) / len(L)
print("\n平均：配色覆盖 %.3f  衣服和谐 %.3f  齐全 %.3f  亮度 %.0f"
      % (avg([r["coverage"] for r in rows]), avg([r["cloth"] for r in rows]),
         avg([r["complete"] for r in rows]), avg([r["lum"] for r in rows])))

print("\n" + "=" * 126)
print("不达标（临界值：配色覆盖<0.62 / 衣服<0.45 / 齐全<0.60 / 亮度<70 / 指令缺失 / IoU<0.93）")
print("=" * 126)
NM = {"cov": "配色覆盖", "cloth": "衣服和谐", "comp": "颜色齐全",
      "lum": "偏暗", "dir": "指令颜色缺失", "shape": "形状IoU"}
for k, v in F.items():
    print("  %-14s %s" % (NM[k], ", ".join(v) if v else "全部通过"))

print("\n唯一性")
ks = [r["name"] for r in rows]
ph = {r["name"]: r["ph"] for r in rows}
dup, near = [], []
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        d = bin(ph[ks[i]] ^ ph[ks[j]]).count("1")
        if d < 6:
            dup.append((ks[i], ks[j], d))
        elif d < 10:
            near.append((ks[i], ks[j], d))
print("  真重复(<6):", dup if dup else "无")
print("  同系列提示(6~9):", near if near else "无")

json.dump(rows, open(os.path.join(DESIGN, "audit2.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> audit2.json")
