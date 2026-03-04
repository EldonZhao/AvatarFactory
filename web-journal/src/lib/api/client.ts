/**
 * API Client for Journal SSR
 *
 * Fetches timeline events and data from the FastAPI backend.
 */

import type {
  TimelineEvent,
  PersonaSummary,
  ContentSummary,
  JournalStats,
} from '../types';

// API base URL - defaults to localhost:8000 for local development
const API_BASE = import.meta.env.API_BASE_URL || 'http://localhost:8000';

/**
 * Generic fetch function with error handling
 */
async function fetchAPI<T>(endpoint: string): Promise<T> {
  const url = `${API_BASE}/api/journal${endpoint}`;

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
// Timeline Functions
// =============================================================================

/**
 * Get all timeline events (paginated)
 */
export async function getTimelineEvents(
  page: number = 1,
  limit: number = 20
): Promise<{ events: TimelineEvent[]; total: number; page: number; pages: number }> {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('limit', String(limit));

  const response = await fetchAPI<{
    events: TimelineEvent[];
    total: number;
    page: number;
    pages: number;
  }>(`/events?${params.toString()}`);

  return response || { events: [], total: 0, page: 1, pages: 0 };
}

/**
 * Get a single event by ID
 */
export async function getEvent(eventId: string): Promise<TimelineEvent | null> {
  return fetchAPI<TimelineEvent | null>(`/events/${eventId}`);
}

/**
 * Get recent events
 */
export async function getRecentEvents(limit: number = 10): Promise<TimelineEvent[]> {
  const response = await fetchAPI<TimelineEvent[]>(`/events/recent?limit=${limit}`);
  return response || [];
}

/**
 * Get events by type
 */
export async function getEventsByType(type: string): Promise<TimelineEvent[]> {
  const response = await fetchAPI<TimelineEvent[]>(`/events/by-type/${type}`);
  return response || [];
}

/**
 * Get events for a specific persona
 */
export async function getEventsByPersona(personaId: string): Promise<TimelineEvent[]> {
  const response = await fetchAPI<TimelineEvent[]>(`/events/by-persona/${personaId}`);
  return response || [];
}

// =============================================================================
// Persona Functions
// =============================================================================

/**
 * Get all personas (summary)
 */
export async function getAllPersonas(): Promise<PersonaSummary[]> {
  const response = await fetchAPI<PersonaSummary[]>('/personas');
  return response || [];
}

/**
 * Get a single persona summary
 */
export async function getPersona(personaId: string): Promise<PersonaSummary | null> {
  return fetchAPI<PersonaSummary | null>(`/personas/${personaId}`);
}

// =============================================================================
// Content Functions
// =============================================================================

/**
 * Get recent published content
 */
export async function getRecentContent(limit: number = 5): Promise<ContentSummary[]> {
  const response = await fetchAPI<ContentSummary[]>(`/content/recent?limit=${limit}`);
  return response || [];
}

/**
 * Get a single content item
 */
export async function getContent(contentId: string): Promise<ContentSummary | null> {
  return fetchAPI<ContentSummary | null>(`/content/${contentId}`);
}

// =============================================================================
// Stats Functions
// =============================================================================

/**
 * Get journal statistics
 */
export async function getJournalStats(): Promise<JournalStats> {
  const stats = await fetchAPI<JournalStats>('/stats');
  return stats || {
    total_events: 0,
    total_personas: 0,
    total_content: 0,
    total_published: 0,
    events_by_type: {},
    events_by_day: [],
  };
}
