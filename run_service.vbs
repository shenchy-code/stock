Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\ai\stocks"
WshShell.Run "python c:\ai\stocks\app.py", 0
