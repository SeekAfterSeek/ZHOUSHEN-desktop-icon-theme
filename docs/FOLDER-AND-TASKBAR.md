# 图标统一方案（新建 / 系统位置 / 快捷方式）

## 已解决

### 1. 文件夹（含新建）—— 100% 生效

机制：**desktop.ini + 文件夹 ReadOnly 属性**

Windows 规则：文件夹必须带 `ReadOnly` 属性，shell 才会读它的 `desktop.ini`。
（只设 `System` 无效，这是最初一直失败的原因）

- 已有文件夹：`fix_all_folders.py` 批量写入
- **新建文件夹**：`folder_icon_watcher.py` 常驻后台，每 2 秒扫描一次，
  发现新目录立即写 desktop.ini 并设属性。已注册开机自启（`ZsFolderIcons`）
- 监控范围：桌面 / 文档 / 下载 / 图片 / 音乐 / 视频

### 2. 快捷方式（含应用）

`unify_all_icons.py`：扫描桌面、开始菜单（用户+全局）、任务栏固定项，
按应用名匹配 ICO 写入 `IconLocation`。已更新 26 个。

### 3. 用户文件夹 Lenovo

`C:\Users\Lenovo\desktop.ini` + ReadOnly，已验证生效。

---

## 限制（Windows 机制决定，非配置问题）

### 回收站 / 此电脑 / 控制面板 的桌面图标

图标定义在：

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CLSID\{GUID}\DefaultIcon
```

**写 HKLM 需要管理员权限**。当前只写入了 HKCU（优先级更低）。

如需生效，用管理员身份运行 `tools\SystemIcons-Elevated.ps1`。

### 运行中应用的底栏图标

任务栏上「已打开窗口」的图标由 **exe 内嵌资源** 或 **AppUserModelID** 决定，
改 `.lnk` 的 IconLocation 只影响「未运行时的固定项」。

统一这类图标需要修改 exe 资源（破坏签名，且每次应用更新后失效）。

可用的折中方案：

- 给应用注册 `HKCU\Software\Classes\AppUserModelId\<AUMID>` 的 `IconUri`
- 或让应用通过自定义快捷方式启动（重写 AUMID）

---

## 回滚

```powershell
# 移除文件夹监控
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name ZsFolderIcons
Get-Process pythonw | Where-Object { $_.CommandLine -like '*folder_icon_watcher*' } | Stop-Process

# 移除文件夹图标（去掉 ReadOnly 和 desktop.ini）
Get-ChildItem "D:\Desktop" -Directory | ForEach-Object {
    $_.Attributes = 'Directory'
    Remove-Item (Join-Path $_.FullName 'desktop.ini') -Force -ErrorAction SilentlyContinue
}
```
