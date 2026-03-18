#!/bin/bash
# OpenClaw Linux 安装程序启动脚本

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  OpenClaw Linux 自动安装程序"
echo "========================================"
echo ""

if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.8+"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-tk"
    echo "  Fedora:        sudo dnf install python3 python3-tkinter"
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[错误] 未找到 tkinter，请安装："
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  Fedora:        sudo dnf install python3-tkinter"
    exit 1
fi

echo "[信息] 正在启动安装程序..."
echo ""

python3 openclaw_installer_linux.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序运行失败"
    exit 1
fi
