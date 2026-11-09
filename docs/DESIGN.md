# 设计标准与算法细节

> 这份文档回答：一个「好看」的配色匹配，怎么变成可以计算、可以验证、可以复现的东西。

---

## 一、问题定义

给定：

- 24 个应用，每个有原图标 `icon_i`
- 候选照片池 `P = {p_1 ... p_n}`
- 每张照片 `p` 有：颜色分布、人脸框、清晰度

求一个分配 `f: 应用 → 照片`，使得

1. 每个应用的图标配色贴近原图标
2. 衣服颜色与图标主色和谐
3. 原图标的主色都能在照片里找到
4. 照片数量有限，不能重复使用
5. 人像要够大、够清晰

这是一个**带约束的指派问题**（assignment problem）。

---

## 二、颜色特征提取

### 2.1 HSV 分解

不用 OpenCV，纯 numpy 实现（避免为了一次转换引入重依赖）：

```python
mx = rgb.max(axis=2); mn = rgb.min(axis=2)
l  = (mx + mn) / 2                                   # HSL 亮度
dd = mx - mn + 1e-6
s  = np.where(mx == mn, 0,
              dd / np.maximum(1e-6, 1 - np.abs(2*l - 1)))   # 饱和度
r, g, b = rgb[...,0], rgb[...,1], rgb[...,2]
h = np.where(mx == r, ((g - b) / dd) % 6,
    np.where(mx == g, (b - r) / dd + 2,
                      (r - g) / dd + 4)) * 60          # 色相 0~360
```

### 2.2 11 维颜色直方图

把颜色分成 3 个消色 + 8 个色相段：

```
黑 black   l < 0.11
白 white   l > 0.87
灰 gray    s < 0.19 且 0.11 ≤ l ≤ 0.87
红 红 345~15    橙 15~40     黄 40~70     绿 70~165
青 165~200      蓝 200~265   紫 265~310   粉 310~345
```

每张照片得到 11 个占比，和为 1。

### 2.3 三个区域分别统计

| 区域 | 怎么取 | 用途 |
|---|---|---|
| **整图 `all`** | 全图 | 配色相似度 |
| **衣服 `cloth`** | 人脸框往下，脸宽 ×0.95 的宽度，高度从下巴到 +50% | 衣服和谐 |
| **背景 `bg`** | 外框 9% 环带 | 辅助判断 |

**关键**：衣服区的**分母必须用区域总像素数**，不是「满足条件的像素数」。

早期错误：

```python
n = ok.sum()              # ❌ 只为满足条件的像素计数
ev = {k: m.sum() / n}     # 置信度算出 280 / 2463 / 3969
```

正确：

```python
n = float(reg.shape[0] * reg.shape[1])   # ✅ 区域总像素
ev = {k: m.sum() / n}
```

---

## 三、三条标准怎么算

### 3.1 原图标配色（靶心）

原图标是扁平 logo，直接统计它的颜色分布：

```json
"微信":      {"green": 0.538, "white": 0.442, "gray": 0.020}
"QQ音乐":    {"yellow": 0.709, "green": 0.211, "cyan": 0.080}
"Cursor":    {"black": 0.647, "gray": 0.250, "white": 0.103}
"腾讯会议":  {"blue": 0.802, "white": 0.201}
```

### 3.2 标准一：配色相似度（权重 0.34）

余弦相似度：

```python
def cos(photo_hist, icon_pal):
    va = [photo_hist.get(k, 0) for k in HUES]
    vb = [icon_pal.get(k, 0)   for k in HUES]
    return dot(va, vb) / (norm(va) * norm(vb))
```

**为什么用余弦不用欧氏距离？** 因为照片的颜色分布天生更分散（有渐变、有阴影、
有高光），整体占比会比扁平 logo 低。余弦只关心「方向」，对整体缩放不敏感。

### 3.3 标准二：衣服和谐（权重 0.34）

对图标的每个主色，看衣服区满足了多少：

