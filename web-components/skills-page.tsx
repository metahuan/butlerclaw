// app/skills/page.tsx - 技能市场页
'use client';

import { useState } from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { SkillCard } from '@/components/skills/SkillCard';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, SlidersHorizontal } from 'lucide-react';

// 模拟技能数据
const allSkills = [
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
  {
    id: 'brave-search',
    name: 'Brave Search',
    description: 'AI-optimized web search via Brave Search API',
    icon: '🔍',
    category: '工具',
    downloads: 37300,
    rating: 4.5,
  },
  {
    id: 'summarize',
    name: 'Summarize',
    description: 'Summarize text/transcripts from URLs and files',
    icon: '📝',
    category: '效率',
    downloads: 143000,
    rating: 4.8,
  },
];

const categories = ['全部', '工具', '安全', '效率', '开发', '媒体'];
const sortOptions = ['下载量', '评分', '最新', '名称'];

export default function SkillsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('全部');
  const [selectedSort, setSelectedSort] = useState('下载量');

  // 过滤技能
  const filteredSkills = allSkills.filter((skill) => {
    const matchesSearch =
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === '全部' || skill.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">技能市场</h1>
          <p className="mt-2 text-gray-600">
            发现 500+ 实用技能，提升你的 AI 助手
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="sticky top-16 z-40 bg-white border-b border-gray-200 shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <Input
                type="text"
                placeholder="搜索技能..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Categories */}
              <div className="flex flex-wrap gap-1">
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                      selectedCategory === category
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>

              {/* Sort */}
              <div className="flex items-center gap-2 ml-4">
                <SlidersHorizontal className="h-4 w-4 text-gray-400" />
                <select
                  value={selectedSort}
                  onChange={(e) => setSelectedSort(e.target.value)}
                  className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm focus:border-blue-500 focus:outline-none"
                >
                  {sortOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Skills Grid */}
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            全部技能 ({filteredSkills.length})
          </h2>
          <Button variant="outline" size="sm">
            批量操作
          </Button>
        </div>

        {filteredSkills.length > 0 ? (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredSkills.map((skill) => (
              <SkillCard key={skill.id} skill={skill} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-lg font-medium text-gray-900">没有找到相关技能</h3>
            <p className="mt-1 text-gray-500">尝试调整搜索词或筛选条件</p>
          </div>
        )}

        {/* Pagination */}
        {filteredSkills.length > 0 && (
          <div className="mt-8 flex items-center justify-center gap-2">
            <Button variant="outline" size="sm" disabled>
              上一页
            </Button>
            <Button variant="outline" size="sm" className="bg-blue-600 text-white">
              1
            </Button>
            <Button variant="outline" size="sm">
              2
            </Button>
            <Button variant="outline" size="sm">
              3
            </Button>
            <span className="text-gray-400">...</span>
            <Button variant="outline" size="sm">
              10
            </Button>
            <Button variant="outline" size="sm">
              下一页
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
