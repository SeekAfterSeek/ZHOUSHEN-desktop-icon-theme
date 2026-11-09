# -*- coding: utf-8 -*-
"""调色引擎：把照片的配色向原图标真实配色靠拢
   * 保护人脸/皮肤（不换肤色）
   * 色相旋转 + 饱和度缩放 + 亮度伽马，全部在非皮肤区做
   * 强制黑白倾向（原图标黑/白为主时）
   * 少量"补色"：原图标有照片完全缺失的颜色时，给背景补一层极淡的该色光
"""
import numpy as np


HUES = ["black", "white", "gray", "red", "orange", "yellow", "green",
        "cyan", "blue", "purple", "pink"]
# 各色相名义饱和度（用于估目标彩度）
NOM_S = {"red": 0.86, "orange": 0.85, "yellow": 0.92, "green": 0.70,
         "cyan": 0.70, "blue": 0.78, "purple": 0.62, "pink": 0.66}
HUE_CENTER = {"red": 0.0, "orange": 27.0, "yellow": 55.0, "green": 118.0,
              "cyan": 182.0, "blue": 232.0, "purple": 288.0, "pink": 328.0}


def rgb2hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = a.max(axis=2); mn = a.min(axis=2)
    dd = mx - mn
    l = mx
    s = np.where(mx <= 1e-6, 0.0, dd / np.maximum(1e-6, mx))
    h = np.zeros_like(mx)
    nz = dd > 1e-6
    rr = nz & (mx == r)
    gg = nz & (mx == g) & ~rr
    bb = nz & ~rr & ~gg
    h[rr] = (((g - b)[rr] / dd[rr]) % 6)
    h[gg] = ((b - r)[gg] / dd[gg] + 2)
    h[bb] = ((r - g)[bb] / dd[bb] + 4)
    return h * 60.0, s, l


def hsv2rgb(h, s, v):
    h = (h % 360.0) / 60.0
    i = np.floor(h).astype(np.int32) % 6
    f = h - np.floor(h)
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,), dtype=np.float32)
    for k, (rr, gg, bb) in enumerate(((v, t, p), (q, v, p), (p, v, t),
                                      (p, q, v), (t, p, v), (v, p, q))):
        m = i == k
        out[..., 0][m] = rr[m]; out[..., 1][m] = gg[m]; out[..., 2][m] = bb[m]
    return out


def target_spec(pal):
    """从原图标 palette 推目标：主色相、目标饱和度、黑白灰比例、目标亮度"""
    tot = sum(pal.values()) or 1.0
    chrom = {k: v for k, v in pal.items() if k in HUE_CENTER and v > 0.02}
    achroma = sum(pal.get(k, 0) for k in ("black", "white", "gray"))
    cw = sum(chrom.values())
    if cw > 1e-6:
        # 圆周加权平均色相
        ang = np.array([np.deg2rad(HUE_CENTER[k]) for k in chrom])
        w = np.array([chrom[k] for k in chrom])
        cx = float((w * np.cos(ang)).sum() / w.sum())
        sx = float((w * np.sin(ang)).sum() / w.sum())
        thue = float(np.rad2deg(np.arctan2(sx, cx)) % 360)
        tsat = float(sum(NOM_S.get(k, 0.7) * v for k, v in chrom.items()) / cw)
        # 主色相（占比最高的彩色）
        main = max(chrom, key=chrom.get)
        tspan = [HUE_CENTER[k] for k, v in chrom.items() if v >= 0.10]
    else:
        thue, tsat, main, tspan = None, 0.0, None, []
    # 黑白灰的目标平均亮度
    if pal.get("black", 0) >= 0.30:
        tlum = 0.20
    elif pal.get("white", 0) >= 0.35:
        tlum = 0.84
    elif achroma >= 0.55:
        tlum = 0.55
    else:
        tlum = None
    return {"hue": thue, "sat": tsat, "achroma": achroma / tot,
            "main": main, "spans": tspan,
            "black": pal.get("black", 0), "white": pal.get("white", 0),
            "gray": pal.get("gray", 0), "tlum": tlum,
            "chrom": chrom, "cweight": cw / tot}


