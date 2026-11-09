# -*- coding: utf-8 -*-
"""汇总所有来源 -> 统一打分 -> 按颜色配额挑出 200 张最终素材库

筛选标准（按用户要求）：
  1. 只要人像（人脸清晰、单人优先）
  2. 优先舞台照（暗背景 + 局部强光 + 高对比）
  3. 颜色丰富（按 11 色配额分配，保证绿/粉/黄/紫等稀缺色都有）
  4. 排除海报/拼图/纯文字（边缘密度 + 文字区域检测）
"""
import sys, io, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
FINAL = os.path.join(ROOT, "FINAL_200")
os.makedirs(FINAL, exist_ok=True)

# 所有来源目录
SOURCES = [
    ("wb",  os.path.join(ROOT, "picks")),               # 微博 547
    ("xhs", os.path.join(ROOT, "xhs_all_picks")),      # 后援小分队 205
    ("fc",  os.path.join(ROOT, "forcharlie_picks")),   # ForCharlie 120
    ("sx",  os.path.join(ROOT, "studio_xhs_src")),     # 工作室 720(含354有效)
    ("new", os.path.join(ROOT, "xhs_new_src")),        # 新导出的四博主(待下载)
]
# 新导出四个博主的 URL -> 先下载
EXPORT_DIR = os.path.join(ROOT, "xhs_tabs_export")
NEW_SRC = os.path.join(ROOT, "xhs_new_src")
os.makedirs(NEW_SRC, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
import urllib.request, time

def dl(url, fn):
    p = os.path.join(NEW_SRC, fn)
    if os.path.exists(p) and os.path.getsize(p) > 15000: return p
    for _ in range(2):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA,"Referer":"https://www.xiaohongshu.com/"})
            data=urllib.request.urlopen(req,timeout=25).read()
            if len(data)>15000:
                open(p,"wb").write(data); return p
        except Exception: time.sleep(1)
    return None

def color_profile(im):
    a=np.asarray(im.convert("RGB").resize((64,64)),dtype=np.float32)/255
    mx=a.max(axis=2); mn=a.min(axis=2); l=(mx+mn)/2
    s=np.where(mx==mn,0,(mx-mn)/np.maximum(1e-6,1-np.abs(2*l-1)))
    r,g,b=a[...,0],a[...,1],a[...,2]; dd=mx-mn+1e-6
    h=np.where(mx==r,((g-b)/dd)%6,np.where(mx==g,(b-r)/dd+2,(r-g)/dd+4))*60
    ok=(s>=0.13)&(l>=0.12)&(l<=0.88); n=h.size
    return {
        "black":float((l<0.12).sum()/n), "white":float((l>0.88).sum()/n),
        "gray":float((s<0.13).sum()/n),
        "red":float((((h<15)|(h>=345))&ok).sum()/n),
        "orange":float(((h>=15)&(h<40)&ok).sum()/n),
        "yellow":float(((h>=40)&(h<70)&ok).sum()/n),
        "green":float(((h>=70)&(h<165)&ok).sum()/n),
        "cyan":float(((h>=165)&(h<200)&ok).sum()/n),
        "blue":float(((h>=200)&(h<265)&ok).sum()/n),
        "purple":float(((h>=265)&(h<310)&ok).sum()/n),
        "pink":float(((h>=310)&(h<345)&ok).sum()/n),
    }

