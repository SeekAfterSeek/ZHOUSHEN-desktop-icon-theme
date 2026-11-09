# -*- coding: utf-8 -*-
"""Plan B / Plan C 联合求解（两套方案一起分配，保证跨方案也不撞）
   硬约束：
     1 排除历史所有版本用过的照片
     2 任意两张 pHash >= 8
     3 同一连拍系列全局只用一次（B∪C 内唯一）
     4 你的颜色指令
   软目标：总分最大
"""
import sys, io, os, json, itertools
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np

ROOT = HERE
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))
PA = json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))
USED = set(json.load(open(os.path.join(ROOT, "used_history.json"), encoding="utf-8")))
# 人工审核判定的坏图（非周深 / 空舞台 / 海报 / 构图不可用）
_bp = os.path.join(ROOT, "bad_by_review.json")
BADREV = set(json.load(open(_bp, encoding="utf-8"))) if os.path.exists(_bp) else set()
USED |= BADREV
print("排除：历史 %d 张 + 坏图 %d 张" % (
    len(json.load(open(os.path.join(ROOT, "used_history.json"), encoding="utf-8"))),
    len(BADREV)))

HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]
ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

NEED = {
    "微信": [("green", 0.05)], "QQ音乐": [("yellow", 0.09)],
    "哔哩哔哩": [("pink", 0.04)], "Google Chrome": [("red", 0.075)],
    "个人 - Edge": [("cyan", 0.055), ("blue", 0.07)],
    "360安全浏览器": [("green", 0.05)], "Visual Studio Code": [("blue", 0.24)],
    "Cursor": [("black", 0.20)], "DeepSeek Harness": [("white", 0.09)],
    "Cherry Studio": [("red", 0.16)], "WorkBuddy": [("green", 0.045)],
    "WPS Office": [("red", 0.18)], "全能录屏助手": [("black", 0.22), ("red", 0.04)],
    "剪映专业版": [("black", 0.17)], "百度网盘": [("white", 0.12)],
    "飞书": [("blue", 0.16)], "Clash Verge": [("purple", 0.09)],
    "PyCharm 2026.2.3": [("black", 0.14), ("blue", 0.045)],
    "ToDesk": [("blue", 0.18)], "互传": [("blue", 0.045)],
    "网易邮箱大师": [("red", 0.16)], "联想电脑管家": [("blue", 0.24)],
    "腾讯QQ": [("black", 0.12), ("red", 0.045)], "腾讯会议": [("blue", 0.26)],
}


def ser(f):
    b = os.path.basename(f); p = b.split("_")
    if len(p) >= 3 and p[0] in ("station", "studio", "p0", "fc", "sx", "nw", "f2"):
        return "_".join(p[:2]) if p[0] in ("p0", "fc", "sx", "nw", "f2") else "_".join(p[:3])
    return b


