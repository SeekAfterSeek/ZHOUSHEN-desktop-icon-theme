# ============================================================
#  周深桌面图标主题 · 系统项图标启用器 (Enable-SystemIcons.ps1)
#
#  覆盖 5 个系统项：普通文件夹 / 此电脑 / 回收站 / 控制面板 / 用户文件夹
#
#  安全承诺（与 docs/SYSTEM-ICONS.md 的红线一致）：
#    1. 全程零删除 —— 没有任何针对文件/文件夹的删除命令；
#       唯一的移除操作是 rollback 时移除【本脚本自己添加的注册表值】。
#    2. 先备份后修改 —— apply 前把将被覆盖的注册表值（HKCU 与 HKLM 两级）
#       记录到 backup-manifest.json（JSON 清单）。
#    3. 不需要管理员权限 —— HKLM（系统级）部分只生成 .reg 文件交给你
#       双击导入，脚本本身只写 HKCU（当前用户级），不自我提权。
#    4. 不硬编码用户路径 —— 图标统一复制到 %LOCALAPPDATA% 下的纯 ASCII
#       目录再引用（用户名含中文时用 -DestDir 覆盖为其他纯 ASCII 路径）。
#    5. 可一键回退 —— -Action rollback 还原 HKCU，并给出 HKLM 回退文件。
#
#  用法：
#    powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action list
#    powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action apply
#    powershell -ExecutionPolicy Bypass -File installer\Enable-SystemIcons.ps1 -Action rollback
#
#  实测状态：普通文件夹项（Shell Icons 3/4）已在 Win10 家庭中文版 19045
#  实机全流程验证（2026-11-26）；其余项走同类 HKCU 覆盖机制，均有备份可回退。
# ============================================================
[CmdletBinding()]
param(
    [ValidateSet('list', 'apply', 'rollback')]
    [string]$Action = 'list',
    [string]$Theme = 'v13',
    [string]$IconsDir = '',   # 可手动指定包含 folder.ico / pc.ico / ... 的源目录
    [string]$DestDir = ''     # 可手动指定图标工作目录（默认 %LOCALAPPDATA%，用户名含中文时改用纯 ASCII 路径）
)

$ErrorActionPreference = 'Stop'

# ---------- 路径常量 ----------
$repoRoot = Split-Path -Parent $PSScriptRoot
if ($DestDir) { $workDir = $DestDir } else { $workDir = Join-Path $env:LOCALAPPDATA 'ZsIconTheme\system-icons' }
$backupDir    = Join-Path $env:LOCALAPPDATA 'ZsIconTheme\system-icons-backup'
$manifestPath = Join-Path $backupDir 'backup-manifest.json'
$hklmApplyPath = Join-Path $backupDir 'apply_hklm.reg'
$hklmUndoPath  = Join-Path $backupDir 'rollback_hklm.reg'
$shellIconsRel = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons'
$clsidBaseRel  = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CLSID'

# ---------- 目标清单 ----------
# 每个元素 = 一个注册表值。HKCU 由脚本直接写（免管理员）；HKLM 进生成的 .reg。
# 普通文件夹走 Shell Icons 的 3(关闭态)/4(打开态)；
# 其余四项走 Explorer\CLSID\{GUID}\DefaultIcon，回收站含 Empty/Full 两态。
$entries = @(
    @{ Key='folder3'; Name='普通文件夹(关闭态)'; Sub='ShellIcons'; ValueName='3';         Ico='folder.ico' },
    @{ Key='folder4'; Name='普通文件夹(打开态)'; Sub='ShellIcons'; ValueName='4';         Ico='folder.ico' },
    @{ Key='pc';      Name='此电脑';       Sub='Clsid'; Guid='{20D04FE0-3AEA-1069-A2D8-08002B30309D}'; ValueName='(default)'; Ico='pc.ico' },
    @{ Key='bin';     Name='回收站';       Sub='Clsid'; Guid='{645FF040-5081-101B-9F08-00AA002F954E}'; ValueName='(default)'; Ico='bin.ico' },
    @{ Key='binE';    Name='回收站(空)';   Sub='Clsid'; Guid='{645FF040-5081-101B-9F08-00AA002F954E}'; ValueName='Empty'; Ico='bin.ico' },
    @{ Key='binF';    Name='回收站(满)';   Sub='Clsid'; Guid='{645FF040-5081-101B-9F08-00AA002F954E}'; ValueName='Full';  Ico='bin.ico' },
    @{ Key='panelA';  Name='控制面板';     Sub='Clsid'; Guid='{21EC2020-3AEA-1069-A2DD-08002B30309D}'; ValueName='(default)'; Ico='panel.ico' },
    @{ Key='panelB';  Name='控制面板(全部项)'; Sub='Clsid'; Guid='{26EE0668-A00A-44D7-9371-BEB064C98683}'; ValueName='(default)'; Ico='panel.ico' },
    @{ Key='user';    Name='用户文件夹';   Sub='Clsid'; Guid='{59031A47-3F72-44A7-89C5-5595FE6B30EE}'; ValueName='(default)'; Ico='user.ico' }
)

