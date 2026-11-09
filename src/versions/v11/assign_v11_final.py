# -*- coding: utf-8 -*-
"""第四版最终定稿（人工把关 + 全局评分为辅）
   每一条都写明对应你哪句话；被自动评分选错的项已人工改掉
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np

ROOT = HERE
DESIGN = os.path.join(ROOT, "design_v11")
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))
PF = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))}
PA = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))}

HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]

# 人工定稿
FINAL = {
    "微信":              "studio_20261025_76889_5.jpg",   # 绿 0.14 近景（第一版绿系）
    "QQ音乐":            "p0_0108_1.jpg",                # 第三版图 + 第一版黄圆边
    "哔哩哔哩":           "p0_0201_1.jpg",                # 你喜欢第一版的粉红亮片
    "Google Chrome":     "station_20260822_99475_1.jpg", # 红衣近景，脸大
    "个人 - Edge":        "c929b_ee869d9377.jpg",         # 青 0.15 + 蓝 0.71，青蓝俱全
    "360安全浏览器":       "studio_20260903_94616_0.jpg",   # 浅绿西装
    "Visual Studio Code": "sx_0583.jpg",                 # 蓝 0.48+青 0.10，锐 16
    "Cursor":            "station_20261017_31971_2.jpg", # 黑白演出服
    "DeepSeek Harness":  "station_20260905_29652_3.jpg", # 白衣（对应白底鲸鱼）
    "Cherry Studio":     "studio_20260926_93785_7.jpg",  # 红
    "WorkBuddy":         "studio_20260928_00229_4.jpg",   # 绿 0.24 + 青 0.05，绿系更足
    "WPS Office":        "studio_20261004_85716_6.jpg",  # 第三版满意
    "全能录屏助手":        "nw_0047.jpg",                  # 黑衣 + 红，脸清楚
    "剪映专业版":          "studio_20261013_54275_0.jpg",  # 黑白（黑西装+红底）锐25.7
    "百度网盘":           "sx_0505.jpg",                  # 第三版满意
    "飞书":              "c929b_0155a8ad36.jpg",         # 蓝 0.44，大脸
    "Clash Verge":       "station_20260814_56755_2.jpg", # 第一版兔子装的紫
    "PyCharm 2026.2.3":  "c929b_72f8652f20.jpg",         # 蓝 0.74 + 黑 0.26，蓝黑俱全
    "ToDesk":            "studio_20260915_73581_0.jpg",  # 白衣 + 全蓝背景 明亮
    "互传":              "studio_20261020_75648_0.jpg",   # 白+青 明亮近景
    "网易邮箱大师":        "station_20260530_05624_8.jpg",  # 红衣大脸 锐14.4
    "联想电脑管家":        "station_20260524_50364_6.jpg",  # 亮蓝
    "腾讯QQ":            "station_20260625_76107_5.jpg",  # 黑马甲+白衬衫+紫红胸饰，三色齐
    "腾讯会议":           "c929b_c824162da8.jpg",         # 纯蓝 0.72 锐36
}

# 调色强度（人工 + 搜索）
STRENGTH = {
    "微信": 0.55, "QQ音乐": 0.66, "哔哩哔哩": 0.30,
    "Google Chrome": 0.85, "个人 - Edge": 0.70, "360安全浏览器": 0.55,
    "Visual Studio Code": 0.45, "Cursor": 0.25, "DeepSeek Harness": 0.25,
    "Cherry Studio": 0.60, "WorkBuddy": 0.45, "WPS Office": 0.55,
    "全能录屏助手": 0.70, "剪映专业版": 0.55, "百度网盘": 0.35,
    "飞书": 0.40, "Clash Verge": 0.85, "PyCharm 2026.2.3": 0.55,
    "ToDesk": 0.55, "互传": 0.35, "网易邮箱大师": 0.45,
    "联想电脑管家": 0.40, "腾讯QQ": 0.30, "腾讯会议": 0.70,
}


def cos(a, b):
    va = np.array([a.get(k, 0) for k in HUES], float)
    vb = np.array([b.get(k, 0) for k in HUES], float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return 0.0 if na < 1e-9 or nb < 1e-9 else float(va.dot(vb) / (na * nb))


def complete(pal, act):
    main = [k for k, w in pal.items() if w >= 0.10] or [max(pal, key=pal.get)]
    return sum(1 for k in main if act.get(k, 0) >= 0.095) / len(main)


out, miss = {}, []
for n, f in FINAL.items():
    r = PF.get(f) or PA.get(f)
    if not r:
        miss.append((n, f)); continue
    pal = PAL[n]
    c1 = cos(r["all"], pal)
    c2 = cos(r["cloth"], pal)
    cp = complete(pal, r["all"])
    fpx = min(r.get("face_px", 0), 1200) / 1200.0
    sh = min(r["sharp"], 28) / 28.0
    s = 0.34 * c1 + 0.34 * c2 + 0.20 * cp + 0.07 * fpx + 0.05 * sh
    out[n] = {"file": r["file"], "path": r["path"], "dir": r["dir"],
              "cloth": r["dom"], "conf": r["conf"],
              "fx": r.get("fx2", r.get("fx")), "fy": r.get("fy2", r.get("fy")),
              "fw": r.get("fw2", r.get("fw")), "fh": r.get("fh2", r.get("fh")),
              "chin": r.get("chin2", r.get("chin")),
              "farea": r["farea"], "face_px": r.get("face_px", 0),
              "sharp": r["sharp"], "ph": r.get("ph"),
              "cos_all": round(c1, 3), "cos_cloth": round(c2, 3),
              "complete": round(cp, 3), "score": round(s, 3)}

print("%-20s %-34s %-12s %-6s %-6s %-6s %-5s" % (
    "APP", "照片", "目录", "cos全", "cos衣", "齐全", "分"))
for n in FINAL:
    if n not in out:
        print("!!", n, FINAL[n]); continue
    r = out[n]
    print("%-20s %-34s %-12s %-6.2f %-6.2f %-6.2f %-5.2f  fpx%.0f sh%s" % (
        n, r["file"], r["dir"], r["cos_all"], r["cos_cloth"], r["complete"],
        r["score"], r["face_px"], r["sharp"]))

sc = [out[n]["score"] for n in out]
print("\n平均分 %.3f  最低 %.3f (%s)  缺失 %s" % (
    sum(sc) / len(sc), min(sc),
    min(out, key=lambda k: out[k]["score"]), miss))

# 唯一性
ks = list(out); bad = []
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
json.dump(STRENGTH, open(os.path.join(DESIGN, "grade_strength.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("-> assign.json / grade_strength.json")