```python
def harmony(icon_pal, cloth):
    tot = sum(w for w in icon_pal.values() if w >= 0.03)
    if tot <= 0: return 0
    return sum(
        min(1.0, cloth.get(k, 0) / max(w, 1e-6)) * w
        for k, w in icon_pal.items() if w >= 0.03
    ) / tot
```

含义：图标主色占比 53.8% 的绿，如果衣服区绿色只占 20%，
那么这一项得分 `min(1, 0.20/0.538) = 0.37`。

### 3.4 标准三：颜色齐全（权重 0.20）

```python
def completeness(icon_pal, photo_hist):
    main = [k for k, w in icon_pal.items() if w >= 0.10] or [max(icon_pal, key=...)]
    hit  = sum(1 for k in main if photo_hist.get(k, 0) >= 0.095)
    return hit / len(main)
```

Chrome 图标是红黄绿蓝四色（各约 0.25），照片必须四个都能凑出来才算齐全。

### 3.5 辅助项

**脸够大**（0.07）：`min(1, farea / 0.10)`，脸占画面 10% 就满分

**清晰度**（0.05）：拉普拉斯方差 `min(1, sharp / 20)`

### 3.6 总分

```python
score = (0.34 * cos(photo_all, icon_pal)
       + 0.34 * harmony(icon_pal, photo_cloth)
       + 0.20 * completeness(icon_pal, photo_all)
       + 0.07 * min(1, farea / 0.10)
       + 0.05 * min(1, sharp / 20))
```

---

## 四、调色：为什么光挑照片不够

### 4.1 实测的失败

审计 v10 时发现：

| 应用 | 原图标 | 选中照片 | 余弦 |
|---|---|---|---|
| 腾讯会议 | 纯蓝方块 + 白 M | 偏暖色调 | **0.23** |
| PyCharm | 黑方块 PC + 彩色块 | 纯蓝 | **0.17** |

**根本原因**：真实照片的颜色分布**在数学上不可能**等于扁平 logo。
照片有渐变、有阴影、有肤色、有环境光。

### 4.2 极端案例：Chrome

Chrome 图标是红黄绿蓝四色，各约 0.25。

在 **4800 张素材里搜索「同时具备红≥0.055、黄≥0.055、绿≥0.055、蓝≥0.055」的照片**：

```
结果：0 张
```

现实里没有任何一张人物照会同时出现这四种纯色。

### 4.3 解法：向靶心调色

```python
def target_spec(icon_pal):
    # 目标色相 = 图标所有彩色的圆周加权均值（注意色相是环形的，不能直接算术平均）
    ang = [radians(HUE_CENTER[k]) for k in chrom]
    w   = [chrom[k] for k in chrom]
    thue = degrees(arctan2(sum(w*sin(ang)), sum(w*cos(ang)))) % 360

    # 目标饱和度 = 图标各色名义饱和度的加权均值
    tsat = sum(NOM_S[k] * v for k, v in chrom.items()) / sum(chrom.values())

    # 目标亮度：图标以黑为主就压暗，以白为主就提亮
    if icon_pal.get("black", 0) >= 0.30: tlum = 0.20
    elif icon_pal.get("white", 0) >= 0.35: tlum = 0.84
```

调色三步：

**① 色相旋转 + 饱和度缩放**

```python
dh = ((target_hue - source_hue + 180) % 360) - 180   # 最短路径旋转
dh *= strength * 0.92
h = np.where(chrom_mask, (h + dh) % 360, h)
s = np.where(chrom_mask, clip(s * scale, 0, 1), s)
```

**② 亮度伽马（黑白倾向）**

```python
ratio = target_lum / source_lum
g = clip(log2(ratio), -0.85, 0.85)
v = clip(v ** (1.0 / 2**g), 0, 1)
```

用伽马而不是线性缩放，是为了保留层次感（不会把暗部直接压死）。

**③ 缺失色补光**

图标有、照片完全没有的颜色（如 Chrome 的绿和黄），在**背景区域**补一层极淡的该色光：

