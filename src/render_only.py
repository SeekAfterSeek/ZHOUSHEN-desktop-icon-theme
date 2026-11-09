# -*- coding: utf-8 -*-
"""纯渲染：只读 assign.json（已含 path/fx/fy/face），不扫池、不分析"""
import sys, io, os, json, math, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
DESIGN = os.path.join(ROOT,"design_v10")
S=256; BADGE=96; PAD=8
ORIG=os.path.join(ROOT,"backup","original-icons-256")

assign = json.load(open(os.path.join(DESIGN,"assign.json"),encoding="utf-8"))
ORDER = ["微信","QQ音乐","哔哩哔哩","Google Chrome","个人 - Edge","360安全浏览器",
         "Visual Studio Code","Cursor","DeepSeek Harness","Cherry Studio","WorkBuddy",
         "WPS Office","全能录屏助手","剪映专业版","百度网盘","飞书","Clash Verge",
         "PyCharm 2026.2.3","ToDesk","互传","网易邮箱大师","联想电脑管家","腾讯QQ","腾讯会议"]
SHAPES = ["squircle","circle","arch","pebble","blob"]
ACCENTS = {"微信":"#3EB575","QQ音乐":"#F5C542","哔哩哔哩":"#FF7FA5","Google Chrome":"#E8B33C",
    "个人 - Edge":"#3FA9F5","360安全浏览器":"#57C46B","Visual Studio Code":"#2F8FE0",
    "Cursor":"#5A5A5A","DeepSeek Harness":"#A8B8C8","Cherry Studio":"#E05555",
    "WorkBuddy":"#4FC3B5","WPS Office":"#D94B3A","全能录屏助手":"#8A4038",
    "剪映专业版":"#5A5A5A","百度网盘":"#7FB8E8","飞书":"#4FB6E0","Clash Verge":"#B07AE0",
    "PyCharm 2026.2.3":"#3E845F","ToDesk":"#8FC4E8","互传":"#7FB0E0",
    "网易邮箱大师":"#D9534F","联想电脑管家":"#4A7FD9","腾讯QQ":"#7F5547","腾讯会议":"#4A85D9"}

def hexrgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def mask_for(shape,seed):
    m=Image.new("L",(S,S),0); d=ImageDraw.Draw(m); rnd=random.Random(seed)
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

