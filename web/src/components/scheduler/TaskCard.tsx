'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import cronstrue from 'cronstrue';
import { formatDate, cn } from '@/lib/utils';
import type { ScheduledTask } from '@/lib/types';

interface TaskCardProps {
  task: ScheduledTask;
  index?: number;
}

export function TaskCard({ task, index = 0 }: TaskCardProps) {
  let scheduleDesc = task.schedule;
  try {
    scheduleDesc = cronstrue.toString(task.schedule, { locale: 'zh_CN', use24HourTimeFormat: true });
  } catch {
    // Keep original if parsing fails
  }

  const getTypeIcon = () => {
    switch (task.task_type) {
      case 'discovery':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        );
      case 'content':
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
    }
  };

  const getTypeColor = () => {
    switch (task.task_type) {
      case 'discovery':
        return 'from-blue-500 to-blue-600';
      case 'content':
        return 'from-green-500 to-green-600';
      default:
        return 'from-purple-500 to-purple-600';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
    >
      <Card hover>
        <CardContent className="p-4">
          <div className="flex items-start gap-4">
            <div className={cn('w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center text-white', getTypeColor())}>
              {getTypeIcon()}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-medium truncate">{task.name}</h3>
                <Badge variant={task.enabled ? 'success' : 'secondary'}>
                  {task.enabled ? '启用' : '禁用'}
                </Badge>
              </div>

              <p className="text-sm text-[hsl(var(--muted-foreground))] mb-2">{scheduleDesc}</p>

              <div className="flex items-center gap-3 text-xs text-[hsl(var(--muted-foreground))]">
                <span>运行 {task.run_count} 次</span>
                {task.last_run && (
                  <span>上次: {formatDate(task.last_run, 'relative')}</span>
                )}
                {task.last_status && (
                  <Badge
                    variant={task.last_status === 'success' ? 'success' : 'destructive'}
                    className="text-xs"
                  >
                    {task.last_status === 'success' ? '成功' : '失败'}
                  </Badge>
                )}
              </div>

              {task.last_error && (
                <p className="text-xs text-red-500 mt-1 truncate">{task.last_error}</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

interface TaskListProps {
  tasks: ScheduledTask[];
  title?: string;
}

export function TaskList({ tasks, title = '调度任务' }: TaskListProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {tasks.length === 0 ? (
          <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">暂无任务</p>
        ) : (
          <div className="space-y-3">
            {tasks.map((task, index) => (
              <TaskCard key={task.id} task={task} index={index} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