```python
lack = [k for k in icon_colors if photo_k.get(k, 0) < 0.055]
# 只在距中心 > 0.85 半径的背景环形区补，强度 0.30
```

### 4.4 人头保护

第一版调色把**头发染成了绿色和紫色**。

修法：皮肤蒙版之外，再加一个人头椭圆保护：

```python
def head_protect(S, d, grow=1.55):
    rh = max(d["fh"] * S * grow * 0.72, S * 0.13)
    rw = max(d["fw"] * S * grow * 0.60, S * 0.11)
    cx = d["fx"] * S
    cy = d["fy"] * S - rh * 0.18     # 头部中心略高于人脸框中心
    return ((xx - cx)/rw)**2 + ((yy - cy)/rh)**2 <= 1.0

protect = skin_mask | head_protect(S, face_box)
```

### 4.5 每个应用的调色强度

不同应用需要的调色力度不一样。有的是「你选的这个版本，少动」，有的是「必须掰过来」。

做法是**搜索**：对每个应用，在 `{0, 0.22, 0.38, 0.52, 0.66, 0.80, 0.92, 1.0}` 里
试一遍，选让最终图标的配色覆盖 + 齐全度最高的强度。

```python
def objective(act, icon_pal, lum):
    pen = 0
    if lum < 62:  pen += (62 - lum) / 160      # 太暗扣分
    if lum > 205: pen += (lum - 205) / 260     # 过曝扣分
    return 0.62 * coverage(icon_pal, act) + 0.38 * completeness(icon_pal, act) - pen
```

---

## 五、全局分配，而不是逐项贪心

### 5.1 贪心的陷阱

如果对每个应用独立选它自己的最高分照片，会出现：

```
WPS Office      → station_20260530_05624_8.jpg   (score 0.98)
网易邮箱大师     → station_20260530_05624_8.jpg   (score 0.96)   ← 同一张！
```

因为红色系照片本来就少，两个红色应用的最高分是同一张。

### 5.2 解法：联合求解 + 交换优化

1. **锁定项优先**：用户明确指定沿用的，先占位
2. **稀缺优先**：候选最少的应用先挑（避免最后无解）
3. **交换优化**：反复扫描所有应用对 `(a, b)`，如果
   `score[a][photo_b] + score[b][photo_a] > score[a][photo_a] + score[b][photo_b]`
   就交换，直到不再改善

```python
for _ in range(40):
    moved = False
    for a in ORDER:
        for b in ORDER:
            if a >= b: continue
            before = score[a][chosen[a]] + score[b][chosen[b]]
            after  = score[a][chosen[b]] + score[b][chosen[a]]
            if after > before + 1e-4 and not conflicts(a, b):
                chosen[a], chosen[b] = chosen[b], chosen[a]
                moved = True
    if not moved: break
```

---

## 六、唯一性：三重约束

### 6.1 文件级

同一张图片文件不能出现两次。

### 6.2 感知哈希级

```python
def phash(im):
    g = np.asarray(im.convert("L").resize((8, 8)), dtype=np.float32)
    bits = (g > g.mean()).flatten()
    v = 0
    for b in bits: v = (v << 1) | int(b)
    return v

def dist(a, b):
    return bin(a ^ b).count("1")
```

阈值：

| 距离 | 含义 |
|---|---|
| 0 | 同一张图 |
| 1~2 | **同一视频的相邻帧** |
| 3~9 | 同一造型的不同角度 |
| ≥10 | 可视为不同画面 |

要求 **≥ 10**。

**为什么不能只看文件？** 实例：

```
互传   p0_0032_1.jpg
另一张 station_20260923_47687_5.jpg
pHash 距离 = 1
```

文件名完全不同，但视觉上是同一秒的两帧。

### 6.3 连拍系列级

从文件名提取系列号：

```python
def series_of(f):
    p = os.path.basename(f).split("_")
    if p[0] in ("station", "studio"):
        return "_".join(p[:3])      # station_20261025_76889
    if p[0] in ("p0", "fc", "sx", "nw", "f2"):
        return "_".join(p[:2])      # p0_0032
```

