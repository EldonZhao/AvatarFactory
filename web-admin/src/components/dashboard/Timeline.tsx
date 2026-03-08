'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatDate, cn } from '@/lib/utils';

interface TimelineEvent {
  id: string;
  type: 'persona_created' | 'persona_updated' | 'content_created' | 'content_published' | 'review_completed' | 'task_scheduled' | 'task_executed';
  timestamp: string;
  title: string;
  description: string;
  persona_id?: string;
  content_id?: string;
  metadata?: Record<string, unknown>;
}

interface TimelineProps {
  events: TimelineEvent[];
  title?: string;
  maxItems?: number;
  baseUrl?: string;
}

export function Timeline({ events, title = '时间线', maxItems, baseUrl = '' }: TimelineProps) {
  const displayEvents = maxItems ? events.slice(0, maxItems) : events;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {displayEvents.length === 0 ? (
          <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">暂无事件</p>
        ) : (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-[hsl(var(--border))]" />

            <div className="space-y-4">
              {displayEvents.map((event, index) => (
                <TimelineItem key={event.id} event={event} index={index} baseUrl={baseUrl} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface TimelineItemProps {
  event: TimelineEvent;
  index: number;
  baseUrl?: string;
}

function TimelineItem({ event, index, baseUrl = '' }: TimelineItemProps) {
  const getEventIcon = () => {
    switch (event.type) {
      case 'persona_created':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
        );
      case 'persona_updated':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case 'content_created':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        );
      case 'content_published':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'review_completed':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'task_executed':
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      default:
        return (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const getEventColor = () => {
    switch (event.type) {
      case 'persona_created':
        return 'bg-purple-500';
      case 'persona_updated':
        return 'bg-blue-500';
      case 'content_created':
        return 'bg-yellow-500';
      case 'content_published':
        return 'bg-green-500';
      case 'review_completed':
        return 'bg-cyan-500';
      case 'task_executed':
        return 'bg-orange-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getEventBadge = () => {
    switch (event.type) {
      case 'persona_created':
        return <Badge variant="secondary">人设创建</Badge>;
      case 'persona_updated':
        return <Badge variant="info">人设更新</Badge>;
      case 'content_created':
        return <Badge variant="warning">草稿</Badge>;
      case 'content_published':
        return <Badge variant="success">发布</Badge>;
      case 'review_completed':
        return <Badge variant="info">审核</Badge>;
      case 'task_executed':
        return <Badge variant={event.metadata?.status === 'success' ? 'success' : 'destructive'}>任务</Badge>;
      default:
        return <Badge variant="secondary">事件</Badge>;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="relative pl-8"
    >
      {/* Timeline dot */}
      <div className={cn('absolute left-0 top-1.5 w-6 h-6 rounded-full flex items-center justify-center text-white', getEventColor())}>
        {getEventIcon()}
      </div>

      <div className="p-3 rounded-lg bg-[hsl(var(--muted))] hover:bg-[hsl(var(--accent))] transition-colors">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            {getEventBadge()}
            <span className="font-medium text-sm">{event.title}</span>
          </div>
          <span className="text-xs text-[hsl(var(--muted-foreground))]">
            {formatDate(event.timestamp, 'relative')}
          </span>
        </div>
        <p className="text-sm text-[hsl(var(--muted-foreground))] line-clamp-2">
          {event.description}
        </p>
        {event.content_id && (
          <a
            href={`${baseUrl}/contents/${event.content_id}`}
            className="inline-block mt-1 text-xs text-[hsl(var(--primary))] hover:underline"
          >
            查看内容 →
          </a>
        )}
      </div>
    </motion.div>
  );
}
