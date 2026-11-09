# -*- coding: utf-8 -*-
"""把 PNG 母版转成 Windows ICO（多尺寸 BMP 帧）

为什么必须 bitmap_format="bmp"：
    PIL 默认把 ICO 帧存成 PNG。Windows 资源管理器的桌面渲染器
    在小尺寸（16/32/48）下解析 PNG 帧会失败，结果是【空白纸图标】。
    这是本项目踩过的最大的坑，详见 docs/PITFALLS.md 第 1 条。
"""
import os
import sys
import glob
from PIL import Image

SIZES = [256, 128, 64, 48, 32, 16]


def png_to_ico(src, dst, sizes=SIZES):
    im = Image.open(src).convert("RGBA")
    # 先缩到最大尺寸，再让 PIL 生成各档，避免小图放大
    base = im.resize((256, 256), Image.LANCZOS) if im.size != (256, 256) else im
    frames = [base.resize((s, s), Image.LANCZOS) for s in sizes if s <= 256]
    base.save(dst, format="ICO", sizes=[(s, s) for s in sizes],
              append_images=frames[1:], bitmap_format="bmp")
    return dst


def png_to_ico_simple(src, dst, sizes=SIZES):
    """PIL>=9 标准写法：直接给 save 传 sizes，靠 bitmap_format 控制帧格式"""
    im = Image.open(src).convert("RGBA")
    if im.size != (256, 256):
        im = im.resize((256, 256), Image.LANCZOS)
    im.save(dst, format="ICO", sizes=[(s, s) for s in sizes],
            bitmap_format="bmp")
    return dst


if __name__ == "__main__":
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    dst_dir = sys.argv[2] if len(sys.argv) > 2 else src_dir
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for p in sorted(glob.glob(os.path.join(src_dir, "*.png"))):
        name = os.path.splitext(os.path.basename(p))[0]
        if name.lower() in ("preview", "compare", "final", "desktop"):
            continue
        out = os.path.join(dst_dir, name + ".ico")
        try:
            png_to_ico_simple(p, out)
            n += 1
        except Exception as e:
            print("FAIL", name, e)
    print("converted:", n)
