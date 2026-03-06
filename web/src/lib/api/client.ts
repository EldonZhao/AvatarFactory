/**
 * API Client for Chronicle SSR
 *
 * Fetches data from the FastAPI backend for server-side rendering.
 */

import type {
  Persona,
  PersonaVersion,
  PersonaStats,
  Content,
  ReviewReport,
  ScheduledTask,
  TimelineEvent,
  GlobalStats,
} from '../types';

// API base URL - defaults to localhost:8000 for local development
// In Docker, this is set to the internal FastAPI URL
const API_BASE = import.meta.env.API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch function with error handling
 */
async function fetchAPI<T>(endpoint: string): Promise<T> {
  const url = `${API_BASE}/api/chronicle${endpoint}`;

  try {
    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!res.ok) {
      if (res.status === 404) {
        return null as T;
      }
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }

    return res.json();
  } catch (error) {
    console.error(`Failed to fetch ${url}:`, error);
    throw error;
  }
}

// =============================================================================
// Persona Functions
// =============================================================================

/**
 * Get all personas
 */
export async function getAllPersonas(): Promise<Persona[]> {
  const response = await fetchAPI<{ count: number; personas: Persona[] }>('/personas');
  return response?.personas || [];
}

/**
 * Get all persona IDs (for SSR path generation)
 */
export async function getAllPersonaIds(): Promise<string[]> {
  const ids = await fetchAPI<string[]>('/personas/ids');
  return ids || [];
}

/**
 * Get a single persona by ID
 */
export async function getPersona(id: string): Promise<Persona | null> {
  return fetchAPI<Persona | null>(`/personas/${id}`);
}

/**
 * Get persona version history
 */
export async function getPersonaHistory(id: string): Promise<PersonaVersion[]> {
  const history = await fetchAPI<PersonaVersion[]>(`/personas/${id}/history`);
  return history || [];
}

/**
 * Get available version IDs for a persona
 */
export async function getPersonaVersions(id: string): Promise<string[]> {
  const versions = await fetchAPI<string[]>(`/personas/${id}/versions`);
  return versions || [];
}

/**
 * Get persona statistics
 */
export async function getPersonaStats(id: string): Promise<PersonaStats> {
  const stats = await fetchAPI<PersonaStats>(`/personas/${id}/stats`);
  return stats || {
    persona_id: id,
    total_content: 0,
    published_content: 0,
    draft_content: 0,
    avg_review_score: 0,
    content_by_pillar: {},
    content_by_platform: {},
    score_distribution: {
      persona_consistency: 0,
      platform_fit: 0,
      compliance: 0,
      engagement_potential: 0,
    },
  };
}

// =============================================================================
// Content Functions
// =============================================================================

/**
 * Get all content across all personas
 */
export async function getAllContent(): Promise<Content[]> {
  const content = await fetchAPI<Content[]>('/content');
  return content || [];
}

/**
 * Get all content IDs (for SSR path generation)
 */
export async function getAllContentIds(): Promise<string[]> {
  const ids = await fetchAPI<string[]>('/content/ids');
  return ids || [];
}

/**
 * Get recent content
 */
export async function getRecentContent(limit: number = 10): Promise<Content[]> {
  const content = await fetchAPI<Content[]>(`/content/recent?limit=${limit}`);
  return content || [];
}

/**
 * Get a single content item by ID
 */
export async function getContent(contentId: string): Promise<Content | null> {
  return fetchAPI<Content | null>(`/content/${contentId}`);
}

/**
 * Get content by persona
 */
export async function getContentByPersona(personaId: string): Promise<Content[]> {
  const content = await fetchAPI<Content[]>(`/personas/${personaId}/content`);
  return content || [];
}

/**
 * Get review for a content item
 */
export async function getReview(contentId: string): Promise<ReviewReport | null> {
  return fetchAPI<ReviewReport | null>(`/content/${contentId}/review`);
}

/**
 * Get all reviews for a persona
 */
