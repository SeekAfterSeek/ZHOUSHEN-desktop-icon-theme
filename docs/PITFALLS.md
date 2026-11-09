# 踩坑全集：那些文档里不会写、只能撞出来的东西

> 每一条都是这个项目真实撞过的。现象 → 根因 → 解法 → 可复用的判据。

---

## 1. ICO 帧格式：桌面图标变成空白纸

**现象**

生成 ICO 后换成桌面图标，图标位置显示一张**空白纸**（白底 + 折角），不是我们的设计。
但用图片查看器打开这个 .ico 文件，看起来完全正常。

**排查过程**

一开始怀疑是图标缓存。清了 `iconcache_*.db`、重启 explorer、`ie4uinit.exe -show` —— 全都没用。

后来把 ICO 拆开看内部结构才发现问题：

```
frame 256x256   PNG
frame 128x128   PNG
frame  64x64    PNG
...
```

**根因**

Pillow 保存 ICO 时，**默认把每一帧存成 PNG 格式**（这是 ICO 规范允许的新写法）。
但 Windows 资源管理器的**桌面渲染器**在小区块（16/32/48px）下解析 PNG 帧会失败，
于是退回显示「未知文件」的默认图标 —— 那张空白纸。

而图片查看器走的是另一套解码路径，所以看起来正常。

**解法**

```python
im.save(dst, format="ICO",
        sizes=[(s, s) for s in (256,128,64,48,32,16)],
        bitmap_format="bmp")     # ← 关键
```

必须显式指定 `bitmap_format="bmp"`，让每一帧存成传统 DIB 位图。

**验证方法**

```python
b = open(ico_path, 'rb').read()
cnt = struct.unpack('<H', b[4:6])[0]
for i in range(cnt):
    off = 6 + i*16
    _,_,_,_,_,_,sz,ofs = struct.unpack('<BBBBHHII', b[off:off+16])
    is_png = b[ofs:ofs+8] == b'\x89PNG\r\n\x1a\n'
    assert not is_png, "PNG 帧会导致桌面白图标"
```

本仓库的 `tools/verify_ico.py` 就是干这个的。

**可复用判据**
> Windows ICO 交给 Explorer 桌面用，一律 `bitmap_format="bmp"`。

---

## 2. ICO 路径含中文或空格 → 同样的空白纸

**现象**

换成正确格式的 ICO 后，**一部分**图标正常，另一部分还是空白纸。

对比发现：正常的 ICO 路径是

```
C:\Users\Lenovo\zsIcons\weixin.ico
```

不正常的 ICO 路径是

```
D:\DSH\workspace\SMALL RESULT\zhoushen-icon-theme\icons\微信.ico
```

差别只有两个：**含空格**（`SMALL RESULT`）和**含中文**（`微信.ico`）。

**根因**

`IconLocation` 是 `"路径,索引"` 的字符串格式。当路径含空格或非 ASCII 字符时，
Explorer 的解析会出现歧义或编码问题，导致找不到资源。

**解法**

1. 所有 ICO 复制到一个**纯 ASCII、无空格**的目录：`%LOCALAPPDATA%\ZsIconTheme\icons\`
2. 文件名也全部用拼音/英文：`微信 → weixin.ico`、`哔哩哔哩 → bilibili.ico`

本仓库的 `installer/Install-Theme.ps1` 在应用前会自动把 ICO 复制到
`$env:LOCALAPPDATA\ZsIconTheme\icons`，就是为了绕开这个问题。

**可复用判据**
> 凡是要交给 Explorer 渲染的资源路径，只用 `[a-zA-Z0-9_\-\.]`，不要空格、不要中文。

---

## 3. PowerShell 脚本没有 BOM → 语法直接崩

**现象**

```
Unexpected token '360娴夊叏娴忚鍣?' in expression or statement.
Missing argument in parameter list.
The hash literal was incomplete.
```

报错里的中文全是乱码，而且报错位置莫名其妙（一行看起来完全正常的代码）。

**根因**

Windows PowerShell 5.1（`powershell.exe`，不是 `pwsh`）在没有 BOM 时，
会按**系统 ANSI 代码页**（中文 Windows 是 GBK）读取 .ps1 文件。

UTF-8 编码的中文字节被当成 GBK 解码 → 变成乱码 → 而且 GBK 解码可能产生
**看起来像引号或括号的字节序列** → 把字符串提前截断 → 语法崩。

**解法**

脚本保存为 **UTF-8 with BOM**（`EF BB BF` 开头）。

```python
BOM = b"\xef\xbb\xbf"
raw = open(path, "rb").read()
if not raw.startswith(BOM):
    open(path, "wb").write(BOM + raw)
