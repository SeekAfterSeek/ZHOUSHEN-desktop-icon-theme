#Requires -Version 5.1
<#
.SYNOPSIS
    周深主题桌面图标 —— 安装 / 回退 / 预览

.DESCRIPTION
    只修改桌面快捷方式（.lnk）的图标，不修改壁纸、不修改系统主题、
    不修改任何注册表显示设置。所有改动可一键回退。

.PARAMETER Theme
    要应用的方案：v11 / planB / planC（默认 v11）

.PARAMETER Action
    apply    应用主题
    rollback 回退到安装前的原始图标
    list     列出本机检测到的、当前主题支持的应用
    preview  只列出会改哪些，不实际修改

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File installer\Install-Theme.ps1 -Action apply
    powershell -ExecutionPolicy Bypass -File installer\Install-Theme.ps1 -Theme planC -Action apply
    powershell -ExecutionPolicy Bypass -File installer\Install-Theme.ps1 -Action rollback
#>
[CmdletBinding()]
param(
    [ValidateSet('v13', 'v12', 'v11', 'planB', 'planC')]
    [string]$Theme = 'v13',

    [ValidateSet('apply', 'rollback', 'uninstall', 'list', 'preview')]
    [string]$Action = 'apply'
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- 路径
$Root      = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ThemeDir  = Join-Path $Root "themes\$Theme\icons"
$StateDir  = Join-Path $env:LOCALAPPDATA 'ZsIconTheme'
$StateFile = Join-Path $StateDir 'original-shortcuts.json'

# ICO 必须放在纯 ASCII 无空格路径下，否则中文/空格路径下的 ICO
# 在桌面渲染为空白图标（本项目实测，见 docs/PITFALLS.md 第 2 条）
$IconCache = Join-Path $env:LOCALAPPDATA 'ZsIconTheme\icons'

$ThemeNames = @{ v13 = '第十三版（定稿 · 24 应用 + 5 系统项）'
                 v12 = '第十二版（混搭 Plan B/C · 全部方形）'
                 v11 = '第十一版（三标准加权·终版）'
                 planB = 'Plan B（全新照片·方形为主）'
                 planC = 'Plan C（全新照片·圆形为主）' }

# ---------------------------------------------------------------- 应用清单
# key    : themes\<theme>\icons\<key>.png 的文件名
# names  : 这个 key 可能对应的中文 / 英文快捷方式名（用户的叫法可能不同）
# desc   : 展示用
$Catalog = @(
    @{ key = 'weixin';    names = @('微信', 'WeChat', 'Weixin');                     desc = '微信' }
    @{ key = 'qqmusic';   names = @('QQ音乐', 'QQMusic');                            desc = 'QQ音乐' }
    @{ key = 'bilibili';  names = @('哔哩哔哩', 'bilibili', 'Bilibili');              desc = '哔哩哔哩' }
    @{ key = 'chrome';    names = @('Google Chrome', 'Chrome');                      desc = 'Google Chrome' }
    @{ key = 'edge';      names = @('个人 - Edge', 'Microsoft Edge', 'Edge');         desc = 'Microsoft Edge' }
    @{ key = 'se360';     names = @('360安全浏览器', '360浏览器', '360se');             desc = '360 安全浏览器' }
    @{ key = 'vscode';    names = @('Visual Studio Code', 'VS Code', 'Code');         desc = 'Visual Studio Code' }
    @{ key = 'cursor';    names = @('Cursor');                                       desc = 'Cursor' }
    @{ key = 'deepseek';  names = @('DeepSeek Harness', 'DeepSeek');                  desc = 'DeepSeek Harness' }
    @{ key = 'cherry';    names = @('Cherry Studio');                                desc = 'Cherry Studio' }
    @{ key = 'workbuddy'; names = @('WorkBuddy');                                    desc = 'WorkBuddy' }
    @{ key = 'wps';       names = @('WPS Office', 'WPS');                            desc = 'WPS Office' }
    @{ key = 'luping';    names = @('全能录屏助手', '录屏助手');                        desc = '全能录屏助手' }
    @{ key = 'jianying';  names = @('剪映专业版', '剪映');                             desc = '剪映专业版' }
    @{ key = 'baidunet';  names = @('百度网盘', 'BaiduNetdisk');                      desc = '百度网盘' }
    @{ key = 'feishu';    names = @('飞书', 'Feishu', 'Lark');                        desc = '飞书' }
    @{ key = 'clash';     names = @('Clash Verge', 'Clash Verge Rev', 'Clash');       desc = 'Clash Verge' }
    @{ key = 'pycharm';   names = @('PyCharm 2026.2.3', 'PyCharm', 'PyCharm Community Edition', 'PyCharm Professional Edition'); desc = 'PyCharm' }
    @{ key = 'todesk';    names = @('ToDesk');                                       desc = 'ToDesk' }
    @{ key = 'huchuan';   names = @('互传', 'vivo互传', 'EasyShare');                  desc = '互传' }
    @{ key = 'mailmaster';names = @('网易邮箱大师', '网易邮箱', 'Mail Master');          desc = '网易邮箱大师' }
    @{ key = 'lenovopc';  names = @('联想电脑管家', 'Lenovo PC Manager');              desc = '联想电脑管家' }
    @{ key = 'qq';        names = @('腾讯QQ', 'QQ');                                  desc = '腾讯QQ' }
    @{ key = 'wemeet';    names = @('腾讯会议', 'Tencent Meeting', 'VooV Meeting');    desc = '腾讯会议' }
)

# ---------------------------------------------------------------- 工具函数
function Get-DesktopDirs {
    $dirs = @()
    $dirs += [Environment]::GetFolderPath('Desktop')
    $public = [Environment]::GetFolderPath('CommonDesktopDirectory')
    if ($public) { $dirs += $public }
    # OneDrive 重定向的桌面
    if ($env:OneDrive) {
        $od = Join-Path $env:OneDrive 'Desktop'
        if (Test-Path $od) { $dirs += $od }
    }
    $dirs | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique
}

function Find-Shortcut {
    param([string[]]$Names)
    # 注意：必须用 [System.Collections.ArrayList] 或 @() 强制数组。
    # 若只用 `$found += ...`，当只命中 1 个时会退化为 String，
    # 随后 $found[0] 取到的是首字母 'C' 而不是路径（本项目踩过）。
    $found = [System.Collections.Generic.List[string]]::new()
    foreach ($dir in (Get-DesktopDirs)) {
        foreach ($f in (Get-ChildItem -LiteralPath $dir -Filter '*.lnk' -ErrorAction SilentlyContinue)) {
            $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
            foreach ($n in $Names) {
                if ($base -ieq $n) { $found.Add($f.FullName); break }
            }
        }
    }
    , $found.ToArray()
}

function New-AsciiIconDir {
    if (-not (Test-Path $IconCache)) { New-Item -ItemType Directory -Path $IconCache -Force | Out-Null }
    $IconCache
}

function Refresh-Desktop {
    # 只通知 shell 刷新图标，不重启 explorer —— 避免打断用户正在做的事
    try { & "$env:SystemRoot\System32\ie4uinit.exe" -show 2>$null } catch {}
    $sig = @'
[System.Runtime.InteropServices.DllImport("shell32.dll")]
public static extern void SHChangeNotify(int eventId, int flags, System.IntPtr item1, System.IntPtr item2);
'@
    try {
        $sh = Add-Type -MemberDefinition $sig -Name 'ShellNotify' -Namespace 'ZsTheme' -PassThru
        # SHCNE_ASSOCCHANGED = 0x08000000, SHCNF_IDLIST = 0
        $sh::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
    } catch {}
}

function Save-State {
    param($Rows)
    if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir -Force | Out-Null }
    $Rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Load-State {
    if (Test-Path $StateFile) {
        return @(Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json)
    }
    return @()
}

# ---------------------------------------------------------------- 主流程
$sh = New-Object -ComObject WScript.Shell

switch ($Action) {

    'list' {
        Write-Host ""
        Write-Host "  主题方案：$($ThemeNames[$Theme])" -ForegroundColor Cyan
        Write-Host "  支持的 24 个应用，检测结果：" -ForegroundColor Cyan
        Write-Host ""
        $hit = 0
        foreach ($c in $Catalog) {
            $found = Find-Shortcut $c.names
            if ($found.Count -gt 0) {
                $hit++
                Write-Host ("  [√] {0,-22} {1}" -f $c.desc, [string]$found[0]) -ForegroundColor Green
            } else {
                Write-Host ("  [ ] {0,-22} 未安装 / 桌面无快捷方式" -f $c.desc) -ForegroundColor DarkGray
            }
        }
        Write-Host ""
        Write-Host "  命中 $hit / 24" -ForegroundColor Yellow
        Write-Host ""
    }

    'apply' {
        if (-not (Test-Path $ThemeDir)) {
            throw "找不到主题目录：$ThemeDir"
        }
        $cache = New-AsciiIconDir

        # 首次应用：把原始 IconLocation 存下来，供 rollback 用
        $state = Load-State
        $stateMap = @{}
        foreach ($s in $state) { $stateMap[$s.lnk] = $s }

        $rows = New-Object System.Collections.Generic.List[object]
        $applied = 0
        $skipped = 0
        $denied = New-Object System.Collections.Generic.List[string]

        foreach ($c in $Catalog) {
            $srcIco = Join-Path $ThemeDir ($c.key + '.ico')
            if (-not (Test-Path $srcIco)) { continue }

            $lnks = @(Find-Shortcut $c.names)
            if ($lnks.Count -eq 0) { continue }

            # 复制到纯 ASCII 路径（含空格/中文会导致桌面白图标）
            $icoPath = Join-Path $cache ($c.key + '.ico')
            try { Copy-Item -LiteralPath $srcIco -Destination $icoPath -Force } catch {
                $skipped++
                Write-Host ("  [!] {0,-22} ICO 复制失败" -f $c.desc) -ForegroundColor Yellow
                continue
            }

            foreach ($lnkPath in $lnks) {
                try {
                    $lnk = $sh.CreateShortcut($lnkPath)

                    if (-not $stateMap.ContainsKey($lnkPath)) {
                        $rows.Add([pscustomobject]@{
                            lnk          = $lnkPath
                            name         = [System.IO.Path]::GetFileNameWithoutExtension($lnkPath)
                            iconLocation = $lnk.IconLocation
                            target       = $lnk.TargetPath
                        })
                    }

                    $lnk.IconLocation = "$icoPath,0"
                    $lnk.Save()
                    $applied++
                    Write-Host ("  [√] {0,-22} {1}" -f $c.desc, (Split-Path -Leaf $lnkPath)) -ForegroundColor Green
                }
                catch {
                    # 公共桌面（C:\Users\Public\Desktop）需要管理员权限
                    $denied.Add($lnkPath)
                    Write-Host ("  [×] {0,-22} 无权限（公共桌面需管理员）" -f $c.desc) -ForegroundColor DarkYellow
                }
            }
        }

        if ($rows.Count -gt 0) { Save-State (@($state) + $rows.ToArray()) }
        Refresh-Desktop

        Write-Host ""
        Write-Host ("  已应用 {0} 个快捷方式  |  跳过 {1}  |  无权限 {2}" -f `
            $applied, $skipped, $denied.Count) -ForegroundColor Cyan
        Write-Host "  壁纸、系统主题、注册表显示设置 均未改动" -ForegroundColor DarkGray

        if ($denied.Count -gt 0) {
            Write-Host ""
            Write-Host "  以下快捷方式在公共桌面，需要管理员权限：" -ForegroundColor Yellow
            foreach ($p in $denied) { Write-Host ("    " + $p) -ForegroundColor DarkGray }
            Write-Host ""
            Write-Host "  以管理员身份重新运行本脚本即可全部应用：" -ForegroundColor Yellow
            Write-Host ("    powershell -ExecutionPolicy Bypass -File `"" + $MyInvocation.MyCommand.Path + "`" -Action apply") -ForegroundColor DarkGray
        }

        Write-Host ""
        Write-Host "  回退：powershell -File installer\Install-Theme.ps1 -Action rollback" -ForegroundColor DarkGray
        Write-Host ""
    }

    'uninstall' {
        # 与 rollback 同义，保留别名方便记忆
        $state = Load-State
        if ($state.Count -eq 0) {
            Write-Host "  没有找到安装记录，无需回退。" -ForegroundColor Yellow
            break
        }
        $n = 0
        $denied = 0
        foreach ($s in $state) {
            if (-not (Test-Path -LiteralPath $s.lnk)) { continue }
            try {
                $lnk = $sh.CreateShortcut($s.lnk)
                if ([string]::IsNullOrWhiteSpace($s.iconLocation) -or $s.iconLocation -eq ',0') {
                    $lnk.IconLocation = "$($s.target),0"
                } else {
                    $lnk.IconLocation = $s.iconLocation
                }
                $lnk.Save()
                $n++
            } catch { $denied++ }
        }
        Remove-Item -LiteralPath $StateFile -Force -ErrorAction SilentlyContinue
        Refresh-Desktop
        Write-Host ("  已还原 {0} 个快捷方式  无权限 {1}" -f $n, $denied) -ForegroundColor Green
    }

    'preview' {
        Write-Host ""
        Write-Host "  预览模式（不会修改任何文件）" -ForegroundColor Cyan
        Write-Host ""
        foreach ($c in $Catalog) {
            $lnks = @(Find-Shortcut $c.names)
            if ($lnks.Count -gt 0) {
                Write-Host ("  将替换：{0,-22} <- {1}" -f $c.desc, (Split-Path -Leaf $lnks[0])) -ForegroundColor Green
            }
        }
        Write-Host ""
    }

    'rollback' {
        $state = Load-State
        if ($state.Count -eq 0) {
            Write-Host ""
            Write-Host "  没有找到安装记录（$StateFile），无法回退。" -ForegroundColor Yellow
            Write-Host "  如果你之前用其他方式改过图标，请手动在快捷方式属性里设置。" -ForegroundColor DarkGray
            Write-Host ""
            break
        }
        $n = 0
        $denied = 0
        foreach ($s in $state) {
            if (-not (Test-Path -LiteralPath $s.lnk)) { continue }
            try {
                $lnk = $sh.CreateShortcut($s.lnk)
                if ([string]::IsNullOrWhiteSpace($s.iconLocation) -or $s.iconLocation -eq ',0') {
                    $lnk.IconLocation = "$($s.target),0"
                } else {
                    $lnk.IconLocation = $s.iconLocation
                }
                $lnk.Save()
                $n++
                Write-Host ("  [←] {0}" -f $s.name) -ForegroundColor Cyan
            } catch {
                $denied++
                Write-Host ("  [×] {0}  无权限" -f $s.name) -ForegroundColor DarkYellow
            }
        }
        Remove-Item -LiteralPath $StateFile -Force -ErrorAction SilentlyContinue
        Refresh-Desktop
        Write-Host ""
        Write-Host ("  已还原 {0} 个快捷方式到安装前状态  |  无权限 {1}" -f $n, $denied) -ForegroundColor Green
        if ($denied -gt 0) {
            Write-Host "  公共桌面的快捷方式需要以管理员身份重新运行才能回退" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}
