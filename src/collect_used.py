# -*- coding: utf-8 -*-
"""汇总历史所有版本用过的照片（v3~v11），形成排除名单"""
import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
ALIAS = json.load(open(os.path.join(ROOT, "final_alias.json"), encoding="utf-8"))

USED = set()
detail = {}

for ver in ("design_v7", "design_v8", "design_v9", "design_v10", "design_v11"):
    p = os.path.join(ROOT, ver, "assign.json")
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding="utf-8"))
    fs = set()
    for n, v in d.items():
        f = v.get("file")
        if not f:
            continue
        f = ALIAS.get(f, f)
        fs.add(f)
    detail[ver] = fs
    USED |= fs
    print("%-12s %d 张" % (ver, len(fs)))

# v3/v4/v5 的老结构也扫一遍
for pat in ("icons*/*.json", "*assign*.json", "design_v6/*.json"):
    for p in glob.glob(os.path.join(ROOT, pat)):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        got = 0
        for n, v in d.items():
            if isinstance(v, dict):
                f = v.get("file")
                if f:
                    USED.add(ALIAS.get(f, f)); got += 1
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                f = v[0].get("file")
                if f:
                    USED.add(ALIAS.get(f, f)); got += 1
        if got:
            print("%-40s %d 张" % (os.path.relpath(p, ROOT), got))

print("\n历史用过（去重后）:", len(USED))
json.dump(sorted(USED), open(os.path.join(ROOT, "used_history.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
