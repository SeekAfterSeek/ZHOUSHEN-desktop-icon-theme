# -*- coding: utf-8 -*-
"""v10 最终修正：消除重复 + Cursor 换黑衣 + 归档"""
import sys, io, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
DESIGN = os.path.join(ROOT,"design_v10")
assign = json.load(open(os.path.join(DESIGN,"assign.json"),encoding="utf-8"))
pool = json.load(open(os.path.join(ROOT,"v10_pool.json"),encoding="utf-8"))

def clean(path):
    try: im = Image.open(path).convert("RGB")
    except Exception: return False
    if min(im.size) < 450: return False
    a = np.asarray(im.resize((160,160)), dtype=np.int16)
    r,g,b = a[...,0],a[...,1],a[...,2]; mx=a.max(axis=2); mn=a.min(axis=2)
    skin = (r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    skin[int(160*0.65):,:] = False
    if skin.sum()/25600.0 < 0.006: return False
    g64 = np.asarray(im.convert("L").resize((128,128)),dtype=np.float32)
    if float((g64>235).mean()) > 0.40: return False
    if int((np.abs(np.diff(g64,axis=0)).mean(axis=1)>55).sum()) >= 3: return False
    return True

# 找出重复使用同一张源图的情况（fc_0011 与 f2_0011 是同图）
same = {}
for k,v in assign.items():
    base = v["file"].replace("f2_","fc_").replace("_1.jpg",".jpg")
    same.setdefault(base, []).append(k)
dups = {b:apps for b,apps in same.items() if len(apps)>1}
print("重复:", dups)

# 给重复的第二位换一张（同样绿色系，但不同图）
for base, apps in dups.items():
    keeper = apps[0]
    used = {v["file"] for v in assign.values()}
    for app in apps[1:]:
        cands = [r for r in pool if r["file"] not in used and clean(r["path"])
                 and r["all"].get("green",0) > 0.15]
        if not cands:
            cands = [r for r in pool if r["file"] not in used and clean(r["path"])
                     and r["all"].get("cyan",0) > 0.3]
        if cands:
            cands.sort(key=lambda r: -(r["all"].get("green",0)+r["all"].get("cyan",0)*0.6))
            b = cands[0]
            assign[app] = {"file":b["file"],"path":b["path"],"cloth":b["dom"],
                           "conf":b["conf"],"fit":round(b["all"].get("green",0),3),
                           "face":b["face"],"fx":b["fx"],"fy":b["fy"]}
            used.add(b["file"])
            print("  %s 换成 %s (green=%.2f)" % (app, b["file"], b["all"].get("green",0)))

# Cursor 必须黑衣
used = {v["file"] for v in assign.values()}
used.discard(assign["Cursor"]["file"])
cands = [r for r in pool if r["file"] not in used and clean(r["path"])
         and r["all"].get("black",0) > 0.45]
cands.sort(key=lambda r: -(r["all"].get("black",0) + min(r["face"],0.06)*3))
if cands:
    b = cands[0]
    assign["Cursor"] = {"file":b["file"],"path":b["path"],"cloth":b["dom"],
                        "conf":b["conf"],"fit":round(b["all"].get("black",0),3),
                        "face":b["face"],"fx":b["fx"],"fy":b["fy"]}
    print("  Cursor -> %s (black=%.2f face=%.3f)" % (b["file"], b["all"].get("black",0), b["face"]))

json.dump(assign, open(os.path.join(DESIGN,"assign.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("saved")
