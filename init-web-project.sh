#!/bin/bash
# OpenClaw Hub 前端项目初始化脚本
# 运行此脚本创建 Next.js + shadcn/ui 项目

echo "🚀 初始化 OpenClaw Hub 前端项目..."
echo ""

# 获取脚本所在目录的父目录（即 openclaw-hub）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/openclaw-hub"
WEB_DIR="$PROJECT_DIR/web"

echo "📁 项目目录: $WEB_DIR"

# 创建项目目录
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 检查是否已存在项目
if [ -d "$WEB_DIR" ] && [ -f "$WEB_DIR/package.json" ]; then
    echo "⚠️  项目已存在，跳过创建"
    echo "   如需重新创建，请先删除 $WEB_DIR 目录"
    exit 0
fi

# 初始化 Next.js 项目
echo "📦 创建 Next.js 项目..."
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm << EOF
y
EOF

if [ $? -ne 0 ]; then
    echo "❌ 创建 Next.js 项目失败"
    exit 1
fi

cd "$WEB_DIR"

# 安装 shadcn/ui
echo ""
echo "🎨 安装 shadcn/ui..."
npx shadcn-ui@latest init -d << EOF
y
EOF

if [ $? -ne 0 ]; then
    echo "❌ 安装 shadcn/ui 失败"
    exit 1
fi

# 安装常用组件
echo ""
echo "🔧 安装 UI 组件..."
npx shadcn-ui@latest add button card input badge tabs dialog avatar separator skeleton -y

# 安装其他依赖
echo ""
echo "📚 安装其他依赖..."
npm install lucide-react framer-motion clsx tailwind-merge

# 创建项目结构
echo ""
echo "📁 创建项目结构..."

mkdir -p app/skills/\[id\]
mkdir -p app/user/profile
mkdir -p app/developer
mkdir -p components/layout
mkdir -p components/skills
mkdir -p components/common
mkdir -p lib
mkdir -p hooks
mkdir -p types
mkdir -p public/images

echo ""
echo "✅ 项目初始化完成！"
echo ""
echo "项目位置: $WEB_DIR"
echo ""
echo "下一步："
echo "  1. cd $WEB_DIR"
echo "  2. npm run dev"
echo "  3. 打开 http://localhost:3000"
echo ""
echo "💡 提示: 将 web-components 目录下的组件复制到 src/components/ 目录中使用"