imgs={}
for i,n in enumerate(ORDER):
    info = assign.get(n)
    if not info: continue
    accent = ACCENTS.get(n,"#888888")
    fx,fy,face = info["fx"],info["fy"],info["face"]
    im = Image.open(info["path"]).convert("RGB")
    zoom = 1.60 if face<0.012 else 1.45 if face<0.025 else 1.32 if face<0.045 else 1.20 if face<0.08 else 1.10
    w,h = im.size; sc=max(S/w,S/h)*zoom; nw,nh=int(w*sc),int(h*sc)
    im = im.resize((nw,nh), Image.LANCZOS)
    left = max(0,min(int(nw*fx-S/2),nw-S))
    top  = max(0,min(int(nh*fy-S*0.40),nh-S))
    cv = im.crop((left,top,left+S,top+S)).convert("RGBA")
    rgb = ImageEnhance.Color(cv.convert("RGB")).enhance(1.28)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.16)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.05)
    cv = rgb.convert("RGBA")
    ar = hexrgb(accent); rnd=random.Random(2000+i*41)
    shape = SHAPES[i%len(SHAPES)]
    mask = mask_for(shape, 2000+i*41)
    cut = Image.new("RGBA",(S,S),(0,0,0,0)); cut.paste(cv,(0,0),mask); cv=cut
    glow = Image.new("RGBA",(S,S),ar+(0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(10)).point(lambda v:int(v*.55)))
    cv = Image.alpha_composite(glow,cv)
    edge = Image.new("RGBA",(S,S),ar+(0,)); em=mask.filter(ImageFilter.MaxFilter(5))
    em = Image.composite(Image.new("L",(S,S),255),Image.new("L",(S,S),0),
        Image.eval(Image.composite(em,Image.new("L",(S,S),0),mask),lambda v:255-v))
    edge.putalpha(em.point(lambda v:int(v*.85))); cv=Image.alpha_composite(cv,edge)
    hi = Image.new("RGBA",(S,S),(0,0,0,0))
    ImageDraw.Draw(hi).ellipse([-S*.2,-S*.25,S*.75,S*.55],fill=(255,255,255,42))
    hi = hi.filter(ImageFilter.GaussianBlur(28))
    hi.putalpha(Image.composite(hi.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,hi)
    sp = Image.new("RGBA",(S,S),(0,0,0,0)); sd=ImageDraw.Draw(sp)
    for cx,cy in rnd.sample([(.12,.12),(.88,.12),(.10,.78),(.90,.80)],3):
        x=int(S*cx+rnd.uniform(-12,12)); y=int(S*cy+rnd.uniform(-10,10))
        r1=rnd.uniform(6,11); r2=r1*.28
        sd.polygon([(x,y-r1),(x+r2,y-r2),(x+r1,y),(x+r2,y+r2),(x,y+r1),(x-r2,y+r2),
                    (x-r1,y),(x-r2,y-r2)],fill=(255,255,255,rnd.randint(100,170)))
    sp.putalpha(Image.composite(sp.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,sp)
    gd = Image.new("RGBA",(S,S),(0,0,0,0)); g=ImageDraw.Draw(gd)
    for yy in range(S-70,S): g.line([(0,yy),(S,yy)],fill=(4,10,26,int(55*(yy-(S-70))/70)))
    gd.putalpha(Image.composite(gd.split()[3],Image.new("L",(S,S),0),mask))
    cv = Image.alpha_composite(cv,gd)
    op = os.path.join(ORIG,n+".png")
    if os.path.exists(op):
        logo=Image.open(op).convert("RGBA"); logo.thumbnail((int(BADGE*.66),)*2,Image.LANCZOS)
        bd=Image.new("RGBA",(BADGE,BADGE),(0,0,0,0))
        ImageDraw.Draw(bd).ellipse([0,0,BADGE-1,BADGE-1],fill=(255,255,255,248),
                                   outline=(16,30,54,210),width=3)
        bd.paste(logo,((BADGE-logo.width)//2,(BADGE-logo.height)//2),logo)
        bx,by=S-BADGE-PAD,S-BADGE-PAD
        sh=Image.new("RGBA",(S,S),(0,0,0,0))
        sh.paste(Image.new("RGBA",bd.size,(0,0,0,130)),(bx+2,by+5),bd.split()[3])
        sh=sh.filter(ImageFilter.GaussianBlur(6))
        cv=Image.alpha_composite(cv,sh); cv.paste(bd,(bx,by),bd)
    soft=mask.filter(ImageFilter.GaussianBlur(8)).point(lambda v:min(255,v*2))
    cv.putalpha(Image.composite(cv.split()[3],Image.eval(soft,lambda v:int(v*.5)),
                                Image.eval(mask,lambda v:255 if v>200 else 0)))
    cv.save(os.path.join(DESIGN,n+".png"))
    imgs[n]=cv

print("rendered:",len(imgs))
f=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc",15)
c2,cols2=210,4; r2=(len(imgs)+cols2-1)//cols2
sheet=Image.new("RGB",(cols2*c2,r2*(c2+34)),(30,30,40)); d2=ImageDraw.Draw(sheet)
for i,n in enumerate(ORDER):
    if n not in imgs: continue
    x,y=(i%cols2)*c2,(i//cols2)*(c2+34)
    ic=imgs[n].resize((170,170),Image.LANCZOS); sheet.paste(ic,(x+20,y+6),ic)
    bb=d2.textbbox((0,0),n,font=f)
    d2.text((x+(c2-(bb[2]-bb[0]))//2,y+c2-6),n,font=f,fill=(235,235,242))
sheet.save(os.path.join(DESIGN,"preview_v10.png"))
print("DONE")
