'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ScoreBadge } from '../ui/Score';
import { cn, formatDate, truncate, getPlatformColor, getPlatformName } from '@/lib/utils';
import type { Content } from '@/lib/types';

interface ContentCardProps {
  content: Content;
  index?: number;
  showPersona?: boolean;
}

export function ContentCard({ content, index = 0, showPersona = false }: ContentCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
    >
      <a href={`/content/${content.id}`}>
        <Card hover className="h-full">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn('w-2 h-2 rounded-full', getPlatformColor(content.platform))} />
                  <span className="text-xs text-[hsl(var(--muted-foreground))]">
                    {getPlatformName(content.platform)}
                  </span>
                  <Badge variant={content.status === 'published' ? 'success' : 'secondary'} className="text-xs">
                    {content.status === 'published' ? '已发布' : '草稿'}
                  </Badge>
                </div>
                <h3 className="font-semibold text-[hsl(var(--foreground))] line-clamp-2">
                  {content.title}
                </h3>
              </div>
              {content.review_score && (
                <ScoreBadge score={content.review_score} size="sm" />
              )}
            </div>
          </CardHeader>

          <CardContent>
            <p className="text-sm text-[hsl(var(--muted-foreground))] line-clamp-3 mb-3">
              {truncate(content.body.replace(/[#*`]/g, '').replace(/\n+/g, ' '), 150)}
            </p>

            <div className="flex items-center justify-between">
              <div className="flex flex-wrap gap-1">
                {content.tags.slice(0, 2).map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {content.tags.length > 2 && (
                  <Badge variant="outline" className="text-xs">
                    +{content.tags.length - 2}
                  </Badge>
                )}
              </div>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                {formatDate(content.created_at, 'relative')}
              </span>
            </div>
          </CardContent>
        </Card>
      </a>
    </motion.div>
  );
}

interface ContentListProps {
  contents: Content[];
  emptyMessage?: string;
}

export function ContentList({ contents, emptyMessage = '暂无内容' }: ContentListProps) {
  if (contents.length === 0) {
    return (
      <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {contents.map((content, index) => (
        <ContentCard key={content.id} content={content} index={index} />
      ))}
    </div>
  );
}