export async function getReviewsForPersona(personaId: string): Promise<ReviewReport[]> {
  // Fetch content for persona, then fetch reviews for each
  const contents = await getContentByPersona(personaId);
  const reviews: ReviewReport[] = [];

  for (const content of contents) {
    const review = await getReview(content.id);
    if (review) {
      reviews.push(review);
    }
  }

  // Sort by reviewed_at descending
  return reviews.sort((a, b) =>
    new Date(b.reviewed_at).getTime() - new Date(a.reviewed_at).getTime()
  );
}

// =============================================================================
// Scheduler Functions
// =============================================================================

/**
 * Get all scheduled tasks
 */
export async function getAllTasks(): Promise<ScheduledTask[]> {
  const tasks = await fetchAPI<ScheduledTask[]>('/scheduler/tasks');
  return tasks || [];
}

/**
 * Get a single task by ID
 */
export async function getTask(taskId: string): Promise<ScheduledTask | null> {
  return fetchAPI<ScheduledTask | null>(`/scheduler/tasks/${taskId}`);
}

/**
 * Get tasks by persona
 */
export async function getTasksByPersona(personaId: string): Promise<ScheduledTask[]> {
  const tasks = await fetchAPI<ScheduledTask[]>(`/scheduler/tasks/by-persona/${personaId}`);
  return tasks || [];
}

/**
 * Get active (enabled) tasks
 */
export async function getActiveTasks(): Promise<ScheduledTask[]> {
  const tasks = await fetchAPI<ScheduledTask[]>('/scheduler/tasks/active');
  return tasks || [];
}

/**
 * Get scheduler statistics
 */
export async function getTaskStats(): Promise<{
  total: number;
  active: number;
  byType: Record<string, number>;
  successRate: number;
}> {
  const stats = await fetchAPI<{
    total: number;
    active: number;
    byType: Record<string, number>;
    successRate: number;
  }>('/scheduler/stats');

  return stats || {
    total: 0,
    active: 0,
    byType: {},
    successRate: 0,
  };
}

// =============================================================================
// Timeline & Stats Functions
// =============================================================================

/**
 * Get timeline events
 */
export async function getTimelineEvents(
  personaId?: string,
  limit: number = 50
): Promise<TimelineEvent[]> {
  const params = new URLSearchParams();
  if (personaId) params.set('persona_id', personaId);
  params.set('limit', String(limit));

  const events = await fetchAPI<TimelineEvent[]>(`/timeline?${params.toString()}`);
  return events || [];
}

/**
 * Get global statistics
 */
export async function getGlobalStats(): Promise<GlobalStats> {
  const stats = await fetchAPI<GlobalStats>('/stats');
  return stats || {
    total_personas: 0,
    total_content: 0,
    total_published: 0,
    total_drafts: 0,
    avg_review_score: 0,
    active_tasks: 0,
    content_by_day: [],
    personas_stats: [],
  };
}

// =============================================================================
// Dashboard (Optimized - Single API call)
// =============================================================================

/**
 * Dashboard data structure
 */
export interface DashboardData {
  personas: Array<{
    persona: Persona;
    stats: PersonaStats;
  }>;
  recentContent: Content[];
  timeline: TimelineEvent[];
  tasks: ScheduledTask[];
  stats: GlobalStats;
}

/**
 * Get all dashboard data in a single API call
 *
 * This is the optimized endpoint that combines:
 * - Personas with stats
 * - Recent content
 * - Timeline events
 * - Active tasks
 * - Global stats
 */
export async function getDashboardData(): Promise<DashboardData> {
  const data = await fetchAPI<DashboardData>('/dashboard');
  return data || {
    personas: [],
    recentContent: [],
    timeline: [],
    tasks: [],
    stats: {
      total_personas: 0,
      total_content: 0,
      total_published: 0,
      total_drafts: 0,
      avg_review_score: 0,
      active_tasks: 0,
      content_by_day: [],
      personas_stats: [],
    },
  };
}
