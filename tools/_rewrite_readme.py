# -*- coding: utf-8 -*-
r"""重写 README 的安装 / 使用 / 授权 / 图片来源四块"""
import sys, io, os
sys.stdout = io.TextIOWrapper(open(sys.stdout.fileno(), "wb", closefd=False),
                              encoding="utf-8", errors="replace")

P = r"D:\DSH\workspace\SMALL RESULT\zs-icon-theme-release\README.md"
t = open(P, encoding="utf-8").read()

OLD_QUICK = """## 一分钟上手

```powershell
# 1. 克隆（或点右上角 Code → Download ZIP）
git clone https://github.com/SeekAfterSeek/zs-desktop-icon-theme.git
cd zs-desktop-icon-theme

# 2. 先看看会改哪些（不修改任何东西）
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action list

# 3. 应用主题
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action apply

# 4. 不满意？一键回退
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action rollback
```
"""

NEW_INSTALL = """## 安装

### 系统要求

- Windows 10 / 11（64 位）
- PowerShell 5.1 及以上（系统自带，不用另装）
- 不需要装 Python、不需要管理员权限（除非你的快捷方式在公共桌面）

### 方式一：下载 ZIP（不熟悉命令行的用这个）

1. 页面右上角 **Code → Download ZIP**
2. 解压到**纯英文、无空格**的路径，例如 `D:\\zs-icon-theme`

   > 这一点是必须的：ICO 放在含中文或空格的路径下，桌面会把它渲染成一张白纸。
   > 踩坑记录见 [docs/PITFALLS.md](docs/PITFALLS.md) 第 2 条。脚本自己也会把图标
   > 复制到 `%LOCALAPPDATA%\\ZsIconTheme\\icons`（纯 ASCII）再引用，但你解压的路径仍建议保持干净。

3. 在解压出来的文件夹里，地址栏输入 `powershell` 回车，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action apply
```

或者右键 `installer\\Install-Theme.ps1` → **使用 PowerShell 运行**。
如果提示「禁止运行脚本」，就是上面那条带 `-ExecutionPolicy Bypass` 的命令。

### 方式二：git clone

```powershell
git clone https://github.com/SeekAfterSeek/zs-desktop-icon-theme.git
cd zs-desktop-icon-theme
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action apply
```

### 装完没变化？

Windows 会缓存 `.lnk` 的图标。脚本已经做了 `SHChangeNotify` 通知，多数情况立刻就变。
如果还是旧图，按顺序试：

1. 桌面按 `F5`
2. 运行仓库里的 `src\\versions\\v13\\force_refresh_icons.py`（会清 iconcache 并重启 explorer）
3. 注销再登录

## 使用

### 四个动作

| 命令参数 | 作用 | 会改系统吗 |
|---|---|---|
| `-Action list` | 列出本机检测到的应用、命中几个 / 共几个 | 不会 |
| `-Action preview` | 告诉你「将会改哪些快捷方式」 | 不会 |
| `-Action apply` | 应用主题（默认最新 **v13**） | 会改桌面快捷方式的图标 |
| `-Action rollback` | 还原到安装前的图标 | 会改回去 |

```powershell
# 先看一眼
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action list

# 应用最新版
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action apply

# 换指定版本
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Theme v12 -Action apply

# 一键还原
powershell -ExecutionPolicy Bypass -File installer\\Install-Theme.ps1 -Action rollback
```

可选主题：`v13`（默认）、`v12`、`v11`、`planB`、`planC`。

### 脚本到底做了什么

1. 把 `themes\\<版本>\\icons\\*.ico` 复制到 `%LOCALAPPDATA%\\ZsIconTheme\\icons\\`（纯 ASCII 路径）
2. 改写桌面 `.lnk` 快捷方式的 **IconLocation** 指向这些 ICO
3. 首次运行前，把每个快捷方式**原来的** IconLocation 记到
   `%LOCALAPPDATA%\\ZsIconTheme\\original-shortcuts.json`
4. 用 `SHChangeNotify` 通知外壳刷新（**不重启 explorer**，不打断你手上的事）

**它不会**：改壁纸、改系统主题、改任务栏、改窗口颜色、改任何 exe、注入进程、装驱动、写开机项。

### 只想换其中几个图标？

不改脚本也行，直接改快捷方式属性：右键 `.lnk` → 属性 → 更改图标 → 选
`themes\\v13\\icons\\<应用名>.ico`。这个改动同样可以用 `-Action rollback` 撤销
（前提是那次 `apply` 记录过它的原值）。

### 关于系统项

主题里另外还有 5 个系统项图标（用户文件夹、此电脑、回收站、控制面板、文件夹），
它们不是 `.lnk`，改的是注册表 `CLSID\\...\\DefaultIcon` 或文件夹的 `desktop.ini`，
**安装脚本目前不处理这 5 项**，需要手动：

| 项 | 改法 |
|---|---|
| 此电脑 / 回收站 / 控制面板 / 用户文件夹 | `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CLSID\\{CLSID}\\DefaultIcon` 的默认值 |
| 普通文件夹 | 文件夹里放 `desktop.ini`，写 `IconResource=<ico 路径>,0` |

改动前记得先导出对应注册表键备份。这部分我会在后续版本做成 `-IncludeSystemItems` 开关。
"""

if OLD_QUICK not in t:
    print("!! 找不到「一分钟上手」块，未改动安装/使用")
else:
    t = t.replace(OLD_QUICK, NEW_INSTALL)
    print("安装 / 使用 已写入")

