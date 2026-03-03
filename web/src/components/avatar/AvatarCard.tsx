'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ScoreBadge } from '../ui/Score';
import { cn, getPlatformColor, getPlatformName, buildUrl } from '@/lib/utils';
import type { Persona, PersonaStats } from '@/lib/types';

interface AvatarCardProps {
  persona: Persona;
  stats?: PersonaStats;
  index?: number;
}

export function AvatarCard({ persona, stats, index = 0 }: AvatarCardProps) {
  const initials = persona.identity.name.slice(0, 2);
  const gradientColors = [
    'from-blue-500 to-purple-600',
    'from-green-500 to-teal-600',
    'from-orange-500 to-red-600',
    'from-pink-500 to-rose-600',
    'from-cyan-500 to-blue-600',
    'from-violet-500 to-purple-600',
  ];
  const gradient = gradientColors[index % gradientColors.length];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
    >
      <a href={buildUrl(`/avatars/${persona.id}`)}>
        <Card hover className="h-full">
          <CardHeader className="pb-3">
            <div className="flex items-start gap-4">
              {/* Avatar */}
              <div className={cn('w-14 h-14 rounded-xl bg-gradient-to-br flex items-center justify-center text-white font-bold text-lg shadow-lg', gradient)}>
                {initials}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-[hsl(var(--foreground))] truncate">
                  {persona.identity.name}
                </h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] line-clamp-1 mt-0.5">
                  {persona.identity.tagline}
                </p>

                {/* Platforms */}
                <div className="flex gap-1.5 mt-2">
                  {persona.platforms.map((platform) => (
                    <span
                      key={platform}
                      className={cn('w-2 h-2 rounded-full', getPlatformColor(platform))}
                      title={getPlatformName(platform)}
                    />
                  ))}
                </div>
              </div>

              {/* Score */}
              {stats && stats.avg_review_score > 0 && (
                <ScoreBadge score={stats.avg_review_score} size="sm" />
              )}
            </div>
          </CardHeader>

          <CardContent>
            {/* Expertise */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              {persona.identity.expertise.slice(0, 3).map((exp) => (
                <Badge key={exp} variant="secondary" className="text-xs">
                  {exp}
                </Badge>
              ))}
            </div>

            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-lg bg-[hsl(var(--muted))]">
                  <div className="text-lg font-bold text-[hsl(var(--foreground))]">{stats.total_content}</div>
                  <div className="text-xs text-[hsl(var(--muted-foreground))]">内容</div>
                </div>
                <div className="p-2 rounded-lg bg-[hsl(var(--muted))]">
                  <div className="text-lg font-bold text-green-500">{stats.published_content}</div>
                  <div className="text-xs text-[hsl(var(--muted-foreground))]">已发布</div>
                </div>
                <div className="p-2 rounded-lg bg-[hsl(var(--muted))]">
                  <div className="text-lg font-bold text-yellow-500">{stats.draft_content}</div>
                  <div className="text-xs text-[hsl(var(--muted-foreground))]">草稿</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </a>
    </motion.div>
  );
}
