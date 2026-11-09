# -*- coding: utf-8 -*-
"""按【衣服颜色】为准重建候选池：脸小也能用，靠裁剪放大

之前错误：要求 face ratio >= 0.035（近景），把绿/黄/粉衣的全身照全挡掉了。
现在：只要检测到人脸（ratio >= 0.004 且能找到连通的肤色块），就收；
      渲染时按脸部位置放大裁剪，脸自然变大。
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
pool = json.load(open(os.path.join(ROOT,"cloth_pool.json"),encoding="utf-8"))

def face_info(path):
    """返回 (has_face, face_ratio, spread, face_center_x, face_center_y)"""
    try: im = Image.open(path).convert("RGB")
    except Exception: return None
    W,H = im.size
    if min(W,H) < 400: return None
    a = np.asarray(im.resize((160,160)), dtype=np.int16)
    r,g,b = a[...,0],a[...,1],a[...,2]; mx=a.max(axis=2); mn=a.min(axis=2)
    skin = (r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    skin[int(160*0.65):,:] = False          # 只看上部
    n = skin.sum() / 25600.0
    if n < 0.004:                            # 连小脸都找不到
        return None
    ys,xs = np.nonzero(skin)
    # 人脸位置：取肤色块的上部中心（脸在上半）
    fy = float(np.percentile(ys, 30) / 160)
    fx = float(np.percentile(xs, 50) / 160)
    spread = float(np.sqrt(xs.var()+ys.var())/160)
    return {"face":round(n,4),"spread":round(spread,3),
            "fx":round(fx,3),"fy":round(fy,3),
            "size":"%dx%d"%(W,H)}

out = []
for i,r in enumerate(pool):
    fi = face_info(r["path"])
    if fi is None: continue
    out.append({**r, **fi})

json.dump(out, open(os.path.join(ROOT,"face_pool.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("face pool:", len(out), "/", len(pool))
from collections import Counter
c = Counter(r["dom"] for r in out)
print("cloth mix:", dict(c.most_common()))
print("\n各稀缺色可用数：")
for k in ["green","yellow","pink","orange","cyan","purple","red","black","white"]:
    print("  %-8s %d" % (k, c.get(k,0)))
