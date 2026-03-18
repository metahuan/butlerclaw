#!/bin/bash
# OpenClaw macOS 安装程序启动脚本

set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  OpenClaw macOS 自动安装程序"
echo "========================================"
echo ""

if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.8+"
    echo "推荐: 从 https://python.org 或 brew install python"
    exit 1
fi

echo "[信息] 正在启动安装程序..."
echo ""

python3 openclaw_installer_macos.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 程序运行失败"
    exit 1
fi