def grade(rgb, pal, skin_mask=None, strength=1.0, out_mask=None):
    """rgb: float32 HxWx3 (0..1)。返回调色后的 rgb"""
    if pal is None:
        return rgb
    spec = target_spec(pal)
    h, s, v = rgb2hsv(rgb.astype(np.float32))
    lum = rgb.mean(axis=2)

    act = np.ones(rgb.shape[:2], bool) if out_mask is None else out_mask
    if skin_mask is not None:
        act = act & (~skin_mask)

    # ---------- 1) 色相 + 饱和度 ----------
    if spec["hue"] is not None and spec["cweight"] > 0.18:
        chrom_m = act & (s > 0.16) & (v > 0.06)
        if chrom_m.sum() > 200:
            # 圆周平均源色相
            a2 = np.deg2rad(h[chrom_m]); w2 = s[chrom_m] * v[chrom_m]
            if w2.sum() > 1e-6:
                scx = float((w2 * np.cos(a2)).sum() / w2.sum())
                ssx = float((w2 * np.sin(a2)).sum() / w2.sum())
                shue = float(np.rad2deg(np.arctan2(ssx, scx)) % 360)
                dh = ((spec["hue"] - shue + 180) % 360) - 180
                dh *= strength * 0.92
                h = np.where(chrom_m, (h + dh) % 360.0, h)
                ssat = float(np.average(s[chrom_m], weights=np.maximum(v[chrom_m], .05)))
                if ssat > 1e-3:
                    scale = np.clip(spec["sat"] / ssat, 0.72, 1.85)
                    scale = 1.0 + (scale - 1.0) * strength
                    s = np.where(chrom_m, np.clip(s * scale, 0, 1), s)

    # ---------- 2) 亮度（黑白倾向） ----------
    if spec["tlum"] is not None:
        base = float(np.average(lum[act], weights=np.maximum(lum[act], .02))) \
            if act.sum() > 100 else float(lum.mean())
        base = max(base, 1e-3)
        ratio = spec["tlum"] / base
        ratio = 1.0 + (ratio - 1.0) * strength * 0.80
        # 用伽马实现，保留层次
        g = float(np.clip(np.log(max(ratio, 1e-3)) / np.log(2.0), -0.85, 0.85))
        v2 = np.clip(v ** (1.0 / max(1e-3, 2.0 ** g)), 0, 1)
        if skin_mask is None:
            v = v2
        else:
            v = np.where(skin_mask, v, v2)

    out = hsv2rgb(h, s, v)

    # ---------- 3) 缺失色补光（只在背景/非皮肤） ----------
    miss = [k for k in ("red", "orange", "yellow", "green", "cyan", "blue",
                        "purple", "pink")
            if spec["chrom"].get(k, 0) >= 0.10]
    if miss:
        cur = {}
        mx = out.max(axis=2); mn = out.min(axis=2)
        dd = mx - mn
        hh = h.copy()
        for k in HUE_CENTER:
            lo = (HUE_CENTER[k] - 22) % 360
            hi = (HUE_CENTER[k] + 22) % 360
            cur[k] = float((((hh >= lo) & (hh <= hi)) & (dd > 0.10) & act).sum()
                           / max(1, act.sum()))
        lack = [k for k in miss if cur.get(k, 0) < 0.055]
        if lack:
            # 给背景（非人脸、非主体中央椭圆）淡淡补色
            H_, W_ = rgb.shape[:2]
            yy, xx = np.mgrid[0:H_, 0:W_]
            cy0, cx0 = H_ * 0.42, W_ * 0.50
            r_norm = np.sqrt(((xx - cx0) / (W_ * 0.55)) ** 2
                             + ((yy - cy0) / (H_ * 0.62)) ** 2)
            bgm = act & (r_norm > 0.85)
            if skin_mask is not None:
                bgm = bgm & (~skin_mask)
            if bgm.sum() > 300:
                add = np.zeros_like(out)
                for k in lack[:2]:
                    lo = (HUE_CENTER[k] - 26) % 360
                    hi = (HUE_CENTER[k] + 26) % 360
                    band = ((hh >= lo) & (hh <= hi)) if lo < hi else \
                           ((hh >= lo) | (hh <= hi))
                    tgt = np.zeros_like(out)
                    tgt[...] = hsv2rgb(np.full_like(hh, HUE_CENTER[k]),
                                       np.full_like(hh, 0.62),
                                       np.maximum(mn, 0.35))
                    wgt = (bgm & band).astype(np.float32) * 0.30 + bgm.astype(np.float32) * 0.10
                    add += tgt * wgt[..., None]
                out = np.clip(out + add / max(1, len(lack[:2])), 0, 1)

    return np.clip(out, 0, 1)
