# -*- coding: utf-8 -*-
"""给 PowerShell 脚本加 UTF-8 BOM

为什么：Windows PowerShell 5.1（powershell.exe）在没有 BOM 时会按系统 ANSI
代码页读取 .ps1。脚本里的中文会变成乱码，并且会把字符串的引号"吃掉"，
报 `Unexpected token` / `Missing argument`。加 BOM 后按 UTF-8 正确解析。
"""
import sys, os, glob

BOM = b"\xef\xbb\xbf"

targets = sys.argv[1:] or ["*.ps1"]
files = []
for t in targets:
    files.extend(glob.glob(t, recursive=True))

n = 0
for p in sorted(set(files)):
    if not os.path.isfile(p) or not p.lower().endswith(".ps1"):
        continue
    raw = open(p, "rb").read()
    if raw.startswith(BOM):
        print("已有 BOM:", p)
        continue
    open(p, "wb").write(BOM + raw)
    n += 1
    print("已加 BOM:", p)

print("\n处理 %d 个文件" % n)
