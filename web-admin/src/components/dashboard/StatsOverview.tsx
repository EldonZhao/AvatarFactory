'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '../ui/Card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  index?: number;
  color?: string;
  href?: string;
}

export function StatCard({ title, value, subtitle, icon, trend, index = 0, color = 'blue', href }: StatCardProps) {
  const colors: Record<string, string> = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    purple: 'from-purple-500 to-purple-600',
    orange: 'from-orange-500 to-orange-600',
    cyan: 'from-cyan-500 to-cyan-600',
    pink: 'from-pink-500 to-pink-600',
  };

  const content = (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
    >
      <Card className="overflow-hidden" hover={!!href}>
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-[hsl(var(--muted-foreground))] mb-1">{title}</p>
              <p className="text-3xl font-bold text-[hsl(var(--foreground))]">{value}</p>
              {subtitle && (
                <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">{subtitle}</p>
              )}
              {trend && (
                <div className={cn('flex items-center gap-1 mt-2 text-xs', trend.isPositive ? 'text-green-500' : 'text-red-500')}>
                  {trend.isPositive ? (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                    </svg>
                  ) : (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  )}
                  <span>{trend.value}%</span>
                </div>
              )}
            </div>
            <div className={cn('w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center text-white shadow-lg', colors[color])}>
              {icon}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );

  if (href) {
    return <a href={href}>{content}</a>;
  }
  return content;
}

interface StatsOverviewProps {
  stats: {
    personas_count: number;
    contents_count: number;
    draft_count: number;
    published_count: number;
    tasks_count: number;
    active_tasks_count: number;
    connectors_configured: number;
    connectors_total: number;
  };
  baseUrl?: string;
}

export function StatsOverview({ stats, baseUrl = '' }: StatsOverviewProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <StatCard
        title="Persona 数量"
        value={stats.personas_count}
        href={`${baseUrl}/personas`}
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        }
        index={0}
        color="purple"
      />
      <StatCard
        title="内容总数"
        value={stats.contents_count}
        subtitle={`${stats.draft_count} 草稿 · ${stats.published_count} 已发布`}
        href={`${baseUrl}/content`}
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        }
        index={1}
        color="blue"
      />
      <StatCard
        title="已发布"
        value={stats.published_count}
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        }
        index={2}
        color="green"
      />
      <StatCard
        title="草稿"
        value={stats.draft_count}
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        }
        index={3}
        color="orange"
      />
      <StatCard
        title="调度任务"
        value={stats.tasks_count}
        subtitle={`${stats.active_tasks_count} 活跃`}
        href={`${baseUrl}/scheduler`}
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        index={4}
        color="cyan"
      />
      <StatCard
        title="连接器"
        value={`${stats.connectors_configured}/${stats.connectors_total}`}
        subtitle="平台已配置"
        icon={
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        }
        index={5}
        color="pink"
      />
    </div>
  );
}
