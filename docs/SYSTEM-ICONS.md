# 系统项图标指南（文件夹 / 此电脑 / 回收站 / 控制面板 / 用户文件夹）

> **2026-11-26 更新**：新增「方案 A」—— 基于实机验证的 Shell Icons 全局方案，
> 比旧的 desktop.ini + 常驻 watcher 方案更简单、无后台进程、可一键回退。
> 实机验证环境：Win10 家庭中文版 19045，全程零删除、零数据损失。
> 本文面向两类读者：想自己动手的用户，以及替用户执行的 AI 助手。

---

## 0. 安全红线（人和 AI 都必须遵守）

以下规则来自一次真实事故：某 AI 助手用下划线命名临时测试文件夹，清理时用脚本
按「所有含下划线的文件夹」通配删除，导致用户工作区被清空、数据不可恢复。

1. **全程零删除**。不写任何针对文件/文件夹的删除命令（`Remove-Item -Recurse` /
   `rm -rf` / `del /s`）。测试产物「只建不删」，留在原地交用户处置。
2. **先备份，后修改**。所有将被覆盖的注册表值，修改前先导出（JSON 清单 + .reg 双份）。
3. **临时目录用纯字母数字命名**（如 `iconProbe1`），绝不用下划线等易与用户数据重叠的模式。
4. **权限不够不绕过**。HKLM 需要管理员：生成 .reg 文件交用户双击导入，不要绕 UAC。
5. **不硬编码用户路径**。图标一律复制到 `%LOCALAPPDATA%` 下的纯 ASCII 路径再引用
   （旧版提权脚本硬编码 `C:\Users\<作者名>` 导致其他用户必失败，已废弃）。
6. **只动目标值**。回退只移除自己添加的注册表值，不删键、不碰其他值、不碰用户文件。
7. **改完必核对**。修改前后对账：注册表值、文件清单、运行中的进程。

---

## 1. 桌面系统项的真实身份

桌面上的这几项不是 `.lnk` 快捷方式，改 IconLocation 对它们无效：

| 桌面项 | 真实身份 | 图标定义位置 |
|---|---|---|
| 此电脑 | 命名空间 `{20D04FE0-3AEA-1069-A2D8-08002B30309D}` | `Explorer\CLSID\...\DefaultIcon` |
| 回收站 | `{645FF040-5081-101B-9F08-00AA002F954E}`（含 Empty/Full 两态） | 同上 |
| 控制面板 | `{21EC2020-3AEA-1069-A2DD-08002B30309D}`（分类视图）/ `{26EE0668-A00A-44D7-9371-BEB064C98683}`（全部项） | 同上 |
| 用户文件夹 | `{59031A47-3F72-44A7-89C5-5595FE6B30EE}` | 同上 |
| 普通文件夹 | 文件系统目录 | **`Shell Icons` 3/4 全局定义** 或逐目录 `desktop.ini` |

---

## 2. 原理：文件夹图标的两套机制（为什么「改了却不生效」）

| 机制 | 作用范围 | 定义位置 |
|---|---|---|
| A. `desktop.ini` 的 `IconResource`（需配合 ReadOnly 属性） | 仅这一个文件夹 | 文件夹内部 |
| B. 系统默认定义 `Shell Icons` 3/4（3=关闭态，4=打开态） | 全系统所有文件夹 | 注册表 HKLM + HKCU |

每一条都实测过的关键事实：

- 已有文件夹显示新图标 ≠ 系统定义已改——它们可能只是各自贴了 desktop.ini（机制 A）。
- **新建文件夹不会自动生成 desktop.ini**，走机制 B；B 没改 → 回落 `shell32.dll,3` 旧图标。
- 只写 HKCU 的 `Shell Icons` 在部分场景不生效，**必须配 HKLM**。
- 所以「让以后任何地方新建文件夹都用主题图标」的正解是**机制 B（HKCU + HKLM 都写）**，
  不需要常驻 watcher 逐个补写。

**判据**：只影响单个文件夹 → 用机制 A；要让「以后新建的」生效 → 必须改机制 B。

---

## 3. 方案 A（v13.1 推荐）：一键脚本

```powershell
# 只读预览当前注册表状态
powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action list

# 应用：备份 -> 写 HKCU（免管理员）-> 生成 HKLM .reg 供管理员导入
powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action apply

# 一键回退（HKCU 直接还原；HKLM 生成 rollback_hklm.reg 供管理员导入）
powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action rollback
```

脚本行为边界：

- **会做**：复制 ICO 到图标工作目录（纯 ASCII）→ ICO 头校验 → 备份 JSON 清单 →
  写 HKCU 的 `Shell Icons` 3/4 与 5 个 CLSID `DefaultIcon`（含回收站 Empty/Full 两态）→
  生成 HKLM 的 apply / rollback .reg（UTF-16 LE）→ 打印两级缓存刷新指引。
- **不会做**：删除任何文件、改壁纸/主题/exe、写开机项、常驻后台、联网、自我提权。
- **不硬编码任何用户路径**。
- 用户名含中文导致 `%LOCALAPPDATA%` 路径含中文时，用 `-DestDir C:\ZsIcons`
  把图标工作目录指到纯 ASCII 路径（见 PITFALLS 第 2 条）。

---

## 4. 方案 A 手动全流程（实机验证记录）

**步骤 1 · 备份**（把相关键导出为 .reg 文本；「键不存在」本身也是备份信息）

- `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons`
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons`
- `HKCU / HKLM\...\Explorer\CLSID\{GUID}\DefaultIcon`（见第 1 节表格）

**步骤 2 · 写用户级（HKCU，免管理员）**

```powershell
New-Item -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons' -Force
New-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons' `
  -Name '3' -Value 'C:\图标路径\folder.ico,0' -PropertyType String -Force
