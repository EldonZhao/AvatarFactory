// Persona Types
export interface Persona {
  id: string;
  version: string;
  created_at: string;
  updated_at: string;
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
  content_pillars: ContentPillar[];
  boundaries: {
    avoid: string[];
    compliance: string[];
  };
  platforms: string[];
  notification?: {
    enabled: boolean;
    connector_type: string;
    notify_on_content: boolean;
    notify_on_review: boolean;
    notify_on_discovery: boolean;
  };
  metadata?: Record<string, unknown>;
}

export interface ContentPillar {
  name: string;
  description: string;
  frequency: string;
  examples: string[];
}

// Content Types
export interface Content {
  id: string;
  persona_id: string;
  created_at: string;
  title: string;
  body: string;
  pillar: string;
  platform: string;
  structure?: {
    sections: string[];
    style_constraints?: Record<string, string>;
  };
  tags: string[];
  metadata?: Record<string, unknown>;
  review_score?: number;
  review_issues?: string[];
  predicted_engagement?: number | null;
  status: 'draft' | 'published';
}

// Review Types
export interface ReviewReport {
  content_id: string;
  reviewed_at: string;
  persona_consistency: ReviewDimension;
  platform_fit: ReviewDimension;
  compliance: ComplianceDimension;
  engagement_potential: ReviewDimension;
  overall_score: number;
  suggestions: {
    critical: string[];
    recommended: string[];
    optional: string[];
  };
}

export interface ReviewDimension {
  score: number;
  issues: string[];
  strengths: string[];
  reasoning: string[];
}

export interface ComplianceDimension {
  score: number;
  risk_level: 'low' | 'medium' | 'high';
  checks: Record<string, 'pass' | 'fail'>;
  issues: string[];
}

// Persona History Types
export interface PersonaVersion {
  version: string;
  timestamp: string;
  changes: string[];
  reason: string;
  expected_impact: string;
  author: string;
  approved: boolean;
}

// Scheduler Types
export interface ScheduledTask {
  id: string;
  name: string;
  task_type: 'discovery' | 'content' | 'trend_scan' | 'persona_recommendation';
  schedule: string;
  enabled: boolean;
  persona_id: string | null;
  platform: string | null;
  extra_params: Record<string, unknown>;
  last_run: string | null;
  last_status: 'success' | 'error' | null;
  last_error: string | null;
  run_count: number;
}

// Timeline Types
export interface TimelineEvent {
  id: string;
  type: 'persona_created' | 'persona_updated' | 'content_created' | 'content_published' | 'review_completed' | 'task_scheduled' | 'task_executed';
  timestamp: string;
  title: string;
  description: string;
  persona_id?: string;
  content_id?: string;
  metadata?: Record<string, unknown>;
}

// Stats Types
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
