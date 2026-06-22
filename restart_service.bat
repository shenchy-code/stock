@echo off
echo Stopping service on port 5002 (only kills the PID listening on 5002)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_restart_5002.ps1"
echo.
echo Starting service...
wscript.exe c:\ai\stocks\run_service.vbs
echo.
echo Service restarted. Refresh your browser.
pause