function Get-RegPath([string]$hive, [hashtable]$e) {
    if ($e.Sub -eq 'ShellIcons') { return ($hive + ':\' + $shellIconsRel) }
    return ($hive + ':\' + $clsidBaseRel + '\' + $e.Guid + '\DefaultIcon')
}

function Read-RegValue([string]$Path, [string]$Name) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $k = Get-Item -LiteralPath $Path
    if ($Name -eq '(default)') { return $k.GetValue('') }
    if (-not ($k.GetValueNames() -contains $Name)) { return $null }
    return $k.GetValue($Name)
}

function Test-IcoHeader([string]$Path) {
    # 合法 ICO：前 4 字节 00 00 01 00
    $b = [System.IO.File]::ReadAllBytes($Path)
    return ($b.Length -ge 6 -and $b[0] -eq 0 -and $b[1] -eq 0 -and $b[2] -eq 1 -and $b[3] -eq 0)
}

function Copy-Icons {
    $src = if ($IconsDir) { $IconsDir } else { Join-Path $repoRoot ('themes\' + $Theme + '\system-icons') }
    if (-not (Test-Path -LiteralPath (Join-Path $src 'folder.ico'))) {
        throw "在 '$src' 找不到 folder.ico。请解压完整仓库后运行，或用 -IconsDir 指定图标目录。"
    }
    New-Item -ItemType Directory -Path $workDir -Force | Out-Null
    Copy-Item -Path (Join-Path $src '*.ico') -Destination $workDir -Force
    foreach ($e in $entries) {
        $p = Join-Path $workDir $e.Ico
        if (-not (Test-Path -LiteralPath $p)) { throw "缺少图标文件：$p" }
        if (-not (Test-IcoHeader $p)) { throw "ICO 文件头校验失败（不是合法 ICO）：$p" }
    }
    Write-Host "[OK] 图标已复制并通过头部校验：$workDir"
}

function ConvertTo-RegEscaped([string]$s) {
    # .reg 内容里：反斜杠翻倍、引号转义（用 .Replace，避免 -replace 的正则转义坑）
    return $s.Replace('\', '\\').Replace('"', '\"')
}

function Show-List {
    Write-Host '=== 当前注册表状态（只读，不修改任何东西） ==='
    foreach ($e in $entries) {
        $hkcu = Read-RegValue (Get-RegPath 'HKCU' $e) $e.ValueName
        $hklm = Read-RegValue (Get-RegPath 'HKLM' $e) $e.ValueName
        $s1 = if ($null -ne $hkcu) { $hkcu } else { '(未设置)' }
        $s2 = if ($null -ne $hklm) { $hklm } else { '(未设置)' }
        Write-Host ('  {0,-20} HKCU={1}' -f $e.Name, $s1)
        Write-Host ('  {0,-20} HKLM={1}' -f '', $s2)
    }
    Write-Host ''
    Write-Host 'apply = 备份并写入；rollback = 按备份还原。'
}

function New-HklmRegFile {
    param([object[]]$Manifest, [string]$OutFile, [switch]$Undo)
    $lines = @('Windows Registry Editor Version 5.00', '')
    if ($Undo) {
        $lines += '; ZhouShen theme: restore HKLM values to the state BEFORE apply.'
        $lines += '; Import with admin. A "name"=- line removes a value that did not exist before.'
    } else {
        $lines += '; ZhouShen theme: system-level icon definitions (generated by Enable-SystemIcons.ps1).'
        $lines += '; Import: double-click this file and confirm the UAC prompt.'
    }
    $lines += ''
    $cur = ''
    foreach ($m in $Manifest) {
        $full = 'HKEY_LOCAL_MACHINE\' + ($m.HklmPath -replace '^HKLM:\\', '')
        if ($full -ne $cur) { $lines += ''; $lines += ('[' + $full + ']'); $cur = $full }
        $tok = if ($m.ValueName -eq '(default)') { '@' } else { ('"' + $m.ValueName + '"') }
        if ($Undo) {
            if ($m.HklmOldExists) { $lines += ($tok + '="' + (ConvertTo-RegEscaped ([string]$m.HklmOldData)) + '"') }
            else { $lines += ($tok + '=-') }
        } else {
            $lines += ($tok + '="' + (ConvertTo-RegEscaped $m.NewData) + '"')
        }
    }
    $lines += ''
    # .reg 必须存为 UTF-16 LE（Out-File -Encoding Unicode 自带 BOM），UTF-8 会导致导入乱码（PITFALLS #16）
    $lines | Out-File -LiteralPath $OutFile -Encoding Unicode
}

function Invoke-Apply {
    Copy-Icons
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    Write-Host '=== 1/3 备份将被覆盖的原值（HKCU 与 HKLM 两级都记） ==='
    $manifest = @()
    foreach ($e in $entries) {
        $hkcuPath = Get-RegPath 'HKCU' $e
        $hklmPath = Get-RegPath 'HKLM' $e
        $hkcuOld = Read-RegValue $hkcuPath $e.ValueName
        $hklmOld = Read-RegValue $hklmPath $e.ValueName
        $new = (Join-Path $workDir $e.Ico) + ',0'
        $manifest += [pscustomobject]@{
            Key = $e.Key; Name = $e.Name; Ico = $e.Ico
            HkcuPath = $hkcuPath; HklmPath = $hklmPath; ValueName = $e.ValueName
            HkcuOldExists = ($null -ne $hkcuOld); HkcuOldData = $hkcuOld
            HklmOldExists = ($null -ne $hklmOld); HklmOldData = $hklmOld
            NewData = $new
        }
    }
    $manifest | ConvertTo-Json -Depth 4 | Out-File -LiteralPath $manifestPath -Encoding UTF8
    Write-Host "[OK] 备份清单：$manifestPath"

    Write-Host '=== 2/3 写入 HKCU（当前用户级，免管理员，立即生效） ==='
    foreach ($m in $manifest) {
        if (-not (Test-Path -LiteralPath $m.HkcuPath)) { New-Item -Path $m.HkcuPath -Force | Out-Null }
        if ($m.ValueName -eq '(default)') {
            Set-Item -LiteralPath $m.HkcuPath -Value $m.NewData
        } else {
            New-ItemProperty -LiteralPath $m.HkcuPath -Name $m.ValueName -Value $m.NewData -PropertyType String -Force | Out-Null
        }
        $prev = if ($m.HkcuOldExists) { $m.HkcuOldData } else { '(原值不存在，本次新增)' }
        Write-Host ('  [OK] {0}: {1} -> {2}' -f $m.Name, $prev, $m.NewData)
    }

    Write-Host '=== 3/3 生成 HKLM 系统级 .reg（UTF-16 LE，供管理员导入） ==='
    New-HklmRegFile -Manifest $manifest -OutFile $hklmApplyPath
    New-HklmRegFile -Manifest $manifest -OutFile $hklmUndoPath -Undo
    Write-Host "[OK] 应用文件：$hklmApplyPath"
    Write-Host "[OK] 回退文件：$hklmUndoPath（apply 前的原值快照）"

    Write-Host ''
    Write-Host '=== 下一步（两件事） ==='
    Write-Host 'A. 双击导入系统级文件（推荐，让「任何位置新建文件夹」都生效）：'
    Write-Host "   $hklmApplyPath  ->  UAC 点[是] -> 确认导入"
    Write-Host 'B. 刷新图标缓存（两级，依次尝试）：'
    Write-Host '   1) ie4uinit.exe -show'
    Write-Host '   2) 桌面/新建文件夹仍旧图标时，重启 explorer：'
    Write-Host '      taskkill /f /im explorer.exe 然后运行 explorer.exe'
    Write-Host '      （或任务管理器 -> 右键「Windows 资源管理器」-> 重新启动；任务栏闪两秒，不影响其他程序）'
    Write-Host ''
    Write-Host ('回退命令：powershell -ExecutionPolicy Bypass -File "{0}" -Action rollback' -f $PSCommandPath)
}

function Invoke-Rollback {
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw "没有找到备份清单 $manifestPath —— 没有可回退的记录，rollback 什么都不做。"
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    Write-Host '=== 1/2 还原 HKCU（当前用户级，直接写回原值） ==='
    foreach ($m in $manifest) {
        if ($m.HkcuOldExists) {
            if ($m.ValueName -eq '(default)') {
                Set-Item -LiteralPath $m.HkcuPath -Value ([string]$m.HkcuOldData)
            } else {
                New-ItemProperty -LiteralPath $m.HkcuPath -Name $m.ValueName -Value ([string]$m.HkcuOldData) -PropertyType String -Force | Out-Null
            }
            Write-Host ('  [OK] {0} 还原为 {1}' -f $m.Name, $m.HkcuOldData)
        } else {
            # 该值 apply 前不存在：仅移除本脚本添加的这一个值（不删键、不动其他值）
            Remove-ItemProperty -LiteralPath $m.HkcuPath -Name $m.ValueName -ErrorAction SilentlyContinue
            Write-Host ('  [OK] {0}：移除本脚本新增的值（原本不存在）' -f $m.Name)
        }
    }
    Write-Host '=== 2/2 HKLM 系统级 ==='
    if (Test-Path -LiteralPath $hklmUndoPath) {
        Write-Host '  请以管理员身份导入回退文件（内容是 apply 前的原值快照，或删除新增值的标记）：'
        Write-Host "  $hklmUndoPath"
    } else {
        Write-Host '  （未找到 HKLM 回退文件，跳过。若之前导入过 apply_hklm.reg，请手动还原。）'
    }
    Write-Host '[OK] 回退完成。刷新缓存：ie4uinit -show，必要时重启 explorer。'
}

switch ($Action) {
    'list'     { Show-List }
    'apply'    { Invoke-Apply }
    'rollback' { Invoke-Rollback }
}
