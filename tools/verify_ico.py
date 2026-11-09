# -*- coding: utf-8 -*-
"""校验 ICO 帧格式：必须是多尺寸 BMP(DIB) 帧，不能是 PNG 帧"""
import struct, glob, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

pattern = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\DSH\workspace\SMALL RESULT\zs-icon-theme-release\themes\*\icons\*.ico"

files = sorted(glob.glob(pattern))
bad = 0
for p in files:
    b = open(p, "rb").read()
    cnt = struct.unpack("<H", b[4:6])[0]
    sizes, npng = [], 0
    for i in range(cnt):
        w, h, cc, rr, pl, bc, sz, ofs = struct.unpack("<BBBBHHII", b[6 + i * 16:6 + i * 16 + 16])
        w = w or 256
        sizes.append(w)
        if b[ofs:ofs + 8] == b"\x89PNG\r\n\x1a\n":
            npng += 1
    flag = "OK "
    if npng or cnt < 5:
        flag = "BAD"
        bad += 1
    if flag == "BAD" or p == files[0]:
        print("%s %-28s frames=%d sizes=%s png_frames=%d"
              % (flag, os.path.basename(p), cnt, sizes, npng))

print("\n总计 %d 个 ICO，异常 %d 个" % (len(files), bad))
