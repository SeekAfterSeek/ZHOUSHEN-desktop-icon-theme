# -*- coding: utf-8 -*-
"""坏图黑名单（人工肉眼确认）
   分类：非周深 / 合影 / 海报带字 / 空舞台 / 活动背景板
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"

BAD = {
    # ---- 非周深 / 含他人 ----
    "studio_20260927_45173_5.jpg": "两人合影(含工作人员)",
    "c929b_1fcdc231d4.png": "非周深(另一位歌手)",
    "c929b_fbd50888c7.png": "非周深(灰毛衣男士)",
    "c929b_a49b1e1330.png": "非周深(戴眼镜男士)",
    "c929_3a2fa12443.jpg": "非周深(红衣普通人)",
    "c929_83666dc72d.jpg": "非周深(红黑格衬衫普通人)",
    "c929b_6ed5d6caf9.png": "非周深(吉他手)",
    "c929b_72ffcab610.jpg": "非周深(立牌模特)",
    "c929b_d23fee2a94.jpg": "活动照(举红牌带字)",
    # ---- 带文字海报 / 立牌 ----
    "c929b_927c64e96b.jpg": "海报带字(倒流回最初的相遇)",
    "c929b_fca45dc1ea.jpg": "海报带字(贵州我的家)",
    "c929b_ca3865fd13.jpg": "海报带字(音乐节)",
    "c929b_03c8d6d29a.jpg": "海报带字(B站跨年)",
    "c929b_6f5a45b458.jpg": "海报带字(B站周年庆)",
    "c929b_ed23c188e9.jpg": "海报带字(电影华表奖)",
    "c929b_866ab15ec9.jpg": "海报带字(B站周年庆)",
    "c929b_28142c3d7f.jpg": "海报带字(春晚)",
    # ---- 空舞台 / 远景 ----
    "studio_20260913_18311_2.jpg": "空舞台",
    "studio_20260810_87642_5.jpg": "远景小舞台",
    "studio_20261019_42056_4.jpg": "远景小舞台",
    "studio_20260806_23802_5.jpg": "远景小舞台",
    "studio_20260726_40288_2.jpg": "远景小舞台",
    "station_20260816_63109_3.jpg": "活动背景板",
    # ---- 拼图 / 多人 ----
    "c929b_8a735893d2.png": "拼图/多人",
    "studio_20261019_42056_4.jpg ": "远景",
    "station_20260822_18127_2.jpg": "远景小人",
}

# 清理键
BAD = {k.strip(): v for k, v in BAD.items()}
# 只保留确实存在于素材库的
PA = {r["file"] for r in json.load(open(os.path.join(ROOT, "pool_all.json"), encoding="utf-8"))}
ok = {k: v for k, v in BAD.items() if k in PA}
missing = [k for k in BAD if k not in PA]
print("确认黑名单 %d 张" % len(ok))
for k, v in sorted(ok.items()):
    print("   %-34s %s" % (k, v))
if missing:
    print("（不在库中，忽略）", missing)

json.dump(ok, open(os.path.join(ROOT, "bad_by_review.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> bad_by_review.json")