```

本仓库的 `tools/add_bom.py` 就是干这个的。

**备注**

PowerShell 7（`pwsh`）默认按 UTF-8 读，没有这个问题。但为了兼容所有 Win10/11 用户，
脚本仍应加 BOM —— 因为大多数人双击运行走的是 5.1。

**可复用判据**
> 任何含非 ASCII 字符的 .ps1，一律存 UTF-8 with BOM。

---

## 4. 单元素数组退化：`$paths[0]` 取到的是首字母 'C'

**现象**

安装器扫描桌面快捷方式，明明找到了 `C:\Users\Public\Desktop\微信.lnk`，
但打印出来只有 `C`。

**根因**

PowerShell 函数返回值的行为：

```powershell
function Find-Thing {
    $found = @()
    $found += "C:\a\b.lnk"     # 只命中 1 个
    $found                      # ← 返回时被展开成单个 String，不是数组
}

$r = Find-Thing
$r[0]        # → 'C'（String 的索引拿的是字符！）
$r.Count     # → 1（String 也有 Count，所以不会报错）
```

`$r.Count` 不报错、`$r[0]` 不报错，只是结果是错的 —— 这种 bug 特别难发现。

**解法**

```powershell
function Find-Thing {
    $found = [System.Collections.Generic.List[string]]::new()
    # ...
    , $found.ToArray()      # ← 逗号一元运算符强制返回数组
}
```

或者在调用侧强制：

```powershell
$paths = @(Find-Thing)
```

**可复用判据**
> PowerShell 函数返回集合时，调用侧一律 `@()` 包裹，或返回侧用 `, $arr`。

---

## 5. 人脸检测：肤色阈值法把手肘当脸

**现象**

裁剪出来的图标，人物经常歪在边角，或者根本没拍到脸。

**排查**

把检测框画在原图上：

```
fw = 1.00   ← 检测框宽度 = 整个画面宽度
fh = 0.63
```

检测框横跨了整幅照片。

**根因**

用肤色阈值做检测：

```python
skin = (r > 95) & (g > 40) & (b > 20) & (r > g) & (r > b) & ...
```

舞台照里的**手臂、暖色灯光、木质舞台背景**全都落在这个范围内。
再用「峰值细胞 + 4 邻域扩张」找连通域，就会把大片肤色区域连成一个整体。

**解法**

换成 **YuNet** 深度模型（OpenCV `cv2.FaceDetectorYN`）：

```python
det = cv2.FaceDetectorYN.create("yunet.onnx", "", (w, h),
                                score_threshold=0.45, nms_threshold=0.3)
