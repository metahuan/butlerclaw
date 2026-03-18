@echo off
chcp 65001 >nul
title OpenClaw 安装程序
echo ========================================
echo     OpenClaw Windows 自动安装程序
echo ========================================
echo.

REM 检查 Python（优先 python，其次 py）
set PYCMD=
python --version >nul 2>&1 && set PYCMD=python
if not defined PYCMD py --version >nul 2>&1 && set PYCMD=py
if not defined PYCMD (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://python.org  安装时务必勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [信息] Python 已安装
echo [信息] 正在启动安装程序...
echo.

REM 运行 v2 安装程序（与 README 一致）
%PYCMD% "%~dp0openclaw_installer_v2.py"

if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败，请检查是否已安装 tkinter
    pause
)
