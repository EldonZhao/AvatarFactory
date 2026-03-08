'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { cn, formatDate, truncate, getPlatformColor, getPlatformName } from '@/lib/utils';

interface ContentSummary {
  id: string;
  persona_id: string;
  title: string;
  body?: string;
  platform: string;
  status: string;
  created_at: string;
  review_score?: number;
  tags?: string[];
}

interface ContentCardProps {
  content: ContentSummary;
  index?: number;
  baseUrl?: string;
  showPersona?: boolean;
}

export function ContentCard({ content, index = 0, baseUrl = '', showPersona = false }: ContentCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
    >
      <a href={`${baseUrl}/contents/${content.id}`}>
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
              {content.review_score !== undefined && content.review_score > 0 && (
                <div className={cn(
                  'px-2 py-0.5 text-xs rounded-lg border font-bold',
                  content.review_score >= 90 ? 'bg-green-500/10 border-green-500/20 text-green-500' :
                  content.review_score >= 75 ? 'bg-blue-500/10 border-blue-500/20 text-blue-500' :
                  content.review_score >= 60 ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500' :
                  'bg-red-500/10 border-red-500/20 text-red-500'
                )}>
                  {content.review_score}
                </div>
              )}
            </div>
          </CardHeader>

          <CardContent>
            {content.body && (
              <p className="text-sm text-[hsl(var(--muted-foreground))] line-clamp-3 mb-3">
                {truncate(content.body.replace(/[#*`]/g, '').replace(/\n+/g, ' '), 150)}
              </p>
            )}

            <div className="flex items-center justify-between">
              <div className="flex flex-wrap gap-1">
                {content.tags && content.tags.slice(0, 2).map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    {tag}
                  </Badge>
                ))}
                {content.tags && content.tags.length > 2 && (
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
  contents: ContentSummary[];
  baseUrl?: string;
  emptyMessage?: string;
}

export function ContentList({ contents, baseUrl = '', emptyMessage = '暂无内容' }: ContentListProps) {
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
        <ContentCard key={content.id} content={content} index={index} baseUrl={baseUrl} />
      ))}
    </div>
  );
}
