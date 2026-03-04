// Timeline Event Types for Journal
export interface TimelineEvent {
  id: string;
  type: 'persona_created' | 'persona_updated' | 'content_created' | 'content_published' | 'review_completed' | 'task_scheduled' | 'task_executed';
  timestamp: string;
  title: string;
  description: string;
  persona_id?: string;
  persona_name?: string;
  content_id?: string;
  content?: string;  // Content body for content events
  metadata?: Record<string, unknown>;
}

// Persona summary for display
export interface PersonaSummary {
  id: string;
  name: string;
  tagline: string;
  expertise: string[];
  platforms: string[];
  content_count: number;
  created_at: string | null;
}

// Content summary for display
export interface ContentSummary {
  id: string;
  persona_id: string;
  persona_name: string;
  title: string;
  body: string;
  pillar: string;
  platform: string;
  status: 'draft' | 'published';
  created_at: string;
  review_score?: number;
}

// Global stats for Journal
export interface JournalStats {
  total_events: number;
  total_personas: number;
  total_content: number;
  total_published: number;
  events_by_type: Record<string, number>;
  events_by_day: { date: string; count: number }[];
}
