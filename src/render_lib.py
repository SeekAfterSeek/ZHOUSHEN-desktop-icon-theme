# -*- coding: utf-8 -*-
"""纯渲染模块：读取 assign.json 渲染图标，不做任何分配/替换逻辑"""
import os, sys, json, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
DESIGN = os.path.join(ROOT, "design_v8")
S = 256; BADGE = 96; PAD = 8
ORIG = os.path.join(ROOT, "backup", "original-icons-256")

ACCENTS = {
    "微信":"#3EB575","QQ音乐":"#F5C542","哔哩哔哩":"#FF7FA5","Google Chrome":"#E8B33C",
    "个人 - Edge":"#3FA9F5","360安全浏览器":"#57C46B","Visual Studio Code":"#2F8FE0",
    "Cursor":"#F0C24B","DeepSeek Harness":"#8A9BB0","Cherry Studio":"#E05555",
    "WorkBuddy":"#4FC3B5","WPS Office":"#D94B3A","全能录屏助手":"#C96A6A",
    "剪映专业版":"#9AA5B1","百度网盘":"#6FA8DC","飞书":"#4FB6E0","Clash Verge":"#B07AE0",
    "PyCharm 2026.2.3":"#7E93AD","ToDesk":"#5E8FBF","互传":"#4A90D9",
    "网易邮箱大师":"#D9534F","联想电脑管家":"#4A7FD9","腾讯QQ":"#BF6A5A","腾讯会议":"#4A85D9",
}
ORDER = ["微信","QQ音乐","哔哩哔哩","Google Chrome","个人 - Edge","360安全浏览器",
         "Visual Studio Code","Cursor","DeepSeek Harness","Cherry Studio","WorkBuddy",
         "WPS Office","全能录屏助手","剪映专业版","百度网盘","飞书","Clash Verge",
         "PyCharm 2026.2.3","ToDesk","互传","网易邮箱大师","联想电脑管家","腾讯QQ","腾讯会议"]
SHAPES = ["squircle","circle","arch","pebble","blob"]

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def mask_for(shape, seed):
    m = Image.new("L",(S,S),0); d = ImageDraw.Draw(m); rnd = random.Random(seed)
    if shape=="squircle": d.rounded_rectangle([6,6,S-7,S-7],radius=int(S*.30),fill=255)
    elif shape=="circle": d.ellipse([8,8,S-9,S-9],fill=255)
    elif shape=="arch":
        r=(S-20)//2; d.pieslice([10,10,10+2*r,10+2*r],180,360,fill=255)
        d.rectangle([10,10+r,10+2*r,S-8],fill=255)
    elif shape=="pebble": d.ellipse([10,int(S*.16),S-11,int(S*.84)+20],fill=255)
    else:
        cx=cy=S/2; base=S*.44
        hs=[(rnd.uniform(.03,.08),rnd.randint(2,4),rnd.uniform(0,6.28)),
            (rnd.uniform(.02,.05),rnd.randint(5,7),rnd.uniform(0,6.28))]
        pts=[]
        for i in range(120):
            th=i/120*2*math.pi
            rr=base*(1+sum(a*math.sin(k*th+ph) for a,k,ph in hs))
            pts.append((cx+rr*math.cos(th),cy+rr*math.sin(th)))
        d.polygon(pts,fill=255)
    return m

def face_focus(path):
    a=np.asarray(Image.open(path).convert("RGB").resize((128,128)),dtype=np.int16)
    r,g,b=a[...,0],a[...,1],a[...,2]; mx=a.max(axis=2); mn=a.min(axis=2)
    skin=(r>95)&(g>40)&(b>20)&(r>g)&(r>b)&((mx-mn)>15)&((r-g)>15)&(np.abs(r-g)>10)
    skin[int(128*.6):,:]=False
    ys,xs=np.nonzero(skin)
    if len(ys)<40: return .5,.34
    return (float(np.clip(np.percentile(xs,[30,70]).mean()/128,.15,.85)),
            float(np.clip((np.percentile(ys,25)*.75+np.percentile(ys,65)*.25)/128,.1,.55)))

