import * as React from 'react';
import { cn, getScoreColor, getScoreBgColor } from '@/lib/utils';

interface ScoreRingProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
}

export function ScoreRing({ score, size = 'md', showLabel = true, label }: ScoreRingProps) {
  const sizes = {
    sm: { width: 48, stroke: 4, fontSize: 'text-xs' },
    md: { width: 64, stroke: 5, fontSize: 'text-sm' },
    lg: { width: 96, stroke: 6, fontSize: 'text-lg' },
  };

  const { width, stroke, fontSize } = sizes[size];
  const radius = (width - stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width, height: width }}>
        <svg className="transform -rotate-90" width={width} height={width}>
          {/* Background circle */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth={stroke}
          />
          {/* Progress circle */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={score >= 90 ? '#22c55e' : score >= 75 ? '#3b82f6' : score >= 60 ? '#eab308' : '#ef4444'}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className={cn('absolute inset-0 flex items-center justify-center font-bold', fontSize, getScoreColor(score))}>
          {score}
        </div>
      </div>
      {showLabel && label && (
        <span className="text-xs text-[hsl(var(--muted-foreground))]">{label}</span>
      )}
    </div>
  );
}

interface ScoreBarProps {
  score: number;
  label: string;
  showScore?: boolean;
}

export function ScoreBar({ score, label, showScore = true }: ScoreBarProps) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-[hsl(var(--muted-foreground))]">{label}</span>
        {showScore && <span className={cn('font-medium', getScoreColor(score))}>{score}</span>}
      </div>
      <div className="h-2 rounded-full bg-[hsl(var(--muted))] overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-1000 ease-out',
            score >= 90 ? 'bg-green-500' : score >= 75 ? 'bg-blue-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
          )}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md';
}

export function ScoreBadge({ score, size = 'md' }: ScoreBadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-lg border font-bold',
        getScoreBgColor(score),
        getScoreColor(score),
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      )}
    >
      {score}
    </div>
  );
}
