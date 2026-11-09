# -*- coding: utf-8 -*-
"""全局最优分配：每个 APP 按 ①原图标余弦 ②衣服余弦 ③脸够大 选图
   + 全局唯一（pHash>=10）+ 你的逐条颜色指令 + 你点名沿用的固定项
   用匈牙利近似（贪心+迭代交换）求解
"""
import sys, io, os, json, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np

ROOT = HERE
DESIGN = os.path.join(ROOT, "design_v11")
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))
ASG = json.load(open(os.path.join(DESIGN, "assign.json"), encoding="utf-8"))

HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]

ORDER = ["微信", "QQ音乐", "哔哩哔哩", "Google Chrome", "个人 - Edge", "360安全浏览器",
         "Visual Studio Code", "Cursor", "DeepSeek Harness", "Cherry Studio", "WorkBuddy",
         "WPS Office", "全能录屏助手", "剪映专业版", "百度网盘", "飞书", "Clash Verge",
         "PyCharm 2026.2.3", "ToDesk", "互传", "网易邮箱大师", "联想电脑管家",
         "腾讯QQ", "腾讯会议"]

# 你点名“沿用/就这个”的，直接锁定
PIN = {
    "微信": "sx_0295.jpg",
    "QQ音乐": "p0_0108_1.jpg",
    "哔哩哔哩": "p0_0201_1.jpg",
    "WPS Office": "studio_20261004_85716_6.jpg",
    "百度网盘": "sx_0505.jpg",
    "互传": "studio_20260928_23430_0.jpg",
    "联想电脑管家": "station_20260524_50364_6.jpg",
    "腾讯会议": "c929b_c824162da8.jpg",
}
# 硬性颜色要求（缺了直接判不合格）
NEED = {
    "个人 - Edge": [("cyan", 0.20), ("blue", 0.12)],
    "360安全浏览器": [("green", 0.18)],
    "Visual Studio Code": [("blue", 0.45)],
    "Cursor": [("black", 0.35)],
    "DeepSeek Harness": [("white", 0.15)],
    "Cherry Studio": [("red", 0.30)],
    "WorkBuddy": [("green", 0.10)],
    "全能录屏助手": [("black", 0.42), ("red", 0.06)],
    "剪映专业版": [("black", 0.34)],
    "飞书": [("blue", 0.30)],
    "Clash Verge": [("purple", 0.15)],
    "PyCharm 2026.2.3": [("black", 0.22)],
    "ToDesk": [("blue", 0.30)],
    "网易邮箱大师": [("red", 0.30)],
    "腾讯QQ": [("black", 0.20), ("red", 0.08)],
    "Google Chrome": [("red", 0.14)],
}


