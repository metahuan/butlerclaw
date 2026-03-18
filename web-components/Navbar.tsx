// components/layout/Navbar.tsx
'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Menu, X, Download, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  const navLinks = [
    { href: '/', label: '首页' },
    { href: '/skills', label: '技能市场' },
    { href: '/download', label: '下载' },
    { href: '/developer', label: '开发者' },
    { href: '/pricing', label: '价格' },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="text-xl font-bold text-gray-900">OpenClaw Hub</span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-blue-600"
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden items-center gap-3 md:flex">
          <Button variant="ghost" size="sm">
            登录
          </Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
            <Download className="mr-2 h-4 w-4" />
            下载
          </Button>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="rounded-md p-2 text-gray-600 hover:bg-gray-100 md:hidden"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="border-t border-gray-200 bg-white md:hidden">
          <div className="space-y-1 px-4 py-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="block rounded-md px-3 py-2 text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-blue-600"
                onClick={() => setIsOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-4 flex flex-col gap-2 pt-4 border-t border-gray-200">
              <Button variant="outline" className="w-full">
                登录
              </Button>
              <Button className="w-full bg-blue-600 hover:bg-blue-700">
                <Download className="mr-2 h-4 w-4" />
                下载
              </Button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
