'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ScoreRing, ScoreBar } from '../ui/Score';
import { formatDate } from '@/lib/utils';
import type { ReviewReport } from '@/lib/types';

interface ReviewScoreProps {
  review: ReviewReport;
}

export function ReviewScore({ review }: ReviewScoreProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>审核报告</CardTitle>
            <span className="text-sm text-[hsl(var(--muted-foreground))]">
              {formatDate(review.reviewed_at, 'full')}
            </span>
          </div>
        </CardHeader>
        <CardContent>
          {/* Overall Score */}
          <div className="flex justify-center mb-6">
            <ScoreRing score={review.overall_score} size="lg" label="综合评分" />
          </div>

          {/* Dimension Scores */}
          <div className="space-y-4 mb-6">
            <ScoreBar score={review.persona_consistency.score} label="人设一致性" />
            <ScoreBar score={review.platform_fit.score} label="平台适配度" />
            <ScoreBar score={review.compliance.score} label="合规性" />
            <ScoreBar score={review.engagement_potential.score} label="互动潜力" />
          </div>

          {/* Compliance Status */}
          <div className="mb-6">
            <h4 className="text-sm font-medium mb-2">合规检查</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(review.compliance.checks).map(([key, status]) => (
                <Badge
                  key={key}
                  variant={status === 'pass' ? 'success' : 'destructive'}
                  className="text-xs"
                >
                  {key}: {status === 'pass' ? '通过' : '未通过'}
                </Badge>
              ))}
            </div>
            <Badge
              variant={
                review.compliance.risk_level === 'low'
                  ? 'success'
                  : review.compliance.risk_level === 'medium'
                  ? 'warning'
                  : 'destructive'
              }
              className="mt-2"
            >
              风险等级: {review.compliance.risk_level}
            </Badge>
          </div>

          {/* Suggestions */}
          <div className="space-y-4">
            {review.suggestions.critical.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-red-500 mb-2">关键修改</h4>
                <ul className="space-y-1">
                  {review.suggestions.critical.map((s, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">!</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {review.suggestions.recommended.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-yellow-500 mb-2">建议修改</h4>
                <ul className="space-y-1">
                  {review.suggestions.recommended.map((s, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className="text-yellow-500 mt-0.5">•</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {review.suggestions.optional.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-blue-500 mb-2">可选优化</h4>
                <ul className="space-y-1">
                  {review.suggestions.optional.map((s, i) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <span className="text-blue-500 mt-0.5">○</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

interface ReviewDimensionDetailProps {
  title: string;
  dimension: {
    score: number;
    issues: string[];
    strengths: string[];
    reasoning: string[];
  };
}

export function ReviewDimensionDetail({ title, dimension }: ReviewDimensionDetailProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{title}</CardTitle>
          <ScoreRing score={dimension.score} size="sm" showLabel={false} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {dimension.strengths.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-green-500 mb-2">优点</h4>
            <ul className="space-y-1">
              {dimension.strengths.map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-green-500">✓</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {dimension.issues.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-yellow-500 mb-2">问题</h4>
            <ul className="space-y-1">
              {dimension.issues.map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-yellow-500">•</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {dimension.reasoning.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-2">分析</h4>
            <ul className="space-y-1">
              {dimension.reasoning.map((s, i) => (
                <li key={i} className="text-sm text-[hsl(var(--muted-foreground))]">{s}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