def render(name, photo, shape, seed):
    accent = ACCENTS[name]
    fx,fy = face_focus(photo)
    im = Image.open(photo).convert("RGB")
    zoom = max(1.02,min(1.32,1.14+(0.38-fy)*.35))
    w,h = im.size; sc=max(S/w,S/h)*zoom; nw,nh=int(w*sc),int(h*sc)
    im = im.resize((nw,nh),Image.LANCZOS)
    left=max(0,min(int(nw*fx-S/2),nw-S)); top=max(0,min(int(nh*fy-S/2),nh-S))
    cv = im.crop((left,top,left+S,top+S)).convert("RGBA")
    rgb = ImageEnhance.Color(cv.convert("RGB")).enhance(1.28)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.16)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    cv = rgb.convert("RGBA")
    ar = hexrgb(accent); rnd = random.Random(seed); mask = mask_for(shape,seed)
    cut = Image.new("RGBA",(S,S),(0,0,0,0)); cut.paste(cv,(0,0),mask); cv = cut
    glow = Image.new("RGBA",(S,S),ar+(0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v:int(v*.55)))
    cv = Image.alpha_composite(glow,cv)
    edge = Image.new("RGBA",(S,S),ar+(0,))
    em = mask.filter(ImageFilter.MaxFilter(5))
    em = Image.composite(Image.new("L",(S,S),255),Image.new("L",(S,S),0),
                         Image.eval(Image.composite(em,Image.new("L",(S,S),0),mask),lambda v:255-v))
    edge.putalpha(em.point(lambda v:int(v*.85)))
    cv = Image.alpha_composite(cv,edge)
    hi = Image.new("RGBA",(S,S),(0,0,0,0))
    ImageDraw.Draw(hi).ellipse([-S*.2,-S*.25,S*.75,S*.55],fill=(255,255,255,42))
    hi = hi.filter(ImageFilter.GaussianBlur(28))
    hi.putalpha(Image.composite(hi.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,hi)
    sp = Image.new("RGBA",(S,S),(0,0,0,0)); sd = ImageDraw.Draw(sp)
    for cx,cy in rnd.sample([(.12,.12),(.88,.12),(.10,.78),(.90,.80)],3):
        x=int(S*cx+rnd.uniform(-12,12)); y=int(S*cy+rnd.uniform(-10,10))
        r1=rnd.uniform(6,11); r2=r1*.28
        sd.polygon([(x,y-r1),(x+r2,y-r2),(x+r1,y),(x+r2,y+r2),(x,y+r1),(x-r2,y+r2),
                    (x-r1,y),(x-r2,y-r2)],fill=(255,255,255,rnd.randint(100,170)))
    sp.putalpha(Image.composite(sp.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,sp)
    gd = Image.new("RGBA",(S,S),(0,0,0,0)); g = ImageDraw.Draw(gd)
    for yy in range(S-70,S): g.line([(0,yy),(S,yy)],fill=(4,10,26,int(60*(yy-(S-70))/70)))
    gd.putalpha(Image.composite(gd.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,gd)
    op = os.path.join(ORIG,name+".png")
    if os.path.exists(op):
        logo = Image.open(op).convert("RGBA"); logo.thumbnail((int(BADGE*.66),)*2,Image.LANCZOS)
        bd = Image.new("RGBA",(BADGE,BADGE),(0,0,0,0))
        ImageDraw.Draw(bd).ellipse([0,0,BADGE-1,BADGE-1],fill=(255,255,255,248),
                                   outline=(16,30,54,210),width=3)
        bd.paste(logo,((BADGE-logo.width)//2,(BADGE-logo.height)//2),logo)
        bx,by = S-BADGE-PAD, S-BADGE-PAD
        sh = Image.new("RGBA",(S,S),(0,0,0,0))
        sh.paste(Image.new("RGBA",bd.size,(0,0,0,130)),(bx+2,by+5),bd.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        cv = Image.alpha_composite(cv,sh); cv.paste(bd,(bx,by),bd)
    soft = mask.filter(ImageFilter.GaussianBlur(8)).point(lambda v:min(255,v*2))
    cv.putalpha(Image.composite(cv.split()[3],Image.eval(soft,lambda v:int(v*.5)),
                                Image.eval(mask,lambda v:255 if v>200 else 0)))
    cv.save(os.path.join(DESIGN,name+".png"))
    return cv

def render_all():
    assign = json.load(open(os.path.join(DESIGN,"assign.json"),encoding="utf-8"))
    imgs = {}
    for i,n in enumerate(ORDER):
        if n not in assign: continue
        imgs[n] = render(n, assign[n]["path"], SHAPES[i%len(SHAPES)], 1000+i*37)
    return imgs

if __name__ == "__main__":
    imgs = render_all()
    print("rendered:", len(imgs))