def cos(a, b):
    va = np.array([a.get(k, 0) for k in HUES], float)
    vb = np.array([b.get(k, 0) for k in HUES], float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return 0.0 if na < 1e-9 or nb < 1e-9 else float(va.dot(vb) / (na * nb))


def complete(pal, act):
    main = [k for k, w in pal.items() if w >= 0.10] or [max(pal, key=pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


def usable(r, min_fpx):
    if r["face_px"] < min_fpx:
        return False
    if r["sharp"] < 9:
        return False
    if r["farea"] < 0.025:
        return False
    if r["hlines"] >= 2 or r["vlines"] >= 2:
        return False
    if r["topstd"] < 5.5 or r["botstd"] < 5.5:
        return False
    if r["bright"] < 30:
        return False
    return True


def need_ok(name, r):
    for k, th in NEED.get(name, []):
        got = max(r["all"].get(k, 0), r["cloth"].get(k, 0) * 0.9)
        if got < th:
            return False
    return True


# ---------- 打分矩阵 ----------
CAND = [r for r in PF if usable(r, 330)]
# 锁定项可能尺寸偏小，单独纳入
for n, f in PIN.items():
    rr = next((x for x in PF if x["file"] == f), None)
    if rr and rr not in CAND:
        CAND.append(rr)
print("候选:", len(CAND))
print("锁定:", len(PIN))

score = {}
for n in ORDER:
    pal = PAL[n]
    row = {}
    for r in CAND:
        if not need_ok(n, r):
            continue
        c1 = cos(r["all"], pal)
        c2 = cos(r["cloth"], pal)
        cp = complete(pal, r["all"])
        fpx = min(r["face_px"], 1200) / 1200.0
        sh = min(r["sharp"], 28) / 28.0
        # 权重：原图标相似度 .34 + 衣服和谐 .34 + 颜色齐全 .20 + 脸 .07 + 清晰 .05
        s = 0.34 * c1 + 0.34 * c2 + 0.20 * cp + 0.07 * fpx + 0.05 * sh
        row[r["file"]] = (s, c1, c2, cp)
    score[n] = row
    print("  %-20s 合格候选 %4d" % (n, len(row)))

# ---------- 分配 ----------
chosen = {}
ph_of = {r["file"]: r.get("ph") for r in PF}
for n, f in PIN.items():
    chosen[n] = f
used = {f: n for n, f in chosen.items()}


def conflict(f, other):
    pa, pb = ph_of.get(f), ph_of.get(other)
    if pa is None or pb is None:
        return False
    return bin(pa ^ pb).count("1") < 10


rest = [n for n in ORDER if n not in chosen]
# 稀缺优先
rest.sort(key=lambda n: max((v[0] for v in score[n].values()), default=-1))

for n in rest:
    cands = sorted(((f, v) for f, v in score[n].items() if f not in used),
                   key=lambda x: -x[1][0])
    pick = None
    for f, v in cands:
        if any(conflict(f, o) for o in used):
            continue
        pick = f
        break
    if pick is None and cands:
        pick = cands[0][0]
        print("  !! %s 放宽唯一性" % n)
    if pick is None:
        print("  !! %s 无候选" % n)
        continue
    chosen[n] = pick
    used[pick] = n

# ---------- 迭代交换优化 ----------
def total(exclude):
    return sum(score[n][chosen[n]][0] for n in ORDER
               if n in chosen and n not in exclude and chosen[n] in score[n])


LOCK = set(PIN)
improved = True
rounds = 0
while improved and rounds < 24:
    improved = False
    rounds += 1
    for a in ORDER:
        if a in LOCK or a not in chosen:
            continue
        for b in ORDER:
            if b in LOCK or b == a or b not in chosen:
                continue
            fa, fb = chosen[a], chosen[b]
            if fa not in score[b] or fb not in score[a]:
                continue
            before = score[a][fa][0] + score[b][fb][0]
            after = score[a][fb][0] + score[b][fa][0]
            if after > before + 1e-4:
                # 换后还要通过唯一性
                others = [chosen[k] for k in chosen if k not in (a, b)]
                if any(conflict(fb, o) for o in others):
                    continue
                if any(conflict(fa, o) for o in others):
                    continue
                chosen[a], chosen[b] = fb, fa
                improved = True

print("\n=== 全局最优分配 ===")
tot = 0.0
out = {}
for n in ORDER:
    f = chosen[n]
    r = next((x for x in PF if x["file"] == f), None)
    if not r:
        continue
    s, c1, c2, cp = score[n].get(f, (0, 0, 0, 0))
    tot += s
    out[n] = {"file": r["file"], "path": r["path"], "dir": r["dir"],
              "cloth": r["dom"], "conf": r["conf"],
              "fx": r["fx2"], "fy": r["fy2"], "fw": r["fw2"], "fh": r["fh2"],
              "chin": r["chin2"], "farea": r["farea"],
              "face_px": r["face_px"], "sharp": r["sharp"], "ph": r.get("ph")}
    print("  %-20s %-34s %-12s cos全%.2f cos衣%.2f 齐全%.2f 分%.3f fpx%.0f 脸%%%.0f"
          % (n, f, r["dir"], c1, c2, cp, s, r["face_px"],
             256 / max(1e-6, (r["fh2"] * r["h"] if False else r["fh2"] * 3000)) * 100))
print("\n总分 %.3f  平均 %.3f" % (tot, tot / len(out)))

# 唯一性
ks = list(out)
bad = []
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        pa, pb = out[ks[i]]["ph"], out[ks[j]]["ph"]
        if pa is None or pb is None:
            continue
        d = bin(pa ^ pb).count("1")
        if d < 10:
            bad.append((ks[i], ks[j], d))
print("唯一性冲突:", bad if bad else "无")

json.dump(out, open(os.path.join(DESIGN, "assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("-> assign.json")