def cos(a, b):
    va = np.array([a.get(k, 0) for k in HUES], float)
    vb = np.array([b.get(k, 0) for k in HUES], float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return 0.0 if na < 1e-9 or nb < 1e-9 else float(va.dot(vb) / (na * nb))


def comp(pal, act):
    main = [k for k, w in pal.items() if w >= 0.10] or [max(pal, key=pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


def need_ok(n, r):
    for k, th in NEED.get(n, []):
        if max(r["all"].get(k, 0), r["cloth"].get(k, 0) * 0.85) < th:
            return False
    return True


FREE = [r for r in PF if r["file"] not in USED
        and r["face_px"] >= 380 and r["sharp"] >= 11 and r["farea"] >= 0.035
        and r["hlines"] < 2 and r["vlines"] < 2
        and r["topstd"] >= 5.0 and r["botstd"] >= 5.0 and r["bright"] >= 28
        # 构图：不是远景小人，脸在画面中上部
        and r["fh2"] >= 0.055
        and 0.15 <= r["fx2"] <= 0.85
        and 0.10 <= r["fy2"] <= 0.62]
BYF = {r["file"]: r for r in FREE}
PH = {r["file"]: r.get("ph") for r in FREE}
SER = {r["file"]: ser(r["file"]) for r in FREE}
PH_ALL = {r["file"]: r.get("ph") for r in PF}
print("可用候选:", len(FREE), flush=True)

# 评分矩阵
SC = {}
for n in ORDER:
    pal = PAL[n]
    row = {}
    for r in FREE:
        c1 = cos(r["all"], pal); c2 = cos(r["cloth"], pal)
        cp = comp(pal, r["all"])
        base = (0.34 * c1 + 0.34 * c2 + 0.20 * cp
                + 0.07 * min(r["face_px"], 1100) / 1100.0
                + 0.05 * min(r["sharp"], 26) / 26.0)
        ok = need_ok(n, r)
        row[r["file"]] = (base - (0.0 if ok else 0.30), base, c1, c2, cp, ok)
    SC[n] = row
    print("  %-20s 指令满足 %3d" % (n, sum(1 for v in row.values() if v[5])), flush=True)


def dist(a, b):
    pa, pb = PH_ALL.get(a), PH_ALL.get(b)
    if pa is None or pb is None:
        return 99
    return bin(pa ^ pb).count("1")


def solve_pair(seed=0, min_d=8):
    """联合求解两套方案"""
    import random
    rnd = random.Random(seed)
    # 候选按分数排序缓存
    top = {}
    for n in ORDER:
        top[n] = sorted(((f, v[0]) for f, v in SC[n].items()), key=lambda x: -x[1])

    plan = {"B": {}, "C": {}}
    used_f, used_s = [], set()

    def ok_for(f):
        if SER[f] in used_s:
            return False
        for o in used_f:
            if dist(f, o) < min_d:
                return False
        return True

    def head(n):
        return top[n][0][1] if top[n] else -9

    # 先按稀缺度给两套方案交替分配
    order = sorted(ORDER, key=head)
    for n in order:
        for p in ("B", "C"):
            picked = None
            for f, s in top[n]:
                if ok_for(f):
                    picked = f
                    break
            if picked is None:
                for f, s in top[n]:
                    if any(dist(f, o) < 5 for o in used_f):
                        continue
                    if SER[f] in used_s:
                        continue
                    picked = f
                    break
            if picked is None:
                for f, s in top[n]:
                    if any(dist(f, o) < 3 for o in used_f):
                        continue
                    picked = f
                    break
            if picked is None:
                picked = top[n][0][0]
            plan[p][n] = picked
            used_f.append(picked)
            used_s.add(SER[picked])

    # 交换优化（同 APP 在两方案间 + 不同 APP 间）
    allslot = [(p, n) for p in ("B", "C") for n in ORDER]
    for _ in range(60):
        moved = False
        for i in range(len(allslot)):
            for j in range(i + 1, len(allslot)):
                (pa, na), (pb, nb) = allslot[i], allslot[j]
                fa, fb = plan[pa][na], plan[pb][nb]
                if fa not in SC[nb] or fb not in SC[na]:
                    continue
                before = SC[na][fa][0] + SC[nb][fb][0]
                after = SC[na][fb][0] + SC[nb][fa][0]
                if after <= before + 1e-5:
                    continue
                others = [plan[p][n] for (p, n) in allslot
                          if (p, n) not in ((pa, na), (pb, nb))]
                oser = {SER[o] for o in others}
                if SER[fb] in oser or SER[fa] in oser:
                    continue
                if any(dist(fb, o) < min_d for o in others):
                    continue
                if any(dist(fa, o) < min_d for o in others):
                    continue
                plan[pa][na], plan[pb][nb] = fb, fa
                moved = True
        if not moved:
            break
    return plan


def pack(plan, tag):
    out = {}
    for n in ORDER:
        f = plan[tag][n]
        r = BYF[f]
        v = SC[n][f]
        out[n] = {"file": r["file"], "path": r["path"], "dir": r["dir"],
                  "cloth": r["dom"], "conf": r["conf"],
                  "fx": r["fx2"], "fy": r["fy2"], "fw": r["fw2"], "fh": r["fh2"],
                  "chin": r["chin2"], "farea": r["farea"],
                  "face_px": r["face_px"], "sharp": r["sharp"], "ph": r.get("ph"),
                  "cos_all": round(v[2], 3), "cos_cloth": round(v[3], 3),
                  "complete": round(v[4], 3), "need_ok": bool(v[5]),
                  "score": round(v[1], 3), "series": SER[f]}
    return out


def verify(B, C):
    bad = 0
    det = []
    allx = [("B", n, B[n]["file"]) for n in B] + [("C", n, C[n]["file"]) for n in C]
    for i in range(len(allx)):
        for j in range(i + 1, len(allx)):
            ta, na, fa = allx[i]; tb, nb, fb = allx[j]
            if fa == fb:
                det.append(("同图", na, nb)); bad += 1; continue
            if SER[fa] == SER[fb]:
                det.append(("同系列", na, nb, fa, fb)); bad += 1; continue
            if dist(fa, fb) < 8:
                det.append(("近重复", na, nb, dist(fa, fb))); bad += 1
    hist = len({B[n]["file"] for n in B} & USED) + len({C[n]["file"] for n in C} & USED)
    return bad, det, hist


best = None
for sd in (11, 23, 37, 51, 77, 91, 113, 131):
    pl = solve_pair(seed=sd)
    B, C = pack(pl, "B"), pack(pl, "C")
    bad, det, hist = verify(B, C)
    tot = sum(B[n]["score"] for n in B) + sum(C[n]["score"] for n in C)
    okc = sum(1 for n in B if B[n]["need_ok"]) + sum(1 for n in C if C[n]["need_ok"])
    print("seed%-4d 冲突%d 历史%d 总分%.2f 指令%d/48" % (sd, bad, hist, tot, okc))
    if hist == 0 and (best is None or (bad, -tot) < (best[0], -best[1])):
        best = (bad, tot, B, C)

bad, tot, B, C = best
print("\n选定：冲突 %d  总分 %.2f" % (bad, tot))
print("\n%-20s | %-32s %-4s | %-32s %-4s" % ("APP", "Plan B", "指令", "Plan C", "指令"))
print("-" * 122)
for n in ORDER:
    print("%-20s | %-32s %-4s | %-32s %-4s" % (
        n, B[n]["file"][:32], "OK" if B[n]["need_ok"] else "NG",
        C[n]["file"][:32], "OK" if C[n]["need_ok"] else "NG"))

avgB = sum(B[n]["score"] for n in B) / 24
avgC = sum(C[n]["score"] for n in C) / 24
print("\nPlan B 平均 %.3f  最低 %.3f (%s)" % (avgB, min(B[n]["score"] for n in B),
                                              min(B, key=lambda k: B[k]["score"])))
print("Plan C 平均 %.3f  最低 %.3f (%s)" % (avgC, min(C[n]["score"] for n in C),
                                              min(C, key=lambda k: C[k]["score"])))

json.dump(B, open(os.path.join(ROOT, "planB_assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(C, open(os.path.join(ROOT, "planC_assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> planB_assign.json / planC_assign.json")
