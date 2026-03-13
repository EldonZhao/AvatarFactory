'use client';

import * as React from 'react';
import { useState } from 'react';
import { Badge } from '../ui/Badge';
import { cn } from '@/lib/utils';

export interface EvolutionSuggestion {
  id: string;
  target: 'persona' | 'content_agent' | 'review_agent' | 'discovery_agent';
  area: string;
  severity: 'minor' | 'moderate' | 'major';
  confidence: number;
  summary: string;
  current_value?: any;
  proposed_value?: any;
  rationale?: string;
  expected_impact?: string;
  evidence?: string[];
  status: 'pending' | 'approved' | 'rejected' | 'auto_applied';
  created_at?: string;
}

interface SuggestionCardProps {
  suggestion: EvolutionSuggestion;
  personaId: string;
  onStatusChange?: (id: string, newStatus: string) => void;
}

const targetColors: Record<string, string> = {
  persona: 'bg-purple-500/10 text-purple-600 border-purple-500/20',
  content_agent: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  review_agent: 'bg-cyan-500/10 text-cyan-600 border-cyan-500/20',
  discovery_agent: 'bg-orange-500/10 text-orange-600 border-orange-500/20',
};

const severityColors: Record<string, string> = {
  minor: 'bg-green-500/10 text-green-600 border-green-500/20',
  moderate: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
  major: 'bg-red-500/10 text-red-600 border-red-500/20',
};

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
  approved: 'bg-green-500/10 text-green-600 border-green-500/20',
  rejected: 'bg-red-500/10 text-red-600 border-red-500/20',
  auto_applied: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
};

const statusLabels: Record<string, string> = {
  pending: '待审核',
  approved: '已批准',
  rejected: '已拒绝',
  auto_applied: '自动应用',
};

export function SuggestionCard({ suggestion, personaId, onStatusChange }: SuggestionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleReview = async (approved: boolean) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        `/api/admin/personas/${personaId}/evolution/suggestions/${suggestion.id}/review`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approved }),
        }
      );
      if (response.ok) {
        onStatusChange?.(suggestion.id, approved ? 'approved' : 'rejected');
      } else {
        alert('操作失败');
      }
    } catch (e) {
      alert('操作失败: ' + e);
    } finally {
      setIsLoading(false);
    }
  };

  const formatValue = (value: any): string => {
    if (value === undefined || value === null) return '(空)';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] overflow-hidden">
      {/* Header - Always visible */}
      <div
        className="p-4 cursor-pointer hover:bg-[hsl(var(--accent))]/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start gap-3">
          {/* Expand indicator */}
          <svg
            className={cn(
              'w-4 h-4 text-[hsl(var(--muted-foreground))] shrink-0 mt-1 transition-transform',
              isExpanded && 'rotate-90'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>

          <div className="flex-1 min-w-0">
            {/* Badges row */}
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className={cn('px-2 py-0.5 text-xs rounded border', targetColors[suggestion.target])}>
                {suggestion.target.replace('_', ' ')}
              </span>
              <span className={cn('px-2 py-0.5 text-xs rounded border', severityColors[suggestion.severity])}>
                {suggestion.severity}
              </span>
              <span className="px-2 py-0.5 text-xs rounded bg-[hsl(var(--accent))] text-[hsl(var(--muted-foreground))]">
                {suggestion.area}
              </span>
              <span className={cn('px-2 py-0.5 text-xs rounded border', statusColors[suggestion.status])}>
                {statusLabels[suggestion.status]}
              </span>
            </div>

            {/* Summary */}
            <p className="text-sm font-medium text-[hsl(var(--foreground))]">{suggestion.summary}</p>

            {/* Confidence bar */}
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-[hsl(var(--muted-foreground))]">置信度</span>
              <div className="flex-1 h-1.5 rounded-full bg-[hsl(var(--accent))] overflow-hidden max-w-[100px]">
                <div
                  className="h-full bg-[hsl(var(--primary))] rounded-full"
                  style={{ width: `${suggestion.confidence * 100}%` }}
                />
              </div>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                {Math.round(suggestion.confidence * 100)}%
              </span>
            </div>
          </div>

          {/* Actions for pending suggestions */}
          {suggestion.status === 'pending' && (
            <div className="flex gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => handleReview(true)}
                disabled={isLoading}
                className="px-3 py-1.5 text-sm rounded-lg bg-green-500/10 text-green-600 hover:bg-green-500/20 transition-colors disabled:opacity-50"
              >
                批准
              </button>
              <button
                onClick={() => handleReview(false)}
                disabled={isLoading}
                className="px-3 py-1.5 text-sm rounded-lg bg-red-500/10 text-red-600 hover:bg-red-500/20 transition-colors disabled:opacity-50"
              >
                拒绝
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-0 border-t border-[hsl(var(--border))] space-y-4">
          {/* Current vs Proposed */}
          {(suggestion.current_value !== undefined || suggestion.proposed_value !== undefined) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">当前值</p>
                <pre className="p-3 rounded-lg bg-red-500/5 text-sm overflow-x-auto whitespace-pre-wrap break-words border border-red-500/10">
                  {formatValue(suggestion.current_value)}
                </pre>
              </div>
              <div>
                <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">建议值</p>
                <pre className="p-3 rounded-lg bg-green-500/5 text-sm overflow-x-auto whitespace-pre-wrap break-words border border-green-500/10">
                  {formatValue(suggestion.proposed_value)}
                </pre>
              </div>
            </div>
          )}

          {/* Rationale */}
          {suggestion.rationale && (
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">理由</p>
              <p className="text-sm text-[hsl(var(--foreground))]">{suggestion.rationale}</p>
            </div>
          )}

          {/* Expected Impact */}
          {suggestion.expected_impact && (
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">预期影响</p>
              <p className="text-sm text-[hsl(var(--foreground))]">{suggestion.expected_impact}</p>
            </div>
          )}

          {/* Evidence */}
          {suggestion.evidence && suggestion.evidence.length > 0 && (
            <div>
              <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">依据</p>
              <ul className="space-y-1">
                {suggestion.evidence.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-[hsl(var(--primary))]">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SuggestionListProps {
  suggestions: EvolutionSuggestion[];
  personaId: string;
  onStatusChange?: (id: string, newStatus: string) => void;
}

export function SuggestionList({ suggestions, personaId, onStatusChange }: SuggestionListProps) {
  if (suggestions.length === 0) {
    return (
      <div className="text-center py-12 text-[hsl(var(--muted-foreground))]">
        暂无演进建议
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {suggestions.map((suggestion) => (
        <SuggestionCard
          key={suggestion.id}
          suggestion={suggestion}
          personaId={personaId}
          onStatusChange={onStatusChange}
        />
      ))}
    </div>
  );
}
