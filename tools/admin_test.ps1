# 以管理员身份测试完整安装（含公共桌面）
# 用法：右键 → 以管理员身份运行 PowerShell，然后执行本脚本
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$installer = Join-Path $root 'installer\Install-Theme.ps1'

Write-Host "管理员身份: " -NoNewline
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host $isAdmin -ForegroundColor $(if ($isAdmin) { 'Green' } else { 'Red' })

if (-not $isAdmin) {
    Write-Host "此测试需要管理员权限" -ForegroundColor Yellow
    exit 1
}

& $installer -Action apply