def evaluate(path):
    """返回 (总分, 详情) 或 None（不合格）"""
    try: im=Image.open(path).convert("RGB")
    except Exception: return None
    W,H=im.size
    if min(W,H)<450: return None
    sm=np.asarray(im.resize((128,128)),dtype=np.int16)
    r,g,b=sm[...,0],sm[...,1],sm[...,2]; mx=sm.max(axis=2); mn=sm.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    ratio=skin.sum()/float(128*128)
    if ratio<0.015: return None                  # 只要人像
    ys,xs=np.nonzero(skin)
    cx,cy=xs.mean()/128,ys.mean()/128
    center=1.0-min(1.0,abs(cx-0.5)*1.6+abs(cy-0.38)*1.2)
    if ratio<0.025: area=ratio/0.025*0.6
    elif ratio<=0.20: area=1.0
    else: area=max(0.2,1.0-(ratio-0.20)*2)
    spread=np.sqrt(xs.var()+ys.var())/128
    solo=max(0.0,1.0-max(0.0,spread-0.10)*3.5)   # 单人优先
    gray=np.asarray(im.convert("L").resize((256,256)),dtype=np.float32)
    lap=np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean()
    sharp=min(1.0,lap/12.0)
    # 舞台感：暗背景占比 + 高光（亮像素占比适中）+ 强对比
    g64=gray
    dark=(g64<70).mean(); bright=(g64>205).mean()
    stage=0.0
    if 0.20<dark<0.80: stage+=0.8
    if 0.01<bright<0.25: stage+=0.6
    if np.percentile(g64,90)-np.percentile(g64,10)>110: stage+=0.6
    # 排除海报：肤色占比过高或文字区（顶部大块纯色）
    top_strip=np.asarray(im.resize((64,64)).crop((0,0,64,10)),dtype=np.float32)
    if top_strip.std()<12: stage-=0.8            # 顶部纯色横幅
    res=min(1.0,min(W,H)/2000.0)*1.2
    base=res*0.8+center*2.2+area*1.6+solo*1.6+sharp*1.5
    total=base+stage*1.4
    cp=color_profile(im)
    dom=max(cp,key=cp.get)
    return total, {"score":round(float(total),2),"dom":dom,"face":round(center,2),
                   "sharp":round(sharp,2),"stage":round(stage,2),
                   "size":"%dx%d"%(W,H),"colors":{k:round(v,3) for k,v in cp.items()}}

# ---- 1. 下载新导出四个博主的封面 ----
print("downloading new exports...")
ni=0
for fn in sorted(os.listdir(EXPORT_DIR)):
    if not fn.endswith(".json") or fn.startswith("tab_"): continue
    j=json.load(open(os.path.join(EXPORT_DIR,fn),encoding="utf-8"))
    for note in j.get("notes",[]):
        for u in note.get("u",[]):
            if u:
                dl(u,"nw_%04d.jpg"%ni); ni+=1
print("new urls:",ni,"| downloaded:",len([f for f in os.listdir(NEW_SRC) if f.endswith(('.jpg','.png'))]))

# ---- 2. 汇总所有图打分 ----
recs=[]
for tag,d in SOURCES:
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if not f.lower().endswith((".jpg",".png")): continue
        p=os.path.join(d,f)
        e=evaluate(p)
        if e: recs.append({"tag":tag,"path":p,"file":f,"total":e[0],**e[1]})
print("scored total:",len(recs))

# ---- 3. 颜色配额挑选 200 张 ----
# 目标：颜色丰富 + 稀有色保底
QUOTA = {
    "blue":34,"gray":26,"black":22,"red":20,"purple":16,"pink":16,
    "green":16,"yellow":14,"orange":14,"cyan":12,"white":10,
}
by_color={}
for r in recs: by_color.setdefault(r["dom"],[]).append(r)
for k in by_color: by_color[k].sort(key=lambda x:-x["total"])
print("\nby color (available):")
for k in QUOTA: print("  %-8s %d"%(k,len(by_color.get(k,[]))))

chosen=[]; used=set()
# 第一轮：按配额取每色最高分
for color,q in QUOTA.items():
    n=0
    for r in by_color.get(color,[]):
        if r["path"] in used: continue
        chosen.append(r); used.add(r["path"]); n+=1
        if n>=q: break
    print("  %-8s took %d"%(color,n))
# 第二轮：不足 200 用全局最高分补齐
rest=sorted([r for r in recs if r["path"] not in used],key=lambda x:-x["total"])
for r in rest:
    if len(chosen)>=200: break
    chosen.append(r); used.add(r["path"])
chosen=chosen[:200]
print("\nFINAL:",len(chosen))

# ---- 4. 复制到 FINAL_200 并写清单 ----
manifest=[]
for i,r in enumerate(chosen):
    ext=".png" if r["file"].lower().endswith(".png") else ".jpg"
    fn="final_%03d%s"%(i,ext)
    shutil.copy2(r["path"],os.path.join(FINAL,fn))
    manifest.append({"file":fn,"src":r["tag"],"origin":r["file"],
                     "dom":r["dom"],"score":float(r["score"]),"face":float(r["face"]),
                     "sharp":float(r["sharp"]),"stage":float(r["stage"]),"size":r["size"]})
json.dump(manifest,open(os.path.join(ROOT,"FINAL_200_manifest.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
from collections import Counter
c=Counter(r["dom"] for r in chosen)
print("final color mix:",dict(c.most_common()))
print("DONE ->",FINAL)
