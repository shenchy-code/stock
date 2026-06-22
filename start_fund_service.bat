@echo off

rem 基金查看系统启动脚本
rem 用于Windows任务计划程序

echo 启动基金查看系统服务...

rem 设置Python路径
set PYTHON_EXE="C:\Program Files\Python312\python.exe"

rem 启动Flask应用
%PYTHON_EXE% "c:\ai\stocks\app.py"

echo 服务已启动！