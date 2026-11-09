# -*- coding: utf-8 -*-
"""针对性补录：把绿色/黄色/紫色的高质量舞台照强制纳入 200 库

问题：主色算法把「深舞台+绿衣」判成 black/blue，导致绿色配额只有 2 张。
方案：用 HSV 绿色像素占比（不看主色）找出绿衣照，替换掉库里低分冗余图。
"""
import sys, io, os, json, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
FINAL = os.path.join(ROOT, "FINAL_200")
manifest = json.load(open(os.path.join(ROOT,"FINAL_200_manifest.json"),encoding="utf-8"))

# 所有候选目录
DIRS = [
    ("fc",  os.path.join(ROOT,"forcharlie_picks")),
    ("wb",  os.path.join(ROOT,"picks")),
    ("xhs", os.path.join(ROOT,"xhs_all_picks")),
    ("sx",  os.path.join(ROOT,"studio_xhs_src")),
    ("new", os.path.join(ROOT,"xhs_new_src")),
]

def color_ratio(path):
    """各色相占比（不看主色，看绝对占比）"""
    a=np.asarray(Image.open(path).convert("RGB").resize((96,96)),dtype=np.float32)/255
    mx=a.max(axis=2);mn=a.min(axis=2);l=(mx+mn)/2
    s=np.where(mx==mn,0,(mx-mn)/np.maximum(1e-6,1-np.abs(2*l-1)))
    r,g,b=a[...,0],a[...,1],a[...,2];dd=mx-mn+1e-6
    h=np.where(mx==r,((g-b)/dd)%6,np.where(mx==g,(b-r)/dd+2,(r-g)/dd+4))*60
    ok=(s>=0.18)&(l>=0.12)&(l<=0.88);n=h.size
    return {
        "green":float(((h>=70)&(h<165)&ok).sum()/n),
        "yellow":float(((h>=40)&(h<70)&ok).sum()/n),
        "purple":float(((h>=265)&(h<310)&ok).sum()/n),
        "pink":float(((h>=310)&(h<345)&ok).sum()/n),
        "orange":float(((h>=15)&(h<40)&ok).sum()/n),
        "red":float((((h<15)|(h>=345))&ok).sum()/n),
    }

def face_ok(path):
    try: im=Image.open(path).convert("RGB")
    except Exception: return False
    if min(im.size)<450: return False
    a=np.asarray(im.resize((128,128)),dtype=np.int16)
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    return skin.sum()/float(128*128)>=0.015

# 找绿色占比高的图（>= 0.10），按占比排序
cands={"green":[],"yellow":[],"purple":[],"pink":[],"orange":[]}
for tag,d in DIRS:
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if not f.lower().endswith((".jpg",".png")): continue
        p=os.path.join(d,f)
        cr=color_ratio(p)
        for k in cands:
            if cr[k]>=0.10:
                cands[k].append((cr[k],p,f,tag))
print("=== candidates by color (ratio>=0.10) ===")
for k,v in cands.items():
    v.sort(key=lambda x:-x[0])
    print("  %-8s %d | top: %s %.2f"%(k,len(v),v[0][2] if v else "-",v[0][0] if v else 0))

# 强制纳入：每色至少 12 张（绿色优先，用户点名的）
TARGET={"green":16,"yellow":10,"purple":12,"pink":14,"orange":12}
existing={m["origin"] for m in manifest}
add=[]
for k,q in TARGET.items():
    cur=sum(1 for m in manifest if m["dom"]==k)
    need=max(0,q-cur)
    got=0
    for ratio,p,f,tag in cands[k]:
        if f in existing or not face_ok(p): continue
        add.append({"color":k,"path":p,"file":f,"tag":tag,"ratio":round(ratio,3)})
        existing.add(f); got+=1
        if got>=need: break
    print("  %-8s cur=%d need=%d added=%d"%(k,cur,need,got))

print("to add:",len(add))

# 替换：找出库里分数最低、且颜色为冗余蓝/黑/灰的图
bydom={}
for m in manifest: bydom.setdefault(m["dom"],[]).append(m)
removable=[]
for k in ("blue","black","gray","white"):
    removable += bydom.get(k,[])
removable.sort(key=lambda m:m["score"])
victims=removable[:len(add)]
print("victims:",len(victims),"| lowest score:",victims[0]["score"] if victims else "-")

# 执行替换
for v,a in zip(victims,add):
    # 删旧文件
    old=os.path.join(FINAL,v["file"])
    if os.path.exists(old): os.remove(old)
    # 复制新文件，沿用旧文件名（保持 final_XXX 编号连续）
    shutil.copy2(a["path"],old)
    # 更新 manifest
    for m in manifest:
        if m["file"]==v["file"]:
            m["origin"]=a["file"]; m["src"]=a["tag"]
            m["dom"]=a["color"]; m["forced"]=True
            m["color_ratio"]=a["ratio"]
            break

json.dump(manifest,open(os.path.join(ROOT,"FINAL_200_manifest.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
from collections import Counter
print("final color mix:",dict(Counter(m["dom"] for m in manifest).most_common()))
print("files:",len(os.listdir(FINAL)))
