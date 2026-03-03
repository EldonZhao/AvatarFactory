import * as fs from 'node:fs';
import * as path from 'node:path';
import type { ScheduledTask } from '../types';

const KNOWLEDGE_BASE_PATH = process.env.KNOWLEDGE_BASE_PATH || path.resolve(process.cwd(), '../knowledges');

function getSchedulerDir(): string {
  return path.join(KNOWLEDGE_BASE_PATH, 'scheduler');
}

export function getAllTasks(): ScheduledTask[] {
  const tasksPath = path.join(getSchedulerDir(), 'tasks.json');
  if (!fs.existsSync(tasksPath)) {
    return [];
  }
  try {
    const content = fs.readFileSync(tasksPath, 'utf-8');
    return JSON.parse(content) as ScheduledTask[];
  } catch {
    return [];
  }
}

export function getTask(taskId: string): ScheduledTask | null {
  const tasks = getAllTasks();
  return tasks.find(t => t.id === taskId) || null;
}

export function getTasksByPersona(personaId: string): ScheduledTask[] {
  return getAllTasks().filter(t => t.persona_id === personaId);
}

export function getActiveTasks(): ScheduledTask[] {
  return getAllTasks().filter(t => t.enabled);
}

export function getTaskStats(): {
  total: number;
  active: number;
  byType: Record<string, number>;
  successRate: number;
} {
  const tasks = getAllTasks();
  const active = tasks.filter(t => t.enabled);

  const byType: Record<string, number> = {};
  let successCount = 0;
  let totalRuns = 0;

  for (const task of tasks) {
    byType[task.task_type] = (byType[task.task_type] || 0) + 1;
    if (task.run_count > 0) {
      totalRuns += task.run_count;
      if (task.last_status === 'success') {
        successCount += task.run_count;
      }
    }
  }

  return {
    total: tasks.length,
    active: active.length,
    byType,
    successRate: totalRuns > 0 ? Math.round((successCount / totalRuns) * 100) : 0
  };
}
