// app/page.tsx - 首页
import { Navbar } from '@/components/layout/Navbar';
import { Button } from '@/components/ui/button';
import { SkillCard } from '@/components/skills/SkillCard';
import { Download, ArrowRight, Shield, Zap, Palette, Users } from 'lucide-react';
import Link from 'next/link';

// 模拟热门技能数据
const popularSkills = [
  {
    id: 'skill-vetter',
    name: 'Skill Vetter',
    description: 'Security-first skill vetting tool for OpenClaw',
    icon: '🔐',
    category: '安全',
    downloads: 77200,
    rating: 4.8,
  },
  {
    id: 'playwright-mcp',
    name: 'Playwright MCP',
    description: 'Browser automation with Playwright Model Context Protocol',
    icon: '🎭',
    category: '工具',
    downloads: 20800,
    rating: 4.9,
  },
  {
    id: 'ontology',
    name: 'Ontology',
    description: 'Structured knowledge graph for managing entities',
    icon: '📊',
    category: '效率',
    downloads: 98600,
    rating: 4.6,
  },
  {
    id: 'api-gateway',
    name: 'API Gateway',
    description: 'Connect to 100+ APIs including Google, Microsoft, GitHub',
    icon: '🌐',
    category: '工具',
    downloads: 41300,
    rating: 4.7,
  },
];

const stats = [
  { number: '100K+', label: '用户' },
  { number: '500+', label: '技能' },
  { number: '1M+', label: '下载' },
  { number: '4.9★', label: '评分' },
];

const features = [
  {
    icon: Zap,
    title: '一键安装',
    description: '发现、安装、管理，只需几次点击',
  },
  {
    icon: Shield,
    title: '安全可靠',
    description: '所有技能经过安全审核，放心使用',
  },
  {
    icon: Palette,
    title: '丰富多样',
    description: '500+ 技能，覆盖各种场景需求',
  },
  {
    icon: Users,
    title: '开发者友好',
    description: '上传你的技能，获取收益，共建生态',
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50 to-white px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
            OpenClaw Hub
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-xl text-gray-600">
            你的智能助手，无限可能
          </p>
          <p className="mx-auto mt-2 max-w-2xl text-gray-500">
            发现、安装、管理 OpenClaw 技能，让 AI 助手更强大、更个性化
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
              <Download className="mr-2 h-5 w-5" />
              立即下载 v2.0
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/skills">
                浏览技能市场
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-2 gap-8 border-t border-gray-200 pt-8 sm:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-3xl font-bold text-blue-600">{stat.number}</div>
                <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Popular Skills */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">🔥 热门技能</h2>
            <Link
              href="/skills"
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              查看更多 →
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {popularSkills.map((skill) => (
              <SkillCard key={skill.id} skill={skill} />
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="bg-gray-50 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <h2 className="mb-12 text-center text-2xl font-bold text-gray-900">
            ✨ 为什么选择 OpenClaw Hub
          </h2>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl bg-white p-6 text-center shadow-sm"
              >
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-blue-600">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mt-4 font-semibold text-gray-900">{feature.title}</h3>
                <p className="mt-2 text-sm text-gray-500">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-2xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-12 text-center sm:px-12">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              🚀 开发者入驻
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-blue-100">
              有创意？开发技能，获取收益
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button size="lg" variant="secondary">
                成为开发者
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p className="text-sm text-gray-500">
              © 2026 OpenClaw. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-gray-500">
              <Link href="/about" className="hover:text-gray-900">关于我们</Link>
              <Link href="/terms" className="hover:text-gray-900">使用条款</Link>
              <Link href="/privacy" className="hover:text-gray-900">隐私政策</Link>
              <Link href="/contact" className="hover:text-gray-900">联系我们</Link>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
