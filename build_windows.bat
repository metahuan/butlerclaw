@echo off
chcp 65001 >nul
title 打包 OpenClaw 安装助手 (Windows)
echo ========================================
echo   OpenClaw 安装助手 - Windows 打包
echo ========================================
echo.

cd /d "%~dp0"
if errorlevel 1 (
    echo [错误] 无法进入脚本所在目录
    goto :end
)

REM 检查 Python（优先 python，其次 py）
set PYCMD=python
python --version >nul 2>&1 || set PYCMD=py
%PYCMD% -c "import sys; print(sys.executable)" 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先安装 Python 3.8+ 并勾选「Add Python to PATH」
    echo 或在本目录打开「命令提示符」执行: py -m pip install pyinstaller 后重试
    goto :end
)

echo [1/3] 安装打包依赖...
%PYCMD% -m pip install -q -r requirements-build.txt
if errorlevel 1 (
    echo [错误] pip 安装失败
    goto :end
)

echo [2/3] 清理旧构建缓存...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [3/3] 开始打包（仅打包当前平台：Windows）...
%PYCMD% -m PyInstaller --noconfirm "openclaw_installer.spec"
if errorlevel 1 (
    echo [错误] 打包失败
    goto :end
)

echo [4/4] 完成
echo.
echo 输出目录: dist\
echo 可执行文件: dist\Butlerclaw龙虾管家.exe
echo.

:end
echo.
pause
