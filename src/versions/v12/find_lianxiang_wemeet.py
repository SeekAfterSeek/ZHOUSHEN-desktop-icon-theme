# -*- coding: utf-8 -*-
"""为联想电脑管家 / 腾讯会议 找「亮蓝背景 + 白/浅衣 + 表情生动」的照片

原图标特征（实测）：
  联想电脑管家  blue 74.8% + white 25.4%   亮蓝渐变盾牌 + 白 L
  腾讯会议      blue 80.2% + white 20.1%   纯蓝底 + 白 M

所以照片应该是：
  - 背景明亮蓝（不是暗蓝、不是紫、不是暖色）
  - 衣服白或浅色
  - 表情生动（在笑 / 张嘴 / 有情绪），不要呆板正视
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np

ROOT = HERE
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))
USED = set(json.load(open(os.path.join(ROOT, "used_history.json"), encoding="utf-8")))
BAD = set(json.load(open(os.path.join(ROOT, "bad_by_review.json"), encoding="utf-8")).keys())

HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]


def cos(a, b):
    va = np.array([a.get(k, 0) for k in HUES], float)
    vb = np.array([b.get(k, 0) for k in HUES], float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return 0.0 if na < 1e-9 or nb < 1e-9 else float(va.dot(vb) / (na * nb))


def comp(pal, act):
    main = [k for k, w in pal.items() if w >= 0.10] or [max(pal, key=pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


def lum_of(r):
    return r.get("bright", 100)


for app in ("联想电脑管家", "腾讯会议"):
    pal = PAL[app]
    rows = []
    for r in PF:
        if r["file"] in BAD:
            continue
        # 构图与清晰度硬门槛
        if r["face_px"] < 380 or r["sharp"] < 11 or r["farea"] < 0.04:
            continue
        if r["fh2"] < 0.055 or not (0.15 <= r["fx2"] <= 0.85) or not (0.10 <= r["fy2"] <= 0.62):
            continue
        if r["hlines"] >= 2 or r["vlines"] >= 2:
            continue
        # 亮蓝背景 + 白衣
        bg_blue = r["bg"].get("blue", 0)
        bg_white = r["bg"].get("white", 0)
        cloth_white = r["cloth"].get("white", 0)
        cloth_blue = r["cloth"].get("blue", 0)
        if bg_blue < 0.22:
            continue
        if (cloth_white + cloth_blue) < 0.30:
            continue
        c1 = cos(r["all"], pal)
        c2 = cos(r["cloth"], pal)
        cp = comp(pal, r["all"])
        # 关键：亮蓝背景权重提高
        s = (0.30 * bg_blue + 0.22 * c1 + 0.22 * c2 + 0.14 * cp
             + 0.06 * min(r["face_px"], 1100) / 1100
             + 0.06 * min(r["sharp"], 26) / 26)
        rows.append((s, r))
    rows.sort(key=lambda x: -x[0])

    print("\n" + "=" * 110)
    print("=== %s  原图标 blue %.0f%% / white %.0f%% ===" % (
        app, pal.get("blue", 0) * 100, pal.get("white", 0) * 100))
    print("=" * 110)
    print("%-34s %-12s %-6s %-6s %-6s %-6s %-6s %-5s" % (
        "文件", "目录", "bg蓝", "bg白", "衣白", "衣蓝", "余弦", "脸px"))
    for s, r in rows[:16]:
        used = "*" if r["file"] in USED else " "
        print("%s%-33s %-12s %-6.2f %-6.2f %-6.2f %-6.2f %-6.2f %-5.0f  sh%s" % (
            used, r["file"], r["dir"], r["bg"].get("blue", 0), r["bg"].get("white", 0),
            r["cloth"].get("white", 0), r["cloth"].get("blue", 0),
            cos(r["all"], pal), r["face_px"], r["sharp"]))
    json.dump([r["file"] for s, r in rows[:40]],
              open(os.path.join(ROOT, "_cand_%s.json" % app), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("（* = 历史版本用过）候选 %d 张" % len(rows))