# 第 4 值（打开态）同理
```

**步骤 3 · 写系统级（HKLM，需管理员）**

生成下面的 .reg 并**保存为 UTF-16 LE**（PowerShell 用 `Out-File -Encoding Unicode`；
UTF-8 保存会导致导入乱码，见 PITFALLS 第 16 条），双击导入，UAC 点「是」：

```
Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons]
"3"="C:\\图标路径\\folder.ico,0"
"4"="C:\\图标路径\\folder.ico,0"
```

注意 .reg 里路径的反斜杠要写成 `\\`。

**步骤 4 · 刷新缓存**（两级，见第 6 节）

**步骤 5 · 验证**：在任意位置右键新建一个文件夹，看图标是否为主题图标。

**步骤 6 · 留痕**：把导入用的 .reg 和备份放同一目录，就是这次修改的完整记录。

---

## 5. 方案 B（旧方案，保留说明）：desktop.ini + ReadOnly + watcher

机制：文件夹必须带 `ReadOnly` 属性，shell 才会读它的 `desktop.ini`（只设 `System` 无效）。

- 适合：**单个文件夹**的精细控制（比如只想改某个特定文件夹的图标）。
- 全局统一（含新建文件夹）**不再推荐 watcher 方案**：`folder_icon_watcher.py`
  需要常驻后台 + 开机自启，而方案 A 一条注册表定义即可全覆盖。
- 若你已装过旧方案的 `ZsFolderIcons` 开机项并想退役（确认方案 A 生效后）：
  任务管理器 → 启动应用 → 禁用 `ZsFolderIcons`；watcher 进程结束方式为
  任务管理器中结束对应 `pythonw` 进程。**不要用脚本批量删 desktop.ini。**

---

## 6. 图标缓存：两级刷新

改完注册表看不到变化 ≠ 没改成功。缓存有两级：

| 级别 | 覆盖手段 |
|---|---|
| 1 · 外壳数据库 | `ie4uinit.exe -show`；`SHChangeNotify(0x08000000, 0, 0, 0)` |
| 2 · Explorer 进程内存 | **重启 explorer**：`taskkill /f /im explorer.exe` 后运行 `explorer.exe`；或任务管理器 → 右键「Windows 资源管理器」→ 重新启动 |

重启 explorer 时桌面/任务栏闪两秒；正在运行的独立程序（聊天、下载、AI 助手等）
**不受影响**。不需要删除 `iconcache_*.db` 文件——重启进程即可。

**故障排查表**

| 症状 | 原因 | 处理 |
|---|---|---|
| 图标变成空白纸 | ICO 帧是 PNG / 路径含中文或空格 | PITFALLS 第 1、2 条 |
| 注册表读回来是对的，显示仍旧图标 | 缓存两级没刷透 | `ie4uinit -show` → 重启 explorer |
| 已有文件夹变了、新建的还是旧的 | 只改了机制 A 或只写了 HKCU | 补 HKLM `Shell Icons` 3/4 |
| 双击 .reg 没反应 / 导入后乱码 | 编码不是 UTF-16 LE | `Out-File -Encoding Unicode` 重新生成 |
| 图标路径含中文（用户名是中文） | LOCALAPPDATA 跟用户名走 | `-DestDir` 指定纯 ASCII 目录 |
| 想撤销全部改动 | — | 脚本 `-Action rollback`，按其输出操作 |

---

## 7. 给 AI 助手的执行守则

替用户执行本任务时，按四阶段推进，**每阶段之间向用户汇报**：

1. **只读调研**：读 HKCR/HKLM/HKCU 相关键现状、定位图标文件、检查是否有会覆盖
   设置的遗留脚本/计划任务（如开机自启的 watcher）。
2. **安全底座**：建隔离测试区（纯字母数字命名）→ 导出全部相关键为 .reg →
   图标文件哈希快照 → 书面「不改清单」。
3. **修改**：能用户级完成的写 HKCU；HKLM 生成 .reg 交用户导入（不绕 UAC、不自我提权）。
4. **验证交付**：测试区新建文件夹验证 → 请用户肉眼终验（AI 看不到屏幕渲染）→
   对账资产（进程、文件清单、哈希比对）。

不同机器上的环境差异（AI 会遇到）：

- `reg.exe` 可能被企业安全策略拦截：改用 PowerShell 原生 `Get-Item /
  Get-ItemProperty` 读值，自己拼接 .reg 文本。
- 提权可能被策略禁止（`Start-Process -Verb RunAs` 报错）：不绕过，走 .reg 交给用户。
- 从聊天窗口复制的路径可能带不可见字符，资源管理器会报「找不到路径」：
  用 `explorer.exe "<路径>"` 代开窗口验证。
- 修改公共桌面的快捷方式需要管理员（见 README「关于管理员权限」），系统项注册表
  同理：能写 HKCU 就不碰 HKLM，必须 HKLM 时走 .reg 导入。

---

## 8. 配色依据（沿用 v11 加权规则）

系统项图标按主仓库的三标准加权规则匹配照片：`0.34×全图配色 + 0.34×衣服配色 +
0.20×颜色齐全度 + 0.07×脸像素 + 0.05×锐度`。逐图标选用照片见
`themes/v13/system-icons/manifest.json`。

---

**验证记录**：2026-11-26，Win10 家庭中文版 19045。流程：只读调研 → 备份 →
HKCU 写入 → 用户导入 HKLM .reg（UTF-16 LE）→ `ie4uinit -show` → 重启 explorer →
桌面与新建文件夹全部生效；全程零删除、零数据损失。
