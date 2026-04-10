/**
 * Data layer - provides high-level data fetching functions
 * All data is fetched from the FastAPI backend via API calls.
 */

// API base URL - use environment variable or default
// In SSR mode, we need to call the backend directly
const API_BASE_URL = import.meta.env.API_BASE_URL || import.meta.env.ADMIN_API_BASE || 'http://127.0.0.1:8000';

interface FetchOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  cookie?: string; // For SSR - pass cookie header from request
}

async function apiFetch<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Pass cookie for SSR authentication
  if (options.cookie) {
    headers['Cookie'] = options.cookie;
  }

  const response = await fetch(url, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: 'include', // Include cookies for client-side requests
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Dashboard Stats
export interface DashboardData {
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
  recent_personas: Array<{
    id: string;
    name: string;
    tagline?: string;
    description?: string;
    content_count?: number;
  }>;
  connectors: Array<{
    platform: string;
    configured: boolean;
    description?: string;
  }>;
  scheduler_running: boolean;
}

export async function getDashboardData(cookie?: string): Promise<DashboardData> {
  return apiFetch<DashboardData>('/api/admin/dashboard', { cookie });
}

// Personas
export interface PersonaSummary {
  id: string;
  name: string;
  tagline?: string;
  description?: string;
  content_count?: number;
  expertise?: string[];
  avg_score?: number;
}

export interface PersonasResponse {
  personas: PersonaSummary[];
}

export async function getPersonas(cookie?: string): Promise<PersonasResponse> {
  return apiFetch<PersonasResponse>('/api/admin/personas', { cookie });
}

export interface PersonaDetail {
  id: string;
  name: string;
  description: string;
  voice: string;
  expertise: string[];
  style_guidelines: string[];
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export async function getPersona(id: string, cookie?: string): Promise<PersonaDetail> {
  return apiFetch<PersonaDetail>(`/api/admin/personas/${id}`, { cookie });
}

// Content
export interface ContentFilters {
  persona_id?: string;
  status?: string;
  platform?: string;
  limit?: number;
  cookie?: string;
}

export interface ContentSummary {
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

export interface ContentsResponse {
  contents: ContentSummary[];
}

export async function getContents(params?: ContentFilters): Promise<ContentsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.persona_id) searchParams.set('persona_id', params.persona_id);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.platform) searchParams.set('platform', params.platform);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return apiFetch<ContentsResponse>(`/api/admin/content${query ? `?${query}` : ''}`, { cookie: params?.cookie });
}

export interface ContentDetail {
  id: string;
  persona_id: string;
  title: string;
  body: string;
  platform: string;
  status: string;
  scores?: {
    persona_consistency: number;
    platform_fit: number;
    compliance: number;
    engagement_potential: number;
  };
  tags?: string[];
  created_at: string;
  updated_at?: string;
}

export async function getContent(id: string, cookie?: string): Promise<ContentDetail> {
  return apiFetch<ContentDetail>(`/api/admin/content/${id}`, { cookie });
}

// Scheduler
export interface SchedulerTask {
  id: string;
  persona_id: string;
  name?: string;
  task_type: string;
  cron_expression: string;
  enabled: boolean;
  next_run?: string;
  last_run?: string;
  last_status?: 'success' | 'error' | null;
  last_error?: string | null;
  run_count?: number;
}

export interface SchedulerTasksResponse {
  tasks: SchedulerTask[];
}

export async function getSchedulerTasks(cookie?: string): Promise<SchedulerTasksResponse> {
  return apiFetch<SchedulerTasksResponse>('/api/admin/scheduler/tasks', { cookie });
}

// Topics/Discoveries
export interface TopicSummary {
  id: string;
  persona_id: string;
  title: string;
  source: string;
  discovered_at: string;
}

export interface TopicsResponse {
  discoveries: TopicSummary[];
}

export async function getTopics(cookie?: string): Promise<TopicsResponse> {
  return apiFetch<TopicsResponse>('/api/admin/topics', { cookie });
}

// Connectors
export interface ConnectorStatus {
  platform: string;
  configured: boolean;
  connected?: boolean;
  description?: string;
  last_checked?: string;
}

export interface ConnectorsResponse {
  connectors: ConnectorStatus[];
}

export async function getConnectors(cookie?: string): Promise<ConnectorsResponse> {
  return apiFetch<ConnectorsResponse>('/api/admin/connectors', { cookie });
}

// Statistics Types and Functions
export interface PersonaStats {
  persona_id: string;
  total_content: number;
  published_content: number;
  draft_content: number;
  avg_review_score: number;
  content_by_pillar: Record<string, number>;
  content_by_platform: Record<string, number>;
  score_distribution: {
    persona_consistency: number;
    platform_fit: number;
    compliance: number;
    engagement_potential: number;
  };
}

export interface GlobalStats {
  total_personas: number;
  total_content: number;
  total_published: number;
  total_drafts: number;
  avg_review_score: number;
  active_tasks: number;
  content_by_day: { date: string; count: number }[];
  personas_stats: PersonaStats[];
}

// Chronicle API base URL (no auth required)
const CHRONICLE_API_BASE = import.meta.env.API_BASE_URL || import.meta.env.ADMIN_API_BASE || 'http://127.0.0.1:8000';

async function chronicleFetch<T>(endpoint: string): Promise<T> {
  const url = `${CHRONICLE_API_BASE}/api/chronicle${endpoint}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Chronicle API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function getGlobalStats(): Promise<GlobalStats> {
  const stats = await chronicleFetch<GlobalStats>('/stats');
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

export async function getPersonaStats(id: string): Promise<PersonaStats> {
  const stats = await chronicleFetch<PersonaStats>(`/personas/${id}/stats`);
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

export interface Persona {
  id: string;
  version: string;
  created_at: string | null;
  updated_at: string | null;
  identity: {
    name: string;
    tagline: string;
    expertise: string[];
  };
  target_audience: {
    primary: string;
    pain_points: string[];
    goals: string[];
  };
  voice_style: {
    tone: string;
    language_patterns: string[];
    emoji_usage: string;
  };
  content_pillars: Array<{
    name: string;
    description: string;
    frequency: string;
    examples: string[];
  }>;
  boundaries: {
    avoid: string[];
    compliance: string[];
  };
}

export async function getAllPersonas(): Promise<Persona[]> {
  const response = await chronicleFetch<{ count: number; personas: Persona[] }>('/personas');
  return response?.personas || [];
}
