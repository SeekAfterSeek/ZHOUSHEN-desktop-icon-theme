# -*- coding: utf-8 -*-
"""v9：按【原图标真实配色】× 【衣服颜色】重新匹配

评分 = Σ（原图标该色占比 × 照片衣服该色占比），取前 2 色加权
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
DESIGN = os.path.join(ROOT,"design_v9")
os.makedirs(DESIGN, exist_ok=True)

PAL = json.load(open(os.path.join(ROOT,"design_v8","icon_palette.json"),encoding="utf-8"))
pool = json.load(open(os.path.join(ROOT,"cloth_pool.json"),encoding="utf-8"))
print("pool:", len(pool))

def ok(path):
    """只有合格的近景单人照才进入候选"""
    try: im = Image.open(path).convert("RGB")
    except Exception: return False
    if min(im.size) < 480: return False
    a = np.asarray(im.resize((128,128)), dtype=np.int16)
    r,g,b = a[...,0],a[...,1],a[...,2]; mx=a.max(axis=2); mn=a.min(axis=2)
    skin = (r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    ratio = skin.sum()/16384.0
    if ratio < 0.035: return False
    ys,xs = np.nonzero(skin)
    if np.sqrt(xs.var()+ys.var())/128 > 0.26: return False
    g64 = np.asarray(im.convert("L").resize((128,128)),dtype=np.float32)
    if (np.abs(np.diff(g64,axis=0)).mean(axis=1)>60).sum() >= 2: return False
    if (np.abs(np.diff(g64,axis=1)).mean(axis=0)>60).sum() >= 2: return False
    if g64[:12].std() < 8: return False
    return True

cand_pool = [r for r in pool if ok(r["path"])]
print("qualified:", len(cand_pool))
from collections import Counter
print("cloth mix:", dict(Counter(r["dom"] for r in cand_pool).most_common()))

def fit(icon_pal, cloth_all):
    """原图标配色 × 衣服配色 的契合度"""
    s = 0.0
    for k, w in icon_pal.items():
        if w <= 0.02: continue
        s += w * cloth_all.get(k, 0.0)
    return s

def assign_all():
    used = set(); result = {}
    # 稀缺优先：对每个 APP 算最佳可得分，低的先挑
    scores = {}
    for n in PAL:
        if not PAL[n]: continue
        best = max((fit(PAL[n], r["all"]) for r in cand_pool if r["file"] not in used), default=0)
        scores[n] = best
    for n in sorted(scores, key=lambda x: scores[x]):
        cands = [r for r in cand_pool if r["file"] not in used]
        if not cands: continue
        cands.sort(key=lambda r: -fit(PAL[n], r["all"]))
        best = cands[0]
        result[n] = {"file": best["file"], "cloth": best["dom"], "conf": best["conf"],
                     "fit": round(fit(PAL[n], best["all"]), 3), "path": best["path"]}
        used.add(best["file"])
    return result

assign = assign_all()
print("\n=== 匹配结果（按原图标配色 × 衣服色）===")
for n, v in assign.items():
    icon_top = sorted(PAL[n].items(), key=lambda x:-x[1])[0]
    print("  %-20s 图标色 %-7s -> 衣服 %-7s fit=%.2f" % (n, icon_top[0], v["cloth"], v["fit"]))

json.dump(assign, open(os.path.join(DESIGN,"assign.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)

# 渲染
sys.path.insert(0, ROOT)
import render_lib
render_lib.DESIGN = DESIGN
imgs = render_lib.render_all()
print("\nrendered:", len(imgs))

# 对照图：旧图标 | v8(背景配色) | v9(衣服配色)
f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14)
v8 = os.path.join(ROOT,"design_v8")
ORDER = render_lib.ORDER
cellw, cols = 200, 3
rows = (len(ORDER)+cols-1)//cols
comp = Image.new("RGB", (cols*(cellw*3+24), rows*(cellw+38)), (26,26,34))
d = ImageDraw.Draw(comp)
for i, n in enumerate(ORDER):
    x, y = (i%cols)*(cellw*3+24), (i//cols)*(cellw+38)
    # 原图标
    op = os.path.join(ROOT,"backup","original-icons-256",n+".png")
    if os.path.exists(op):
        oi = Image.open(op).convert("RGBA").resize((cellw-12,cellw-12), Image.LANCZOS)
        comp.paste(oi,(x+6,y+6),oi)
    # v8
    p8 = os.path.join(v8,n+".png")
    if os.path.exists(p8):
        i8 = Image.open(p8).convert("RGBA").resize((cellw-12,cellw-12), Image.LANCZOS)
        comp.paste(i8,(x+cellw+12,y+6),i8)
    # v9
    if n in imgs:
        i9 = imgs[n].resize((cellw-12,cellw-12), Image.LANCZOS)
        comp.paste(i9,(x+cellw*2+18,y+6),i9)
    d.text((x+8,y+cellw),"原图标",font=f,fill=(150,150,160))
    d.text((x+cellw+14,y+cellw),"v8 背景色",font=f,fill=(180,180,190))
    d.text((x+cellw*2+20,y+cellw),"v9 衣服色",font=f,fill=(120,230,160))
    bb = d.textbbox((0,0),n,font=f)
    d.text((x+(cellw*3-(bb[2]-bb[0]))//2, y+cellw+18), n, font=f, fill=(235,235,242))
comp.save(os.path.join(DESIGN,"compare_v9.png"))

# 总览
cell2, cols2 = 210, 4
rows2 = (len(imgs)+cols2-1)//cols2
sheet = Image.new("RGB",(cols2*cell2, rows2*(cell2+34)),(30,30,40))
d2 = ImageDraw.Draw(sheet)
for i,n in enumerate(ORDER):
    if n not in imgs: continue
    x,y = (i%cols2)*cell2, (i//cols2)*(cell2+34)
    ic = imgs[n].resize((170,170),Image.LANCZOS)
    sheet.paste(ic,(x+20,y+6),ic)
    bb = d2.textbbox((0,0),n,font=f)
    d2.text((x+(cell2-(bb[2]-bb[0]))//2, y+cell2-6), n, font=f, fill=(235,235,242))
sheet.save(os.path.join(DESIGN,"preview_v9.png"))
print("DONE ->", DESIGN)
