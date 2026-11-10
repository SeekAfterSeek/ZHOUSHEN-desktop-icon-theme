# 一键把本地的迭代历史 + 版本 tag 推送到 GitHub
#
# 什么时候用：
#   本机到 GitHub 的 TLS 握手恢复后，双击运行即可。
#   所有提交和 tag 已经在本地建好，这个脚本只负责推送，不会重复建。
#
# 用法：右键 → 使用 PowerShell 运行
#     或：powershell -ExecutionPolicy Bypass -File tools\Push-ToGitHub.ps1

$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

Write-Host "仓库：$repo" -ForegroundColor Cyan
Write-Host ""

# 1. 先测连通性
Write-Host "[1/4] 检测 GitHub 连通性..." -ForegroundColor Yellow
$ok = $false
for ($i = 1; $i -le 3; $i++) {
    $r = & curl.exe -sS -o NUL -w "%{http_code}" --max-time 12 https://github.com 2>$null
    if ($r -match '^\d{3}$') { $ok = $true; break }
    Start-Sleep -Seconds 2
}
if (-not $ok) {
    Write-Host "  ✗ 仍然连不上 GitHub（TLS 握手失败）。" -ForegroundColor Red
    Write-Host "    这是本机网络/系统问题，不是仓库问题。等网络恢复后再运行本脚本。" -ForegroundColor DarkGray
    Write-Host "    本地提交和 tag 都已保存，不会丢失。" -ForegroundColor DarkGray
    exit 1
}
Write-Host "  ✓ 连通" -ForegroundColor Green

# 2. 推提交
Write-Host "[2/4] 推送提交..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "  ✗ 提交推送失败" -ForegroundColor Red; exit 1 }
Write-Host "  ✓ 完成" -ForegroundColor Green

# 3. 推 tag
Write-Host "[3/4] 推送版本 tag（v1 ~ v12）..." -ForegroundColor Yellow
git push origin --tags --force
if ($LASTEXITCODE -ne 0) { Write-Host "  ✗ tag 推送失败" -ForegroundColor Red; exit 1 }
Write-Host "  ✓ 完成" -ForegroundColor Green

# 4. 验证
Write-Host "[4/4] 验证远程状态..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  远程 tag 列表：" -ForegroundColor Cyan
gh api "repos/SeekAfterSeek/zs-desktop-icon-theme/tags" --jq '.[].name' 2>$null
Write-Host ""
Write-Host "  最新版本 tag：" -ForegroundColor Cyan
git ls-remote --tags origin 2>$null | Select-Object -Last 3
Write-Host ""
Write-Host "全部完成！" -ForegroundColor Green
Write-Host "打开 https://github.com/SeekAfterSeek/zs-desktop-icon-theme/releases" -ForegroundColor Cyan
Write-Host "或点仓库右侧的 Tags / Releases，就能看到 v1 ~ v12 并可逐版回退。" -ForegroundColor Cyan
