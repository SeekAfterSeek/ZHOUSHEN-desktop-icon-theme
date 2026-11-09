# -*- coding: utf-8 -*-
"""第四版（v11）定稿：全部满足 脸像素>=350 + 高锐度 + pHash 唯一
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
OUT = os.path.join(ROOT, "design_v11")
os.makedirs(OUT, exist_ok=True)
byf = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_face.json"), encoding="utf-8"))}
POOL = {r["file"]: r for r in json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))}
PAL = json.load(open(os.path.join(ROOT, "design_v8", "icon_palette.json"), encoding="utf-8"))

# 人工定稿（v11 第四版）
FINAL = {
    "微信":              "sx_0295.jpg",                    # 你看好第一版（翠绿纱衣）
    "QQ音乐":            "p0_0108_1.jpg",                  # 第三版的图(黄衣) + 第一版黄圆边
    "哔哩哔哩":           "p0_0201_1.jpg",                  # 你喜欢第一版(粉红亮片)
    "Google Chrome":     "station_20260822_99475_1.jpg",   # 红衣+蓝底 红蓝同时在场
    "个人 - Edge":        "c929b_33e03408a2.jpg",          # 青色衣带蓝
    "360安全浏览器":       "studio_20260903_94616_0.jpg",     # 浅绿
    "Visual Studio Code": "fc_1083.jpg",                   # 蓝亮片夹克
    "Cursor":            "station_20260815_36422_3.jpg",   # 黑白演出服 锐度34.3
    "DeepSeek Harness":  "station_20260905_29652_3.jpg",   # 白衣（原图标白底）大脸
    "Cherry Studio":     "f2_0093.jpg",                    # 红
    "WorkBuddy":         "studio_20260819_73927_3.jpg",    # 青绿 绿植自然系
    "WPS Office":        "studio_20261004_85716_6.jpg",    # 第三版满意
    "全能录屏助手":        "studio_20260913_73157_7.jpg",     # 黑为主+红 锐度14.1 脸416px
    "剪映专业版":          "studio_20261026_32066_5.jpg",     # 黑白 大脸
    "百度网盘":           "sx_0505.jpg",                    # 第三版满意
    "飞书":              "fc_0761.jpg",                    # 蓝
    "Clash Verge":       "station_20260524_50364_3.jpg",   # 紫（第一版兔子装同系）
    "PyCharm 2026.2.3":  "c929b_72f8652f20.jpg",           # 蓝0.74+黑0.26 脸474px
    "ToDesk":            "studio_20261001_00685_2.jpg",    # 蓝银亮片 明亮蓝
    "互传":              "station_20260524_50364_8.jpg",    # 蓝白
    "网易邮箱大师":        "station_20260530_05624_0.jpg",    # 红 大脸
    "联想电脑管家":        "station_20260524_50364_6.jpg",    # 亮蓝+粉 明亮大脸
    "腾讯QQ":            "station_20260524_50364_2.jpg",    # 黑+红+白
    "腾讯会议":           "studio_20260916_13855_0.jpg",    # 蓝 全新
}
BORDER = {"QQ音乐"}

rows, miss = {}, []
for n, f in FINAL.items():
    r = byf.get(f) or POOL.get(f)
    if not r:
        miss.append((n, f)); continue
    rows[n] = {"file": r["file"], "path": r["path"], "dir": r["dir"],
               "cloth": r["dom"], "conf": r["conf"],
               "fx": r.get("fx2", r.get("fx")), "fy": r.get("fy2", r.get("fy")),
               "fw": r.get("fw2", r.get("fw")), "fh": r.get("fh2", r.get("fh")),
               "chin": r.get("chin2", r.get("chin")),
               "farea": r["farea"], "face_px": r.get("face_px", 0),
               "sharp": r["sharp"], "ph": r.get("ph")}

print("=== 定稿核验 ===")
for n in FINAL:
    if n not in rows:
        print("  !! MISSING %-18s %s" % (n, FINAL[n])); continue
    r = rows[n]
    print("  %-20s %-34s %-12s %-5s %.2f 脸%5.0fpx 锐%-5s farea%.3f"
          % (n, r["file"], r["dir"], r["cloth"], r["conf"], r["face_px"], r["sharp"], r["farea"]))

print("\n=== 唯一性 ===")
ks = list(rows); bad = 0
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        a, b = rows[ks[i]], rows[ks[j]]
        if a["ph"] is None or b["ph"] is None:
            continue
        dd = bin(a["ph"] ^ b["ph"]).count("1")
        if dd < 10:
            bad += 1
            print("  ⚠ %-16s vs %-16s d=%d" % (ks[i], ks[j], dd))
print("  冲突(<10):", bad, " 项数:", len(rows), " 缺失:", miss)

json.dump(rows, open(os.path.join(OUT, "assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("-> assign.json")
