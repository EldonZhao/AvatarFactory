import type { TimelineEvent, GlobalStats } from '../types';
import { getAllPersonas, getPersonaHistory } from './personas';
import { getAllContent, getReviewsForPersona } from './content';
import { getAllTasks } from './scheduler';
import { getPersonaStats } from './stats';

export function getTimelineEvents(personaId?: string, limit: number = 50): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  const personas = personaId ? [{ id: personaId }] : getAllPersonas();

  for (const persona of personas) {
    const id = 'id' in persona ? persona.id : (persona as { id: string }).id;

    // Add persona creation/update events from history
    const history = getPersonaHistory(id);
    for (const version of history) {
      events.push({
        id: `${id}-${version.version}`,
        type: version.version === 'v1.0' ? 'persona_created' : 'persona_updated',
        timestamp: version.timestamp,
        title: version.version === 'v1.0' ? '创建人设' : `更新至 ${version.version}`,
        description: version.changes.join(', '),
        persona_id: id,
        metadata: { reason: version.reason, author: version.author }
      });
    }

    // Add content events
    const contents = getAllContent().filter(c => c.persona_id === id);
    for (const content of contents) {
      events.push({
        id: `content-${content.id}`,
        type: content.status === 'published' ? 'content_published' : 'content_created',
        timestamp: content.created_at,
        title: content.status === 'published' ? '发布内容' : '创建草稿',
        description: content.title,
        persona_id: id,
        content_id: content.id,
        metadata: { platform: content.platform, pillar: content.pillar }
      });
    }

    // Add review events
    const reviews = getReviewsForPersona(id);
    for (const review of reviews) {
      events.push({
        id: `review-${review.content_id}`,
        type: 'review_completed',
        timestamp: review.reviewed_at,
        title: '审核完成',
        description: `评分: ${review.overall_score}`,
        persona_id: id,
        content_id: review.content_id,
        metadata: { score: review.overall_score }
      });
    }
  }

  // Add task events
  const tasks = getAllTasks();
  for (const task of tasks) {
    if (task.last_run && (!personaId || task.persona_id === personaId)) {
      events.push({
        id: `task-${task.id}-${task.last_run}`,
        type: 'task_executed',
        timestamp: task.last_run,
        title: `执行任务: ${task.name}`,
        description: task.last_status === 'success' ? '成功' : `失败: ${task.last_error}`,
        persona_id: task.persona_id || undefined,
        metadata: { task_type: task.task_type, status: task.last_status }
      });
    }
  }

  // Sort by timestamp descending and limit
  return events
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, limit);
}

export function getGlobalStats(): GlobalStats {
  const personas = getAllPersonas();
  const allContent = getAllContent();
  const tasks = getAllTasks();

  const published = allContent.filter(c => c.status === 'published');
  const drafts = allContent.filter(c => c.status === 'draft');

  // Calculate average score
  let totalScore = 0;
  let scoreCount = 0;
  for (const content of allContent) {
    if (content.review_score) {
      totalScore += content.review_score;
      scoreCount++;
    }
  }

  // Content by day (last 30 days)
  const contentByDay: Record<string, number> = {};
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    contentByDay[dateStr] = 0;
  }

  for (const content of allContent) {
    const dateStr = new Date(content.created_at).toISOString().split('T')[0];
    if (dateStr in contentByDay) {
      contentByDay[dateStr]++;
    }
  }

  // Get stats for each persona
  const personasStats = personas.map(p => getPersonaStats(p.id));

  return {
    total_personas: personas.length,
    total_content: allContent.length,
    total_published: published.length,
    total_drafts: drafts.length,
    avg_review_score: scoreCount > 0 ? Math.round(totalScore / scoreCount) : 0,
    active_tasks: tasks.filter(t => t.enabled).length,
    content_by_day: Object.entries(contentByDay).map(([date, count]) => ({ date, count })),
    personas_stats: personasStats
  };
}
