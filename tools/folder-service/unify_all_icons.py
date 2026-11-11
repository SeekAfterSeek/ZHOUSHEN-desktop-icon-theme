# -*- coding: utf-8 -*-
r"""底栏（任务栏）图标统一方案

原理：
  运行中的窗口在任务栏显示的图标由三处决定，优先级从高到低：
    1. AppUserModelID 关联的注册表图标（HKCU\...\AppModelID 与 shell\...\AppUserModelID）
    2. 窗口自己设置的 WM_SETICON
    3. exe 内嵌图标

  对「未运行时」的固定项，改 .lnk 的 IconLocation 即可。
  对「已运行」的窗口，最可靠的做法是把 exe 内嵌图标整体替换（需要管理员+签名处理），
  或者在快捷方式里用 AUMID 重定向。

这里实现不破坏系统、可回滚的方案：
  A. 给所有相关 .lnk（桌面/开始菜单/任务栏固定）统一写 IconLocation
  B. 为 AppUserModelID 注册自定义图标
  C. 生成一份应用名→ICO 的映射表
"""
import sys
import io
import os
import json
import glob
import winreg
import subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ICO_DIR = r"C:\Users\Lenovo\zsIcons"
ROOT = r"D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme"
APPDATA = os.environ.get("APPDATA", "")
PROGRAMDATA = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
LOCAL = os.environ.get("LOCALAPPDATA", "")

# 应用名关键词 -> ICO 文件
MAP = {
    "chrome": "chrome.ico",
    "edge": "edge.ico",
    "vscode": "vscode.ico",
    "visual studio code": "vscode.ico",
    "cursor": "cursor.ico",
    "pycharm": "pycharm.ico",
    "clash": "clash.ico",
    "qqmusic": "qqmusic.ico",
    "qq音乐": "qqmusic.ico",
    "qq": "qq.ico",
    "腾讯qq": "qq.ico",
    "weixin": "weixin.ico",
    "微信": "weixin.ico",
    "wemeet": "wemeet.ico",
    "腾讯会议": "wemeet.ico",
    "feishu": "feishu.ico",
    "飞书": "feishu.ico",
    "deepseek": "deepseek.ico",
    "workbuddy": "workbuddy.ico",
    "todesk": "todesk.ico",
    "wps": "wps.ico",
    "jianying": "jianying.ico",
    "剪映": "jianying.ico",
    "baidu": "baidunet.ico",
    "百度网盘": "baidunet.ico",
    "bilibili": "bilibili.ico",
    "哔哩哔哩": "bilibili.ico",
    "huchuan": "huchuan.ico",
    "互传": "huchuan.ico",
    "mailmaster": "mailmaster.ico",
    "网易邮箱": "mailmaster.ico",
    "lenovo": "lenovopc.ico",
    "联想": "lenovopc.ico",
    "360": "se360.ico",
    "cherry": "cherry.ico",
    "luping": "luping.ico",
    "录屏": "luping.ico",
    "terminal": "wt.ico",
    "wt.ico": "wt.ico",
}


def pick_ico(name):
    low = name.lower()
    for k, v in MAP.items():
        if k in low:
            p = os.path.join(ICO_DIR, v)
            if os.path.exists(p):
                return p
    return None


def set_lnk_icon(lnk, ico):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
          "$s.IconLocation='%s,0';$s.Save()"
          % (lnk.replace("'", "''"), ico.replace("'", "''")))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    return r.returncode == 0


def main():
    # ---------- 1. 收集所有快捷方式 ----------
    dirs = [
        os.path.join(APPDATA, "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(PROGRAMDATA, "Microsoft", "Windows", "Start Menu", "Programs"),
        r"D:\Desktop",
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        r"C:\Users\Public\Desktop",
        os.path.join(APPDATA, "Microsoft", "Internet Explorer", "Quick Launch",
                     "User Pinned", "TaskBar"),
    ]
    lnks = []
    for d in dirs:
        if os.path.isdir(d):
            lnks += glob.glob(os.path.join(d, "**", "*.lnk"), recursive=True)
    print("发现快捷方式 %d 个" % len(lnks))

    # ---------- 2. 逐个匹配并写入 ----------
    changed = []
    for lnk in lnks:
        base = os.path.splitext(os.path.basename(lnk))[0]
        ico = pick_ico(base)
        if not ico:
            continue
        if set_lnk_icon(lnk, ico):
            changed.append((base, os.path.basename(ico), lnk))
    print("已更新 %d 个快捷方式" % len(changed))
    for b, i, p in changed:
        print("   %-28s -> %-16s %s" % (b[:28], i, os.path.dirname(p)[-30:]))

    # ---------- 3. AppUserModelID 图标 ----------
    print("\n=== AppUserModelID 注册 ===")
    aumid_map = {
        "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App": "wt.ico",
        "Microsoft.WindowsTerminal_8wekyb3d8bbwe!Windows.Terminal.VisualStudio": "wt.ico",
    }
    for aumid, icof in aumid_map.items():
        ico = os.path.join(ICO_DIR, icof)
        if not os.path.exists(ico):
            continue
        key = r"Software\Classes\AppUserModelId\%s" % aumid
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key, 0,
                                    winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "IconUri", 0, winreg.REG_SZ, ico)
            print("   ✓", aumid, "->", icof)
        except Exception as e:
            print("   ✗", aumid, e)

    json.dump([{"name": b, "ico": i, "lnk": p} for b, i, p in changed],
              open(os.path.join(ROOT, "_lnk_updated.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n-> _lnk_updated.json")


if __name__ == "__main__":
    main()
