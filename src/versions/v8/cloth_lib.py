# -*- coding: utf-8 -*-
"""衣服颜色识别：纯函数模块（无顶层副作用）"""
import numpy as np
from PIL import Image

HUES = ["red","orange","yellow","green","cyan","blue","purple","pink"]

def face_center(a):
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>95*1.0)&(g>40*1.0)  # placeholder, overwritten below
    # a is float 0..1
    r,g,b=a[...,0],a[...,1],a[...,2];mx=a.max(axis=2);mn=a.min(axis=2)
    skin=(r>0.37)&(g>0.16)&(b>0.08)&(r>g)&(r>b)&((mx-mn)>0.06)&((r-g)>0.06)
    skin[int(a.shape[0]*0.62):,:]=False
    ys,xs=np.nonzero(skin)
    if len(ys)<40: return 0.5,0.34
    return (float(np.clip(np.percentile(xs,[30,70]).mean()/a.shape[1],.15,.85)),
            float(np.clip((np.percentile(ys,25)*.75+np.percentile(ys,65)*.25)/a.shape[0],.1,.55)))

def cloth_color(path):
    try: im=Image.open(path).convert("RGB")
    except Exception: return None
    R=192
    a=np.asarray(im.resize((R,R)),dtype=np.float32)/255.0
    fx,fy=face_center(a)
    y0=max(0,int((fy+0.10)*R)); y1=min(R,int((fy+0.46)*R))
    x0=max(0,int((fx-0.17)*R)); x1=min(R,int((fx+0.17)*R))
    if y1-y0<12 or x1-x0<12: return None
    reg=a[y0:y1,x0:x1]
    mx=reg.max(axis=2);mn=reg.min(axis=2);l=(mx+mn)/2
    s=np.where(mx==mn,0,(mx-mn)/np.maximum(1e-6,1-np.abs(2*l-1)))
    rr,gg,bb=reg[...,0],reg[...,1],reg[...,2];dd=mx-mn+1e-6
    h=np.where(mx==rr,((gg-bb)/dd)%6,np.where(mx==gg,(bb-rr)/dd+2,(rr-gg)/dd+4))*60
    is_skin=(rr>0.42)&(gg>0.20)&(bb>0.10)&(rr>gg)&(rr>bb)&((rr-gg)>0.06)
    ok=(s>=0.22)&(l>=0.10)&(l<=0.92)&(~is_skin)
    n=float(reg.shape[0]*reg.shape[1])   # 统一分母 = 衣服区总像素
    ev={}
    ev["black"]=float(((l<0.10)&(~is_skin)).sum()/n)
    ev["white"]=float(((l>0.88)&(~is_skin)).sum()/n)
    ev["gray"]=float(((s<0.18)&(l>=0.10)&(l<=0.88)).sum()/n)
    for k,(lo,hi) in zip(HUES,[(345,15),(15,40),(40,70),(70,165),(165,200),(200,265),(265,310),(310,345)]):
        m=(((h>=lo)|(h<hi))&ok) if lo>hi else ((h>=lo)&(h<hi)&ok)
        ev[k]=float(m.sum()/n)
    dom=max(ev,key=ev.get)
    return {"dom":dom,"conf":round(float(ev[dom]),3),
            "all":{k:round(float(v),3) for k,v in ev.items()},
            "fx":round(fx,2),"fy":round(fy,2)}
