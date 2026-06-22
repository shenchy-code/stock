@echo off
echo Stopping service on port 5002 (only kills the PID listening on 5002)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_restart_5002.ps1"
echo Starting new service...
cd /d %~dp0
python app.py
pause
