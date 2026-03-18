// components/skills/SkillCard.tsx
'use client';

import Link from 'next/link';
import { Download, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';

interface Skill {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  downloads: number;
  rating: number;
  installed?: boolean;
}

interface SkillCardProps {
  skill: Skill;
}

export function SkillCard({ skill }: SkillCardProps) {
  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return num.toString();
  };

  return (
    <Card className="group overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-lg">
      <CardContent className="p-5">
        {/* Icon & Name */}
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-50 to-blue-100 text-2xl">
            {skill.icon}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-semibold text-gray-900 group-hover:text-blue-600">
              {skill.name}
            </h3>
            <Badge variant="secondary" className="mt-1 text-xs">
              {skill.category}
            </Badge>
          </div>
        </div>

        {/* Description */}
        <p className="mt-3 line-clamp-2 text-sm text-gray-600">
          {skill.description}
        </p>

        {/* Stats */}
        <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-1">
            <Download className="h-4 w-4" />
            <span>{formatNumber(skill.downloads)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
            <span>{skill.rating}</span>
          </div>
        </div>

        {/* Action */}
        <div className="mt-4">
          {skill.installed ? (
            <Button variant="outline" className="w-full" disabled>
              已安装
            </Button>
          ) : (
            <Button className="w-full bg-blue-600 hover:bg-blue-700">
              安装
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