TAIL_OLD = t[t.index("## 版权与免责"):]
TAIL_NEW = """## 授权协议

**开源，但禁止商用。**

| 部分 | 许可 |
|---|---|
| 代码（`installer/`、`tools/`、`src/`） | MIT —— 随便用、随便改，保留版权声明即可 |
| 图标成品、展示图、仓库内所有图像 | **CC BY-NC 4.0** —— 可转载、可修改、可自用，**不得用于任何商业用途** |

「商业用途」包括但不限于：售卖图标包、收费主题、放进付费装机盘、用于商家广告/宣传物料、
印在商品上、作为付费课程/教程的素材。

同时请遵守以下三条：

1. **本项目是非官方同人项目**，与周深本人、其工作室、以及腾讯、字节、阿里等应用厂商**均无关系**；
2. 图标里的第三方应用标志（微信、QQ、Chrome、哔哩哔哩……）版权归各自公司，这里只是做视觉搭配；
3. 人像照片的版权属于**原摄影者与发布账号**（见下一节），本项目只做裁剪、调色、加角标，
   **不主张**对照片本身的任何权利。

**如权利人认为有不妥，开一个 issue，我会立刻下架相关图像。**

---

## 图片来源

本仓库**不分发任何原始照片**，只分发渲染后的图标成品。所有素材抓取自公开账号，
抓取时间：**2026 年 5 月 — 11 月**。

### 主要来源账号

| 平台 | 账号 | 地址 | 本主题采用 |
|---|---|---|---|
| 微博 | **周深工作室** | <https://weibo.com/u/7478855230>（UID `7478855230`） | 5 个图标 |
| 微博 | **ForCharlie丨周深图文站** | <https://weibo.com/u/6987697229>（UID `6987697229`） | 11 个图标 |
| 小红书 | **ForCharlie｜周深图文站** | <https://www.xiaohongshu.com/user/profile/5fc1f667000000000101d007> | 6 个图标 |
| 小红书 | 周深粉丝后援小分队 | 小红书站内搜索该账号名 | 其中 1 个（全能录屏助手） |
| 小红书 | 工作室账号（`studio_xhs_src`） | 小红书站内搜索「周深工作室」 | 其中 1 个（百度网盘） |
| 微博 | 早期整理（`c929b_*`，2023 年前的历史图集） | 见文件名，具体单条未记录 | 1 个（腾讯会议） |

### 逐个图标的出处

| 图标 | 采用的照片 | 来源账号 |
|---|---|---|
| 微信 | `studio_20261025_76889_5` | 周深工作室（微博） |
| QQ音乐 | `station_20260510_59173_0` | ForCharlie丨周深图文站（微博） |
| 哔哩哔哩 | `station_20260524_50364_0` | ForCharlie丨周深图文站（微博） |
| Google Chrome | `station_20260822_99475_1` | ForCharlie丨周深图文站（微博） |
| 个人 - Edge | `fc_0979` | ForCharlie｜周深图文站（小红书） |
| 360 安全浏览器 | `studio_20260903_94616_0` | 周深工作室（微博） |
| Visual Studio Code | `fc_1277` | ForCharlie｜周深图文站（小红书） |
| Cursor | `station_0030` | ForCharlie丨周深图文站（微博） |
| DeepSeek Harness | `station_20260912_43162_3` | ForCharlie丨周深图文站（微博） |
| Cherry Studio | `studio_20260926_93785_7` | 周深工作室（微博） |
| WorkBuddy | `station_0007` | ForCharlie丨周深图文站（微博） |
| WPS Office | `studio_20261004_85716_6` | 周深工作室（微博） |
| 全能录屏助手 | `nw_0047` | 周深粉丝后援小分队（小红书） |
| 剪映专业版 | `fc_0475` | ForCharlie｜周深图文站（小红书） |
| 百度网盘 | `sx_0505` | 工作室账号（小红书） |
| 飞书 | `station_20260628_79992_0` | ForCharlie丨周深图文站（微博） |
| Clash Verge | `f2_0169` | ForCharlie（小红书，补充抓取） |
| PyCharm | `studio_20261026_32066_5` | 周深工作室（微博） |
| ToDesk | `station_20260927_91932_0` | ForCharlie丨周深图文站（微博） |
| 互传 | `station_20260925_18697_3` | ForCharlie丨周深图文站（微博） |
| 网易邮箱大师 | `station_20260530_05624_8` | ForCharlie丨周深图文站（微博） |
| 联想电脑管家 | `fc_0995` | ForCharlie｜周深图文站（小红书） |
| 腾讯 QQ | `station_20261017_31971_5` | ForCharlie丨周深图文站（微博） |
| 腾讯会议 | `c929b_90b313ea59` | 微博早期图集 |
| Lenovo 用户文件夹 | `f2_0015`（透明雨衣） | ForCharlie（小红书，补充抓取） |
| 此电脑 / 回收站 / 控制面板 / 文件夹 | 同上两个微博账号的光图池 | 周深工作室 / ForCharlie丨周深图文站 |

> 文件名里的 `studio_` 前缀对应周深工作室，`station_` 对应图文站，
> `fc_` / `f2_` / `nw_` / `sx_` 对应小红书，`c929b_` 是早期微博图。

---

## License

- 代码：**MIT**
- 图标与图片：**CC BY-NC 4.0（禁止商用）**

完整说明见上面的「授权协议」。商用授权不在本仓库范围内，也不提供。
"""

if "## 版权与免责" in t:
    t = t.replace(TAIL_OLD, TAIL_NEW)
    print("授权 / 图片来源 已写入")

open(P, "w", encoding="utf-8").write(t)
print("README 长度:", len(t))
