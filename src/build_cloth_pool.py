# -*- coding: utf-8 -*-
"""扫全量素材池，按衣服颜色建索引（不局限于 FINAL_200）"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
# 复用 cloth_color 里的函数
sys.path.insert(0, ROOT)
from cloth_lib import cloth_color

DIRS = [
    ("wb",  os.path.join(ROOT,"picks")),
    ("xhs", os.path.join(ROOT,"xhs_all_picks")),
    ("fc",  os.path.join(ROOT,"forcharlie_picks")),
    ("sx",  os.path.join(ROOT,"studio_xhs_src")),
    ("new", os.path.join(ROOT,"xhs_new_src")),
    ("fa",  os.path.join(ROOT,"forcharlie_src")),
    ("xa",  os.path.join(ROOT,"xhs_all")),
]

recs=[]
for tag,d in DIRS:
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if not f.lower().endswith((".jpg",".png")): continue
        p=os.path.join(d,f)
        c=cloth_color(p)
        if c and 0 <= c["conf"] <= 1.5:
            recs.append({"tag":tag,"path":p,"file":f,**c})
# 按文件名去重（同名多目录）
seen=set(); uniq=[]
for r in recs:
    key=r["file"]
    if key in seen: continue
    seen.add(key); uniq.append(r)
json.dump(uniq,open(os.path.join(ROOT,"cloth_pool.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
print("cloth pool:",len(uniq))
from collections import Counter
c=Counter(r["dom"] for r in uniq)
for k,v in c.most_common(): print("  %-8s %d"%(k,v))
