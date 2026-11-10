# -*- coding: utf-8 -*-
"""最终裁定 v2：合并「人脸锚点」+「ORB投票」两路候选，用脸尺寸比精确缩放后模板匹配

为什么合并：两种方法各有盲区
  - 锚点法：紧凑裁切时补丁外圈内容不同 → 分数偏低
  - ORB 票数：区分度弱，但真匹配往往票数断层领先
合并候选后做一次"正确缩放"的模板匹配，是真匹配就会逐像素重合，相关值接近 1。
"""
import sys, io, os, json, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import cv2
from PIL import Image as PILImage

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
sys.path.insert(0, ROOT)
from facedet import detect_face

ANCHOR = json.load(open(os.path.join(ROOT, "_shot_anchor.json"), encoding="utf-8"))
ORB = json.load(open(os.path.join(ROOT, "_shot_orb.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "_shot_verify")
os.makedirs(OUT, exist_ok=True)


def imread_bgr(p):
    try:
        b = np.fromfile(p, np.uint8)
        return cv2.imdecode(b, cv2.IMREAD_COLOR) if b.size else None
    except Exception:
        return None


_fh_cache = {}


def face_frac(p):
    if p in _fh_cache:
        return _fh_cache[p]
    v = None
    bgr = imread_bgr(p)
    if bgr is not None:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        d = detect_face(PILImage.fromarray(rgb))
        if d:
            v = d["fh"]
    _fh_cache[p] = v
    return v


def match_at(shot_bgr, shot_fh, cand_path):
    cd = imread_bgr(cand_path)
    if cd is None or not shot_fh:
        return 0.0, 0.0, None
    cfh = face_frac(cand_path)
    if not cfh:
        return 0.0, 0.0, None
    scale = (cfh * cd.shape[0]) / (shot_fh * shot_bgr.shape[0])
    if not (0.15 <= scale <= 3.0):
        return 0.0, scale, None
    tw, th = int(shot_bgr.shape[1] * scale), int(shot_bgr.shape[0] * scale)
    if tw < 30 or th < 30 or tw >= cd.shape[1] or th >= cd.shape[0]:
        return 0.0, scale, None
    tpl = cv2.resize(shot_bgr, (tw, th), interpolation=cv2.INTER_AREA)
    g1 = cv2.cvtColor(cd, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    r = cv2.matchTemplate(g1, g2, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    return float(mx), scale, (loc[0], loc[1], tw, th)


def main():
    t0 = time.time()
    result = {}
    for k, a in ANCHOR.items():
        shot_path = a["shot"]
        sb = imread_bgr(shot_path)
        if sb is None:
            continue
        sfh = None
        rgb = cv2.cvtColor(sb, cv2.COLOR_BGR2RGB)
        d = detect_face(PILImage.fromarray(rgb))
        if d:
            sfh = d["fh"]

        # 合并候选
        cands = {}
        for c in a["top"]:
            cands[c["path"]] = cands.get(c["path"], 0) + c["score"]
        if k in ORB:
            for m in ORB[k]["matches"]:
                cands[m["path"]] = cands.get(m["path"], 0) + min(m["votes"], 40) / 40.0
        items = list(cands.items())[:14]

        rows = []
        for p, prior in items:
            corr, sc, box = match_at(sb, sfh, p)
            rows.append({"corr": round(corr, 4), "scale": round(sc, 3),
                         "prior": round(prior, 3), "path": p,
                         "file": os.path.basename(p),
                         "dir": os.path.basename(os.path.dirname(p)),
                         "box": list(box) if box else None})
        rows.sort(key=lambda x: -x["corr"])
        result[k] = {"shot": shot_path, "sfh": sfh, "top": rows}
        print("\n[%s]" % k, flush=True)
        for r in rows[:4]:
            mark = ("★★★" if r["corr"] >= 0.85 else "★★" if r["corr"] >= 0.70 else
                    "★" if r["corr"] >= 0.55 else "  ")
            print("   %s 相关%.3f 缩放%.2f  %s" % (mark, r["corr"], r["scale"],
                                                  r["file"][:46]), flush=True)

    json.dump(result, open(os.path.join(ROOT, "_shot_final3.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    hi = sum(1 for v in result.values() if v["top"] and v["top"][0]["corr"] >= 0.70)
    md = sum(1 for v in result.values() if v["top"] and v["top"][0]["corr"] >= 0.55)
    print("\n=== 相关≥0.85: %d | ≥0.70: %d | ≥0.55: %d | 共 %d ===" %
          (sum(1 for v in result.values() if v["top"] and v["top"][0]["corr"] >= 0.85),
           hi, md, len(result)))
    print("总耗时 %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