```

效果：24 张测试图 **24/24 全部检出**，置信度 0.85~0.95。

**踩过的额外坑**

`pip install opencv-python-headless` 默认装 **5.0**，这个版本**没有
`cv2.CascadeClassifier`**，也没有 `cv2.data.haarcascades`。需要降级：

```bash
pip install "opencv-python-headless<5"
```

**可复用判据**
> 人脸检测不要自己写阈值判断，用现成模型。舞台照、逆光、暖光全是陷阱。

---

## 6. 图案重复：不只是「同一张图」，还有「相邻帧」

**现象**

用户指出「腾讯会议和之前的图标图案重复了吧」。

**排查**

第一层：查文件是否重复。发现确实有 ——
v7 里 **WPS 和网易邮箱、百度网盘和 PyCharm、DSH 和剪映** 各自用了同一张照片。

第二层：修掉文件重复后，仍被说重复。改用感知哈希（pHash）查近似：

```
互传   p0_0032_1.jpg
另一个 station_20260923_47687_5.jpg
pHash 汉明距离 = 1
```

距离 1 意味着 **64 位里只有 1 位不同** —— 这几乎就是同一张图的相邻视频帧。

**根因**

素材来自视频抽帧和连拍，同一造型会产生几十张几乎一样的照片。
文件名看起来完全不同，但视觉上是同一张。

**解法**

三重约束：

1. 文件不重复
2. **pHash 汉明距离 ≥ 10**（距离 1~2 是相邻帧，3~9 是同一造型的不同角度）
3. **连拍系列全局只用一次** —— 从文件名提取系列号：
   `station_20261025_76889_7.jpg` → 系列 `station_20261025_76889`

**可复用判据**
> 用照片做视觉素材时，光比对文件哈希不够，必须上 pHash + 系列号双约束。

---

## 7. 素材库里混着「不是目标人物」的人

**现象**

Plan B 的 VS Code 位出现一位老先生，Plan C 的 WPS 位出现一位穿正装的陌生人。

**尝试过但失败的方案**

| 方案 | 思路 | 结果 |
|---|---|---|
| LBP 直方图 + 单锚点 | 与人脸锚点算相似度 | ❌ 陌生人 0.870，**高于中位数** |
| 10 锚点投票 | 有多少锚点认为像 | ❌ 陌生人 10/10 全票 |
| 加权色调一致性 | 发色 + 肤色调 | ❌ 区分度不足 |

**根因**

LBP / HOG 这类手工特征描述的是「纹理和梯度方向」，
对**同族、同性别、同年龄段**的面孔区分度本来就不够。
这是方法的天花板，不是参数没调好。

**最终解法**

**人工审核 278 张候选**。生成 7 张拼版大图，逐张肉眼过，圈出 24 张坏图：

- 非周深 8 张（老先生、戴眼镜男士、吉他手、红衣普通人…）
- 带文字海报 8 张
- 空舞台 / 远景 6 张
- 拼图 / 背景板 2 张

黑名单存进 `bad_by_review.json`，求解器直接排除。

**可复用判据**
> 当「是不是同一个人」直接影响成品质量时，手工特征不可靠。
> 要么上真正的人脸识别模型（ArcFace 等），要么人工兜底。**不要假装算法能解决。**

---

## 8. 自动评分完全不看构图

**现象**

Plan B/C 的「全能录屏」位选了**空舞台**，「WPS」位选了**生日蛋糕场景**。

**根因**

评分公式只有颜色维度：

```
score = 0.34×配色余弦 + 0.34×衣服和谐 + 0.20×颜色齐全 + 0.07×脸 + 0.05×清晰度
```

空舞台的颜色分布可能恰好匹配，而它压根没有人。

**解法**

加构图质量筛，作为**硬门槛**而不是加分项：

```python
r["fh2"] >= 0.055              # 脸高占画面 ≥5.5%，排除远景小人
and 0.15 <= r["fx2"] <= 0.85   # 水平位置，排除边角人物
and 0.10 <= r["fy2"] <= 0.62   # 垂直位置，排除下半部
and r["farea"] >= 0.035        # 脸占画面面积
and not (r["hlines"] >= 2)     # 排除带文字海报（横线检测）
and not (r["vlines"] >= 2)     # 排除带文字海报（竖线检测）
and r["topstd"] >= 5.5         # 排除纯色条（截图、海报边框）
```

**可复用判据**
> 颜色相似度不能代表「可用」。构图、清晰度、是否含人物，必须是硬门槛。

---

## 9. 调色把头发的颜色也改了

**现象**

第一版调色上线后，Chrome、Cherry、互传、PyCharm、腾讯会议的图标里，
**头发变成了绿色或紫色**。

**根因**

调色只保护了「皮肤」：

```python
skin = (r > 0.34) & (g > 0.14) & ... & (r > g) & (r > b)
```

头发是黑色的，不满足肤色条件，所以被当成背景一起做了色相旋转。

**解法**

除了皮肤蒙版，再加一个**人头保护椭圆**：

```python
def head_protect(S, d, grow=1.55):
    """以人脸框为中心、放大 grow 倍的椭圆 = 整个人头（含头发）"""
    rh = max(d["fh"] * S * grow * 0.72, S * 0.13)
    rw = max(d["fw"] * S * grow * 0.60, S * 0.11)
    cx = d["fx"] * S
    cy = d["fy"] * S - rh * 0.18      # 头部中心略高于人脸框
    return ((xx - cx) / rw)**2 + ((yy - cy) / rh)**2 <= 1.0

