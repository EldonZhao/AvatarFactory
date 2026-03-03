'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatDate } from '@/lib/utils';
import type { PersonaVersion } from '@/lib/types';

interface VersionHistoryProps {
  versions: PersonaVersion[];
}

export function VersionHistory({ versions }: VersionHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>版本历史</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-[hsl(var(--border))]" />

          <div className="space-y-6">
            {versions.map((version, index) => (
              <motion.div
                key={version.version}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="relative pl-8"
              >
                {/* Timeline dot */}
                <div className="absolute left-0 top-1 w-6 h-6 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-white" />
                </div>

                <div className="p-4 rounded-lg bg-[hsl(var(--muted))]">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{version.version}</Badge>
                      {version.approved && (
                        <Badge variant="success">已批准</Badge>
                      )}
                    </div>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      {formatDate(version.timestamp, 'full')}
                    </span>
                  </div>

                  <div className="space-y-2">
                    <div>
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">变更:</span>
                      <ul className="mt-1 space-y-0.5">
                        {version.changes.map((change, i) => (
                          <li key={i} className="text-sm flex items-start gap-2">
                            <span className="text-green-500">+</span>
                            <span>{change}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {version.reason && (
                      <div>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">原因:</span>
                        <p className="text-sm mt-0.5">{version.reason}</p>
                      </div>
                    )}

                    {version.expected_impact && (
                      <div>
                        <span className="text-xs text-[hsl(var(--muted-foreground))]">预期影响:</span>
                        <p className="text-sm mt-0.5">{version.expected_impact}</p>
                      </div>
                    )}

                    <div className="pt-2 text-xs text-[hsl(var(--muted-foreground))]">
                      由 {version.author} 创建
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
