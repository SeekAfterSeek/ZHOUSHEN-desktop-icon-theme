# -*- coding: utf-8 -*-
"""为“脸太小/会糊”的 APP 定向检索：脸像素 >= 350 才进候选"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
sys.path.insert(0, ROOT)
from facedet import detect_face
from PIL import Image
from multiprocessing import Pool as MPool

POOL = json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))


def _w(r):
    try:
        im = Image.open(r["path"])
        d = detect_face(im)
        if d is None:
            return None
        W, H = im.size
        r = dict(r)
        r["face_px"] = round(d["fh"] * H, 1)
        r["fx2"] = round(d["fx"], 3); r["fy2"] = round(d["fy"], 3)
        r["fw2"] = round(d["fw"], 3); r["fh2"] = round(d["fh"], 3)
        r["chin2"] = round(d["chin"], 3)
        r["score2"] = d["score"]
        r["W"] = W; r["H"] = H
        return r
    except Exception:
        return None


if __name__ == "__main__":
    cand = [r for r in POOL if r["sharp"] >= 8 and 8 <= r["bright"] <= 250
            and r["topstd"] >= 6 and r["botstd"] >= 6
            and r["hlines"] < 2 and r["vlines"] < 2]
    print("base:", len(cand), flush=True)
    with MPool(8) as mp:
        out = [x for x in mp.map(_w, cand, chunksize=8) if x]
    print("with face:", len(out), flush=True)
    json.dump(out, open(os.path.join(ROOT, "pool_face.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    big = [r for r in out if r["face_px"] >= 350]
    print("face_px>=350:", len(big))
    print("quality(sharp>=15 & facepx>=350):",
          len([r for r in big if r["sharp"] >= 15]))
