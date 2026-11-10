# 系统图标 + 全局文件夹图标（需要管理员）
#
# 为什么需要管理员：
#   此电脑 / 回收站 / 控制面板 / 全局文件夹 的图标定义在 HKLM 下，
#   普通权限写不进去。普通文件夹可以用 desktop.ini 单独指定（已生效）。
#
# 用法：右键这个文件 → 使用 PowerShell 运行
#       或者双击 SystemIcons.bat

$ErrorActionPreference = 'Continue'

# 自我提权
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "正在请求管理员权限..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","`"$PSCommandPath`""
    exit
}

$ico = "C:\Users\Lenovo\zsIcons"
Write-Host "已获得管理员权限" -ForegroundColor Green
Write-Host ""

# ---------- 1. 系统图标 ----------
$map = @{
    '此电脑'   = @{ GUID = '{20D04FE0-3AEA-1069-A2D8-08002B30309D}'; ICO = 'sys_pc.ico'   }
    '回收站'   = @{ GUID = '{645FF040-5081-101B-9F08-00AA002F954E}'; ICO = 'sys_bin.ico'  }
    '控制面板' = @{ GUID = '{26EE0668-A00A-44D7-9371-BEB064C98683}'; ICO = 'sys_panel.ico'}
    '用户文件' = @{ GUID = '{59031a47-3f72-44a7-89c5-5595fe6b30ee}'; ICO = 'sys_folder.ico'}
}

foreach ($name in $map.Keys) {
    $g = $map[$name].GUID
    $f = Join-Path $ico $map[$name].ICO
    $key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CLSID\$g\DefaultIcon"
    try {
        if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
        Set-ItemProperty -Path $key -Name '(default)' -Value "$f,0" -ErrorAction Stop
        if ($name -eq '回收站') {
            foreach ($v in 'Empty','Full') {
                New-ItemProperty -Path $key -Name $v -Value "$f,0" -PropertyType String -Force | Out-Null
            }
        }
        Write-Host "  ✓ $name" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $name : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ---------- 2. 全局文件夹图标 ----------
Write-Host ""
$folderIco = Join-Path $ico 'sys_folder.ico'
foreach ($k in @('HKLM:\SOFTWARE\Classes\Folder\DefaultIcon',
                 'HKLM:\SOFTWARE\Classes\Directory\DefaultIcon')) {
    try {
        if (-not (Test-Path $k)) { New-Item -Path $k -Force | Out-Null }
        Set-ItemProperty -Path $k -Name '(default)' -Value "$folderIco,0" -ErrorAction Stop
        Write-Host "  ✓ $k" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ $k : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# ---------- 3. 清理 HKLM 回收站键下可能残留 ----------
Write-Host ""
Write-Host "刷新图标缓存..." -ForegroundColor Yellow
ie4uinit.exe -show
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
$cd = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
Get-ChildItem $cd -Filter "*.db" -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe
Start-Sleep -Seconds 6

Write-Host ""
Write-Host "完成。若个别图标未刷新，按 F5 或注销重登。" -ForegroundColor Green
Read-Host "按回车键退出"
