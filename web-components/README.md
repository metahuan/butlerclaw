# OpenClaw Hub Web

OpenClaw Hub 前端项目 - 基于 Next.js + TailwindCSS + shadcn/ui

## 🚀 快速开始

### 环境要求

- Node.js 18+
- npm 9+

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/openclaw/openclaw-hub.git
cd openclaw-hub/web

# 2. 安装依赖
npm install

# 3. 运行开发服务器
npm run dev

# 4. 打开浏览器访问
http://localhost:3000
```

### 构建生产版本

```bash
# 构建
npm run build

# 启动生产服务器
npm start
```

## 📁 项目结构

```
web/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 首页
│   ├── skills/            # 技能市场
│   │   ├── page.tsx       # 技能列表
│   │   └── [id]/          # 技能详情
│   │       └── page.tsx
│   ├── user/              # 用户中心
│   │   └── profile/
│   │       └── page.tsx
│   ├── developer/         # 开发者中心
│   │   └── page.tsx
│   ├── layout.tsx         # 根布局
│   └── globals.css        # 全局样式
├── components/            # 组件
│   ├── ui/               # shadcn/ui 组件
│   ├── layout/           # 布局组件
│   │   ├── Navbar.tsx    # 导航栏
│   │   └── Footer.tsx    # 页脚
│   ├── skills/           # 技能相关组件
│   │   ├── SkillCard.tsx # 技能卡片
│   │   └── SkillList.tsx # 技能列表
│   └── common/           # 通用组件
├── lib/                  # 工具函数
│   ├── utils.ts          # 通用工具
│   └── api.ts            # API 封装
├── hooks/                # 自定义 Hooks
├── types/                # TypeScript 类型
├── public/               # 静态资源
└── tailwind.config.ts    # Tailwind 配置
```

## 🎨 设计规范

### 色彩系统

- **主色**: `#3B82F6` (蓝色)
- **成功**: `#10B981` (绿色)
- **警告**: `#F59E0B` (橙色)
- **错误**: `#EF4444` (红色)

### 字体

- **中文**: system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei'
- **英文**: Inter, system-ui

### 间距

基于 4px 的倍数系统：4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px

## 🛠 技术栈

- **框架**: [Next.js 14](https://nextjs.org/)
- **样式**: [TailwindCSS](https://tailwindcss.com/)
- **组件库**: [shadcn/ui](https://ui.shadcn.com/)
- **图标**: [Lucide React](https://lucide.dev/)
- **动画**: [Framer Motion](https://www.framer.com/motion/)

## 📱 页面列表

| 页面 | 路径 | 描述 |
|------|------|------|
| 首页 | `/` | 产品介绍、热门技能、功能特性 |
| 技能市场 | `/skills` | 技能列表、搜索、筛选 |
| 技能详情 | `/skills/[id]` | 技能详情、安装、评价 |
| 用户中心 | `/user/profile` | 个人信息、我的技能、订单 |
| 开发者中心 | `/developer` | 技能上传、数据统计、收益 |
| 下载页 | `/download` | 软件下载、版本历史 |
| 价格页 | `/pricing` | 会员方案、价格对比 |

## 🔧 开发指南

### 添加新页面

```bash
# 在 app 目录下创建新文件夹
mkdir app/new-page

# 创建 page.tsx
touch app/new-page/page.tsx
```

### 添加新组件

```bash
# 在 components 目录下创建
# 例如：创建 Button 组件
touch components/common/Button.tsx
```

### 使用 shadcn/ui 组件

```bash
# 安装组件
npx shadcn-ui@latest add button

# 在代码中使用
import { Button } from '@/components/ui/button'
```

## 📝 代码规范

### 文件命名

- 组件: `PascalCase.tsx` (如 `SkillCard.tsx`)
- 页面: `page.tsx`, `layout.tsx`
- 工具: `camelCase.ts` (如 `api.ts`)
- 样式: `kebab-case.css` (如 `globals.css`)

### 组件结构

```tsx
// 1. 导入
import { useState } from 'react'
import { Button } from '@/components/ui/button'

// 2. 类型定义
interface Props {
  title: string
}

// 3. 组件
export function Component({ title }: Props) {
  // 状态
  const [count, setCount] = useState(0)
  
  // 处理函数
  const handleClick = () => {
    setCount(c => c + 1)
  }
  
  // 渲染
  return (
    <div>
      <h1>{title}</h1>
      <Button onClick={handleClick}>
        Count: {count}
      </Button>
    </div>
  )
}
```

## 🚀 部署

### 部署到 Vercel

```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 部署
vercel
```

### 部署到腾讯云云开发

```bash
# 安装云开发 CLI
npm i -g @cloudbase/cli

# 登录
tcb login

# 部署
tcb hosting deploy dist
```

## 📄 环境变量

创建 `.env.local` 文件:

```env
# API 基础 URL
NEXT_PUBLIC_API_URL=https://api.openclaw.io

# 云开发环境 ID
NEXT_PUBLIC_TCB_ENV_ID=your-env-id
```

## 🤝 贡献指南

1. Fork 项目
2. 创建分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

[MIT](LICENSE)

## 💬 联系我们

- 官网: https://openclaw.io
- 邮箱: contact@openclaw.io
- GitHub: https://github.com/openclaw

---

Made with ❤️ by OpenClaw Team
