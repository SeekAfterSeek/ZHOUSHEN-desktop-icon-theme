# 系统图标与文件夹图标

## 为什么之前没被风格化

桌面上的这几项不是 .lnk 快捷方式，改 IconLocation 对它们无效：

| 桌面项 | 真实身份 | 图标来源 |
|---|---|---|
| 此电脑 | 系统命名空间 {20D04FE0-3AEA-1069-A2D8-08002B30309D} | HKLM Explorer\CLSID\...\DefaultIcon |
| 回收站 | {645FF040-5081-101B-9F08-00AA002F954E} | 同上（还有 Empty/Full 两种状态） |
| 控制面板 | {26EE0668-A00A-44D7-9371-BEB064C98683} | 同上 |
| Lenovo | 其实是 C:\Users\Lenovo 用户文件夹 | 用户文件夹 / 全局文件夹 |
| 普通文件夹 | 文件系统目录 | 全局 Folder\DefaultIcon，或逐目录 desktop.ini |

## 已生效

- **普通文件夹**：用 desktop.ini 指定，已应用到桌面上的文件夹（总文件夹 / 工作成果）。
- 文件夹图标选的是库里最好看且未被其它图标占用的一张：studio_20261001_00685_2，
  外形做成文件夹轮廓（标签 + 主体）。

## 需要管理员

此电脑 / 回收站 / 控制面板 / 全局文件夹 的图标定义在 **HKLM**，普通权限写不进去。
运行 	ools\SystemIcons.bat（或右键 SystemIcons-Elevated.ps1 → 使用 PowerShell 运行），
脚本会自动请求提权，然后：

1. 设置三个系统图标的 DefaultIcon
2. 设置全局 Folder / Directory 的 DefaultIcon（所有文件夹统一）
3. 刷新图标缓存并重启 explorer

## 配色依据

系统图标按 v11 起沿用的加权规则匹配：

`
s = 0.34*cos(全图配色, 原图标配色)
  + 0.34*cos(衣服配色, 原图标配色)
  + 0.20*颜色齐全度 + 0.07*脸像素 + 0.05*锐度
`

| 图标 | 原图标主色 | 选用照片 |
|---|---|---|
| 此电脑 | 蓝 55% + 灰 45% | 见 system-icons/pc.png |
| 回收站 | 灰 87% + 蓝 13% | 见 system-icons/bin.png |
| 控制面板 | 蓝 67% + 青 24% | 见 system-icons/panel.png |
| 文件夹 | 黄（不强制配色，取最好看的一张） | studio_20261001_00685_2 |
