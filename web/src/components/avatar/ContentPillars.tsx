'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { ContentPillar } from '@/lib/types';

interface ContentPillarsProps {
  pillars: ContentPillar[];
}

export function ContentPillars({ pillars }: ContentPillarsProps) {
  const frequencyColors: Record<string, 'default' | 'success' | 'warning' | 'info'> = {
    daily: 'success',
    weekly: 'info',
    monthly: 'warning',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>内容支柱</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {pillars.map((pillar, index) => (
            <motion.div
              key={pillar.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="p-4 rounded-lg bg-[hsl(var(--muted))] space-y-3"
            >
              <div className="flex items-center justify-between">
                <h4 className="font-medium">{pillar.name}</h4>
                <Badge variant={frequencyColors[pillar.frequency] || 'secondary'}>
                  {pillar.frequency}
                </Badge>
              </div>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {pillar.description}
              </p>
              {pillar.examples.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">示例:</p>
                  <ul className="space-y-1">
                    {pillar.examples.map((example, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <span className="text-[hsl(var(--primary))]">•</span>
                        <span>{example}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
