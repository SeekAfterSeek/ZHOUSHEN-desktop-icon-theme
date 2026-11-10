# -*- coding: utf-8 -*-
"""修补 3 个未定组：候选池内做多尺度扫描（不依赖脸尺寸比）

有些截图的人脸检测框不准（侧头/低头），由脸尺寸比推的缩放就错了。
改成在合理区间内扫一遍尺度，取最高相关。
"""
import sys, io, os, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import cv2

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
ANCHOR = json.load(open(os.path.join(ROOT, "_shot_anchor.json"), encoding="utf-8"))
ORB = json.load(open(os.path.join(ROOT, "_shot_orb.json"), encoding="utf-8"))
FINAL = json.load(open(os.path.join(ROOT, "_shot_final3.json"), encoding="utf-8"))

TARGETS = [k for k, v in FINAL.items() if not v["top"] or v["top"][0]["corr"] < 0.70]


def imread_bgr(p):
    try:
        b = np.fromfile(p, np.uint8)
        return cv2.imdecode(b, cv2.IMREAD_COLOR) if b.size else None
    except Exception:
        return None


def sweep(shot_bgr, cand_path, scales):
    cd = imread_bgr(cand_path)
    if cd is None:
        return 0.0, 0.0
    g1 = cv2.cvtColor(cd, cv2.COLOR_BGR2GRAY)
    best, bs = 0.0, 0.0
    for s in scales:
        tw, th = int(shot_bgr.shape[1] * s), int(shot_bgr.shape[0] * s)
        if tw < 40 or th < 40 or tw >= cd.shape[1] or th >= cd.shape[0]:
            continue
        tpl = cv2.resize(shot_bgr, (tw, th), interpolation=cv2.INTER_AREA)
        g2 = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
        r = cv2.matchTemplate(g1, g2, cv2.TM_CCOEFF_NORMED)
        v = float(r.max())
        if v > best:
            best, bs = v, s
    return best, bs


SCALES = list(np.geomspace(0.20, 2.90, 26))


def main():
    print("待修补:", TARGETS)
    patch = {}
    for k in TARGETS:
        shot_bgr = imread_bgr(ANCHOR[k]["shot"])
        if shot_bgr is None:
            continue
        cands = {}
        for c in ANCHOR[k]["top"]:
            cands[c["path"]] = c["file"]
        if k in ORB:
            for m in ORB[k]["matches"]:
                cands[m["path"]] = m["file"]
        print("\n[%s] 候选 %d 个" % (k, len(cands)), flush=True)
        rows = []
        for p, f in cands.items():
            corr, sc = sweep(shot_bgr, p, SCALES)
            rows.append({"corr": round(corr, 4), "scale": round(sc, 2),
                         "path": p, "file": f,
                         "dir": os.path.basename(os.path.dirname(p))})
        rows.sort(key=lambda x: -x["corr"])
        for r in rows[:5]:
            mark = "★★★" if r["corr"] >= 0.85 else ("★★" if r["corr"] >= 0.70 else
                                                    ("★" if r["corr"] >= 0.55 else "  "))
            print("   %s 相关%.3f 尺度%.2f  %s" % (mark, r["corr"], r["scale"],
                                                  r["file"][:46]), flush=True)
        patch[k] = {"shot": ANCHOR[k]["shot"], "top": rows}

    # 合并回总表
    for k, v in patch.items():
        FINAL[k] = v
    json.dump(FINAL, open(os.path.join(ROOT, "_shot_final3.json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n已合并进 _shot_final3.json")


if __name__ == "__main__":
    main()
