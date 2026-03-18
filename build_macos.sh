#!/bin/bash
# 打包 OpenClaw 安装助手 (macOS) - 生成 .app
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "  OpenClaw 安装助手 - macOS 打包"
echo "========================================"
echo ""

if ! command -v python3 &>/dev/null; then
    echo "[错误] 未找到 python3"
    exit 1
fi

echo "[1/3] 安装打包依赖..."
python3 -m pip install -q -r requirements-build.txt

echo "[2/3] 开始打包（仅当前平台：macOS）..."
python3 -m PyInstaller --noconfirm \
    --windowed \
    --name "OpenClaw安装助手" \
    openclaw_assistant.py

echo "[3/3] 完成"
echo ""
echo "输出: dist/OpenClaw安装助手.app"
echo "可将 .app 拖到「应用程序」或直接双击运行。"
echo ""
