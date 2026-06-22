' 创建基金服务启动快捷方式
' 用于添加到Windows启动文件夹

Set WshShell = WScript.CreateObject("WScript.Shell")

' 启动文件夹路径
StartupPath = WshShell.SpecialFolders("Startup")

' 快捷方式信息
ShortcutPath = StartupPath & "\FundService.lnk"
TargetPath = "C:\Program Files\Python312\python.exe"
Arguments = """c:\ai\stocks\app.py"""
WorkingDir = "c:\ai\stocks"
Description = "基金查看系统服务"
IconPath = "C:\Program Files\Python312\python.exe"

' 创建快捷方式
Set oShellLink = WshShell.CreateShortcut(ShortcutPath)
oShellLink.TargetPath = TargetPath
oShellLink.Arguments = Arguments
oShellLink.WorkingDirectory = WorkingDir
oShellLink.Description = Description
oShellLink.IconLocation = IconPath
' 设置为最小化运行
oShellLink.WindowStyle = 7
oShellLink.Save

WScript.Echo "快捷方式已创建到启动文件夹: " & ShortcutPath