# -*- coding: utf-8 -*-
"""按人工核对的编号剔除海报/拼图/非人像，从候选池补回纯人像"""
import sys, io, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
FINAL = os.path.join(ROOT, "FINAL_200")
m = json.load(open(os.path.join(ROOT,"FINAL_200_manifest.json"),encoding="utf-8"))

BAD_IDX = [
    4,18,19,20,30,33,40,55,77,93,96,98,
    114,120,130,133,137,144,147,149,152,154,158,164,165,167,182,183,188,
]
bad_files = ["final_%03d.jpg" % i for i in BAD_IDX]
print("to remove:", len(bad_files))

# 候选池：所有来源里的人像，排除当前库里的 origin
DIRS = [os.path.join(ROOT,d) for d in
        ("forcharlie_picks","picks","xhs_all_picks","studio_xhs_src","xhs_new_src","xhs_all","forcharlie_src")]
existing = {x["file"] for x in m}

def face_score(path):
    try: im=Image.open(path).convert("RGB")
    except Exception: return None
    W,H=im.size
    if min(W,H)<450: return None
    a=np.asarray(im.resize((128,128)),dtype=np.int16)
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    ratio=skin.sum()/float(128*128)
    if ratio<0.018: return None
    ys,xs=np.nonzero(skin)
    spread=np.sqrt(xs.var()+ys.var())/128
    if spread>0.26: return None           # 排除多人/拼图
    cx,cy=xs.mean()/128,ys.mean()/128
    center=1.0-min(1.0,abs(cx-0.5)*1.6+abs(cy-0.38)*1.2)
    gray=np.asarray(im.convert("L").resize((256,256)),dtype=np.float32)
    lap=np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean()
    sharp=min(1.0,lap/12.0)
    # 排除顶部大色带海报
    top=gray[:18]
    if top.std()<10 and ratio<0.05: return None
    return center*2.2+sharp*1.8+ratio*2.5+min(1.0,min(W,H)/2000.0)

pool=[]
for d in DIRS:
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if not f.lower().endswith((".jpg",".png")): continue
        p=os.path.join(d,f); s=face_score(p)
        if s is not None: pool.append((s,p,f))
# 去重（同名文件可能出现在多个目录）
seen=set(); uniq=[]
for s,p,f in sorted(pool,key=lambda x:-x[0]):
    if f in seen: continue
    seen.add(f); uniq.append((s,p,f))
print("replacement pool:", len(uniq))

it=iter(uniq)
for bf in bad_files:
    old=os.path.join(FINAL,bf)
    try: s,p,f=next(it)
    except StopIteration: break
    shutil.copy2(p,old)
    for x in m:
        if x["file"]==bf:
            x["origin"]=f; x["src"]=os.path.basename(os.path.dirname(p))
            x["cleaned2"]=True
            break
    print("  ",bf,"<-",f[:34])

json.dump(m,open(os.path.join(ROOT,"FINAL_200_manifest.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
print("DONE files:",len(os.listdir(FINAL)))
