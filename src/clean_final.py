# -*- coding: utf-8 -*-
"""二次净化：剔除海报/拼图/多人合影，从剩余素材里补回 200 张纯人像

判定规则：
  - 拼图：图片内出现明显直线分割（横/竖白线或色块边界）
  - 海报：人脸占比很小但有大面积高饱和文字色块，或顶部/底部有整齐色带
  - 多人：肤色区域分散度过高
"""
import sys, io, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
FINAL = os.path.join(ROOT, "FINAL_200")
m = json.load(open(os.path.join(ROOT,"FINAL_200_manifest.json"),encoding="utf-8"))

def is_poster(path):
    try: im=Image.open(path).convert("RGB")
    except Exception: return True
    W,H=im.size
    sm=im.resize((128,128))
    a=np.asarray(sm,dtype=np.int16)
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    ratio=skin.sum()/float(128*128)
    ys,xs=np.nonzero(skin)
    spread=np.sqrt(xs.var()+ys.var())/128 if len(xs)>0 else 1
    # 多人/拼图：肤色块分散
    if spread>0.30: return True
    # 强直线分割检测：行/列的亮度突变条带（拼图白边）
    g=np.asarray(im.convert("L").resize((128,128)),dtype=np.float32)
    row_grad=np.abs(np.diff(g,axis=0)).mean(axis=1)
    col_grad=np.abs(np.diff(g,axis=1)).mean(axis=0)
    if (row_grad>55).sum()>=2 or (col_grad>55).sum()>=2: return True
    # 顶部或底部整齐大色带（海报标题）
    top=g[:12]; bot=g[-12:]
    if top.std()<9 and (top.mean()>200 or top.mean()<40) and ratio<0.06: return True
    if ratio<0.02: return True
    return False

bad=[x for x in m if is_poster(os.path.join(FINAL,x["file"]))]
print("posters/collages to remove:", len(bad))
for x in bad[:15]: print("  ", x["file"], x["origin"], x["dom"])

# 从候选池补回（所有来源，排除已在库里的 origin）
DIRS = [os.path.join(ROOT,d) for d in
        ("forcharlie_picks","picks","xhs_all_picks","studio_xhs_src","xhs_new_src")]
existing={x["origin"] for x in m}

def quality(path):
    try: im=Image.open(path).convert("RGB")
    except Exception: return None
    W,H=im.size
    if min(W,H)<450: return None
    if is_poster(path): return None
    sm=im.resize((128,128)); a=np.asarray(sm,dtype=np.int16)
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    ratio=skin.sum()/float(128*128)
    if ratio<0.015: return None
    ys,xs=np.nonzero(skin); cx,cy=xs.mean()/128,ys.mean()/128
    center=1.0-min(1.0,abs(cx-0.5)*1.6+abs(cy-0.38)*1.2)
    gray=np.asarray(im.convert("L").resize((256,256)),dtype=np.float32)
    lap=np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean()
    sharp=min(1.0,lap/12.0)
    return center*2+sharp*2+ratio*3+min(1.0,min(W,H)/2000.0)

pool=[]
for d in DIRS:
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if f in existing or not f.lower().endswith((".jpg",".png")): continue
        p=os.path.join(d,f); q=quality(p)
        if q is not None: pool.append((q,p,f))
pool.sort(key=lambda x:-x[0])
print("replacement pool:", len(pool))

# 替换
for x,(q,p,f) in zip(bad,pool):
    old=os.path.join(FINAL,x["file"])
    shutil.copy2(p,old)
    x["origin"]=f; x["src"]=os.path.basename(os.path.dirname(p))
    x["cleaned"]=True
    print("  replace",x["file"],"<-",f[:30])

json.dump(m,open(os.path.join(ROOT,"FINAL_200_manifest.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
print("DONE files:",len(os.listdir(FINAL)),"| cleaned:",len(bad))