同一个系列全局只用一次。

---

## 七、构图质量硬门槛

颜色相似不能代表「可用」。以下条件不满足直接淘汰：

```python
# 人脸必须检到
d = detect_face(path)
if d is None: reject()

# 脸高占画面 ≥5.5%（排除远景小舞台）
if d["fh"] < 0.055: reject()

# 水平居中（排除边角人物）
if not (0.15 <= d["fx"] <= 0.85): reject()

# 垂直位置（排除画面下半部）
if not (0.10 <= d["fy"] <= 0.62): reject()

# 脸占画面面积
if farea < 0.035: reject()

# 带文字海报：横线 / 竖线过多
if hlines >= 2 or vlines >= 2: reject()

# 纯色条（截图、海报边框）
if topstd < 5.5 or botstd < 5.5: reject()

# 过暗
if bright < 28: reject()
```

---

## 八、渲染管线

### 8.1 人脸感知裁剪

目标：**脸高占图标 46%，脸放在 42% 高度的位置**。

```python
face_h_px = d["fh"] * H
crop = min(face_h_px / 0.46, min(W, H))    # 不超出原图
scale = S / crop
im2 = im.resize((W*scale, H*scale), LANCZOS)

# 把人脸放到水平中、垂直 42%
left = cx - S * 0.50
top  = cy - S * 0.42
```

脸小会自动放大到边界（受原始分辨率限制）。

### 8.2 形状

只保留两种：

```python
# 圆角方形：圆角半径 = 边长 26.8%
d.rounded_rectangle(box, radius=int(S * 0.268), fill=255)

# 圆形
d.ellipse(box, fill=255)
```

异形（拱形 / 鹅卵石 / 波浪）在 v7 后被弃用。

### 8.3 层次（从下到上）

1. 照片裁剪
2. 调色（保护人头）
3. 应用到蒙版
4. 外发光（图标主色，高斯模糊 3%）
5. 描边（图标主色，1% 宽）
6. 左上柔光（白色，透明度 11%）
7. 四角星点（随机 3 个）
8. **右下角应用角标**（96px 白色圆形 + 深色描边 + 投影）

### 8.4 角标尺寸

```python
BADGE = S * 0.360
PAD   = S * 0.022
# 角标内缩到 logo 的 68%
logo.thumbnail((int(BADGE * 0.68),) * 2)
```

---

## 九、可复现流程

```bash
# 1. 扫描素材，提取颜色 / 人脸 / 清晰度 / 构图
python src/pool_all.py           # → pool_all.json (2843 张)

# 2. YuNet 人脸检测
python src/pool_face.py          # → pool_face.json (1476 张)

# 3. 全局分配
python src/assign_global.py      # → assign.json

# 4. 搜索每个应用的最优调色强度
python src/search_grade.py       # → grade_strength.json

# 5. 渲染
python src/render_v11.py         # → PNG 256x256

# 6. PNG → ICO
python tools/png2ico.py themes/v11/icons themes/v11/icons

# 7. 校验 ICO
python tools/verify_ico.py
```

---

## 十、实测基准

| 指标 | v11 | Plan B | Plan C |
|---|---|---|---|
| 配色覆盖均值 | 0.708 | — | — |
| 衣服和谐均值 | 0.665 | — | — |
| 颜色齐全均值 | 0.708 | — | — |
| 平均亮度 | 117 | — | — |
| 指令通过 | **24/24** | 22/24 | 22/24 |
| 形状 IoU | **1.00** | 1.00 | 1.00 |
| 真重复 | **0** | 0 | 0 |

### 已知瓶颈

**绿色素材极度稀缺**。全部 2843 张里，绿衣只有 **11 张**，黄 15、青 26、粉 35。

这导致微信、360、WorkBuddy 三个需要绿色的应用，只能靠调色和背景补光，
配色覆盖分别只有 0.42 / 0.31 / 0.50。

**这是素材量的问题，不是算法的问题。** 如果有足够多的绿衣素材，这些指标会自然上升。
