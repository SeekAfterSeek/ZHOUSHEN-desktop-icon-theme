# -*- coding: utf-8 -*-
"""2026 新图 × 24 APP 配色匹配：生成替换设计方案（不部署）

匹配策略：
  1. 每个 APP 按原图标主色做加权匹配（主色权重高，次色次之）
  2. 24 个 APP 用 24 张互不重复的图
  3. 稀缺色（green/pink/yellow）允许"近似色"兜底，并在报告中标注置信度
"""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
POOL = json.load(open(os.path.join(ROOT, "pool_2026.json"), encoding="utf-8"))
OUTDIR = os.path.join(ROOT, "design_v6")
os.makedirs(OUTDIR, exist_ok=True)

# APP -> (目标色列表, 主色, 描述)
APPS = [
    ("微信",               ["green"],                 "#3EB575"),
    ("QQ音乐",             ["yellow", "cyan"],        "#F5C542"),
    ("哔哩哔哩",           ["pink"],                  "#FF7FA5"),
    ("Google Chrome",      ["red", "yellow", "blue", "green"], "#E8B33C"),
    ("个人 - Edge",        ["blue", "cyan"],          "#3FA9F5"),
    ("360安全浏览器",      ["green"],                 "#57C46B"),
    ("Visual Studio Code", ["blue"],                  "#2F8FE0"),
    ("Cursor",             ["yellow"],                "#F0C24B"),
    ("DeepSeek Harness",   ["black", "gray"],         "#8A9BB0"),
    ("Cherry Studio",      ["red"],                   "#E05555"),
    ("WorkBuddy",          ["cyan", "green"],         "#4FC3B5"),
    ("WPS Office",         ["red"],                   "#D94B3A"),
    ("全能录屏助手",       ["gray", "red"],           "#C96A6A"),
    ("剪映专业版",         ["black", "gray"],         "#9AA5B1"),
    ("百度网盘",           ["gray", "blue"],          "#6FA8DC"),
    ("飞书",               ["blue", "cyan"],          "#4FB6E0"),
    ("Clash Verge",        ["purple", "pink"],        "#B07AE0"),
    ("PyCharm 2026.2.3",   ["gray", "blue"],          "#7E93AD"),
    ("ToDesk",             ["gray", "blue"],          "#5E8FBF"),
    ("互传",               ["blue"],                  "#4A90D9"),
    ("网易邮箱大师",       ["red"],                   "#D9534F"),
    ("联想电脑管家",       ["blue"],                  "#4A7FD9"),
    ("腾讯QQ",             ["gray", "red"],           "#BF6A5A"),
    ("腾讯会议",           ["blue"],                  "#4A85D9"),
]

def score(rec, targets):
    prof = rec["prof"]
    total = 0.0
    for i, t in enumerate(targets):
        w = 1.0 if i == 0 else 0.55
        total += prof.get(t, 0.0) * w
    return total

# 全局贪心分配：先满足稀缺色需求，避免好图被抢
order = sorted(range(len(APPS)), key=lambda i: max(
    (score(r, APPS[i][1]) for r in POOL), default=0))

used = set()
assign = {}
for ai in order:
    name, targets, accent = APPS[ai]
    cands = [r for r in POOL if r["path"] not in used]
    if not cands:
        continue
    cands.sort(key=lambda r: -score(r, targets))
    best = cands[0]
    assign[name] = (best, round(score(best, targets), 3))
    used.add(best["path"])

print("assigned:", len(assign))
for name, targets, accent in APPS:
    if name in assign:
        rec, sc = assign[name]
        print("  %-20s <- %-25s %-6s score=%.3f" % (name, rec["file"][:25], rec["dom"], sc))

json.dump({k: {"file": v[0]["file"], "dom": v[0]["dom"], "score": v[1],
               "src": v[0]["src"], "path": v[0]["path"]}
           for k, v in assign.items()},
          open(os.path.join(OUTDIR, "assign.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
