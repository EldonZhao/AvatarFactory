// API client for Admin dashboard

const API_BASE_URL = import.meta.env.API_BASE_URL || 'http://127.0.0.1:8000';

interface FetchOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function apiFetch<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Dashboard
export async function getDashboardStats() {
  return apiFetch<DashboardStats>('/api/admin/dashboard');
}

// Personas
export async function getPersonas() {
  return apiFetch<PersonasResponse>('/api/personas/');
}

export async function getPersona(id: string) {
  return apiFetch<PersonaDetail>(`/api/personas/${id}`);
}

export async function createPersona(data: CreatePersonaRequest) {
  return apiFetch<PersonaDetail>('/api/personas/', {
    method: 'POST',
    body: data,
  });
}

export async function deletePersona(id: string) {
  return apiFetch<void>(`/api/personas/${id}`, {
    method: 'DELETE',
  });
}

// Content
export async function getContents(params?: ContentFilters) {
  const searchParams = new URLSearchParams();
  if (params?.persona_id) searchParams.set('persona_id', params.persona_id);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.platform) searchParams.set('platform', params.platform);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return apiFetch<ContentsResponse>(`/api/contents/${query ? `?${query}` : ''}`);
}

export async function getContent(id: string) {
  return apiFetch<ContentDetail>(`/api/contents/${id}`);
}

export async function generateContent(data: GenerateContentRequest) {
  return apiFetch<ContentDetail>('/api/contents/generate', {
    method: 'POST',
    body: data,
  });
}

export async function deleteContent(id: string) {
  return apiFetch<void>(`/api/contents/${id}`, {
    method: 'DELETE',
  });
}

// Scheduler
export async function getSchedulerTasks() {
  return apiFetch<SchedulerTasksResponse>('/api/scheduler/tasks');
}

export async function setupSchedulerTask(personaId: string, data: SetupTaskRequest) {
  return apiFetch<SchedulerTask>(`/api/scheduler/tasks/${personaId}/setup`, {
    method: 'POST',
    body: data,
  });
}

export async function runSchedulerTask(taskId: string) {
  return apiFetch<TaskRunResponse>(`/api/scheduler/tasks/${taskId}/run`, {
    method: 'POST',
  });
}

export async function deleteSchedulerTask(taskId: string) {
  return apiFetch<void>(`/api/scheduler/tasks/${taskId}`, {
    method: 'DELETE',
  });
}

// Topics/Discoveries
export async function getTopics() {
  return apiFetch<TopicsResponse>('/api/discoveries/');
}

// Connectors
export async function getConnectors() {
  return apiFetch<ConnectorsResponse>('/api/connectors/');
}

// Types
export interface DashboardStats {
  personas_count: number;
  contents_count: number;
  tasks_count: number;
  connectors: ConnectorStatus[];
  recent_personas: PersonaSummary[];
}

export interface PersonaSummary {
  id: string;
  name: string;
  description: string;
  platforms: string[];
  content_count?: number;
}

export interface PersonasResponse {
  personas: PersonaSummary[];
}

export interface PersonaDetail {
  id: string;
  name: string;
  description: string;
  platforms: string[];
  voice: string;
  expertise: string[];
  style_guidelines: string[];
  notification_config?: NotificationConfig;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface NotificationConfig {
  enabled: boolean;
  channel?: string;
  webhook_url?: string;
}

export interface CreatePersonaRequest {
  name: string;
  description: string;
  platforms?: string[];
  voice?: string;
  expertise?: string[];
  style_guidelines?: string[];
}

export interface ContentFilters {
  persona_id?: string;
  status?: string;
  platform?: string;
  limit?: number;
}

export interface ContentSummary {
  id: string;
  persona_id: string;
  title: string;
  platform: string;
  status: string;
  created_at: string;
}

export interface ContentsResponse {
  contents: ContentSummary[];
}

export interface ContentDetail {
  id: string;
  persona_id: string;
  title: string;
  body: string;
  platform: string;
  status: string;
  scores?: ContentScores;
  created_at: string;
  updated_at?: string;
}

export interface ContentScores {
  persona_consistency: number;
  platform_fit: number;
  compliance: number;
  engagement_potential: number;
}

export interface GenerateContentRequest {
  persona_id: string;
  topic?: string;
  platform?: string;
}

export interface SchedulerTask {
  id: string;
  persona_id: string;
  task_type: string;
  cron_expression: string;
  enabled: boolean;
  next_run?: string;
  last_run?: string;
}

export interface SchedulerTasksResponse {
  tasks: SchedulerTask[];
}

export interface SetupTaskRequest {
  task_type: string;
  cron_expression: string;
  enabled?: boolean;
}

export interface TaskRunResponse {
  task_id: string;
  status: string;
  message?: string;
}

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

export interface ConnectorStatus {
  platform: string;
  connected: boolean;
  last_checked?: string;
}

export interface ConnectorsResponse {
  connectors: ConnectorStatus[];
}