protect = skin_mask | head_protect(...)
```

**可复用判据**
> 做局部调色时，「皮肤」不等于「人」。头发、五官、脖子都要保护。

---

## 10. UAC 提权：脚本路径含空格导致静默失败

**现象**

要修改公共桌面的快捷方式，需要管理员权限。用 `Start-Process powershell -Verb RunAs`
启动提权脚本，返回码 `-196608`，而且**完全没有日志输出**。

**根因**

命令行是：

```powershell
Start-Process powershell -Verb RunAs -ArgumentList "-File D:\DSH\workspace\SMALL RESULT\apply_public.ps1"
```

`SMALL RESULT` 里有空格，`-File` 只拿到了 `D:\DSH\workspace\SMALL`，
剩下部分被当成额外参数，PowerShell 启动后立刻报错退出。
因为提权窗口一闪而过，看不到错误。

**解法**

```powershell
$argList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
Start-Process powershell -Verb RunAs -ArgumentList $argList
```

**可复用判据**
> `Start-Process -ArgumentList` 传路径，一律用反引号转义的双引号包裹。

---

## 11. 微博 API 翻页返回 -100

**现象**

```
GET m.weibo.cn/api/container/getIndex?type=uid&value=XXX&containerid=107603XXX&page=2
→ {"ok": -100}
```

第 1 页正常，第 2 页永远失败。试过 `max_id`、`since_id`，全部被忽略。

**根因**

**未登录**。`/api/config` 返回 `login: false` 时，翻页接口直接拒绝。

**解法**

先在浏览器里正常登录，然后从浏览器 Profile 里读 cookie。
登录后 page 2 立即返回 10 条。

**可复用判据**
> 移动端 API 返回 `ok: -100` 先查登录态，不要先怀疑参数。

---

## 12. Edge 的 `--remote-debugging-port` 被忽略

**现象**

用 `msedge.exe --remote-debugging-port=9222` 启动，DevTools 端口连不上。

**根因**

现代 Edge 在**默认 Profile** 下会忽略这个参数（安全策略）。

**解法**

必须用一个独立的 user-data-dir：

```bash
msedge.exe --remote-debugging-port=9222 \
           --user-data-dir=C:\Users\X\edge-debug-profile \
           --profile-directory=debug
```

**可复用判据**
> Chromium 系浏览器开调试端口，必须配独立 `--user-data-dir`。

---

## 13. 小红书：不要跟 DOM 滚动较劲

**现象**

在小红书个人主页，`scrollHeight == innerHeight == 776`，页面高度永远不增长，
只拿到 30 个笔记链接。反复滚动无效。

**根因**

页面用了虚拟滚动 + 懒加载，DOM 里永远只保留可见范围内的节点。
滚动条高度不变，是因为容器内部滚动而不是文档滚动。

**解法**

**直接读 Vue 的响应式 store**，不碰 DOM：

```javascript
window.__INITIAL_STATE__.user.notes._rawValue
```

一次拿到完整列表：某个账号 240 条，另一个 996 条。

封面图地址：

```javascript
noteCard.cover.infoList[0].url
```

**可复用判据**
> 现代 SPA 做数据抓取，优先找 `__INITIAL_STATE__` / `__NUXT__` / `__NEXT_DATA__`，
> 而不是模拟滚动。

---

## 14. 一次失败的重构：重扫全池导致脚本假死

**现象**

`refine_v8.py` / `refine_v10.py` 每次运行都要重新扫描整个候选池（1021 张图），
运行 10 分钟以上没有任何输出，也没有生成文件。看起来像卡死了。

**根因**

把「分析」和「渲染」耦合在一个脚本里。每次微调参数都要重跑全量分析。

**解法**

拆成两步：

1. `assign_*.py` — 分析 + 分配，输出 `assign.json`
2. `render_*.py` — **只读 assign.json 渲染**，不碰素材池

拆分后渲染 24 张图只需 **1 秒**，迭代速度提升两个数量级。

**可复用判据**
> 分析和渲染必须解耦。中间结果落盘（JSON），后续步骤只读它。

---

## 汇总：一页速查

| 症状 | 首查 |
|---|---|
| 桌面图标空白纸 | ICO 是否 `bitmap_format="bmp"`；路径是否纯 ASCII 无空格 |
| .ps1 报莫名其妙的语法错 | 是否 UTF-8 with BOM |
| `$arr[0]` 拿到单个字符 | 单元素数组退化，用 `@()` 或 `, $arr` |
| UAC 提权脚本无输出 | 路径含空格，`-ArgumentList` 未加引号 |
| 人物裁到边角 | 人脸检测不可靠，换 YuNet |
| 图标里出现陌生面孔 | 素材库混入他人，需要人工兜底 |
| 两个图标"看起来一样" | pHash 距离 + 连拍系列号 |
| 选中了空舞台/海报 | 缺构图硬门槛 |
| 头发被染色 | 保护椭圆没加 |
| 滚动抓不到数据 | 读 `__INITIAL_STATE__` |
