'use client';

import * as React from 'react';
import { useState } from 'react';

export interface VersionEntry {
  version: string;
  timestamp?: string;
  changes?: string[];
  author?: string;
  is_current?: boolean;
}

interface VersionHistoryProps {
  versions: VersionEntry[];
  personaId: string;
  onRollback?: (version: string) => void;
}

export function VersionHistory({ versions, personaId, onRollback }: VersionHistoryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [rollingBack, setRollingBack] = useState<string | null>(null);

  const handleRollback = async (version: string) => {
    if (!confirm(`确定要回滚到版本 ${version} 吗？此操作不可撤销。`)) return;

    setRollingBack(version);
    try {
      const response = await fetch(`/api/admin/personas/${personaId}/evolution/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_version: version }),
      });

      if (response.ok) {
        onRollback?.(version);
        // Reload page to show updated state
        window.location.reload();
      } else {
        const data = await response.json();
        alert(data.detail || '回滚失败');
      }
    } catch (e) {
      alert('回滚失败: ' + e);
    } finally {
      setRollingBack(null);
    }
  };

  if (versions.length === 0) {
    return (
      <div className="text-center py-8 text-[hsl(var(--muted-foreground))]">
        暂无版本历史
      </div>
    );
  }

  const displayVersions = isExpanded ? versions : versions.slice(0, 5);

  return (
    <div className="space-y-4">
      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-[7px] top-3 bottom-3 w-0.5 bg-[hsl(var(--border))]" />

        <div className="space-y-3">
          {displayVersions.map((entry, index) => (
            <div key={entry.version} className="relative flex items-start gap-4 pl-6">
              {/* Timeline dot */}
              <div
                className={`absolute left-0 w-3.5 h-3.5 rounded-full border-2 ${
                  index === 0
                    ? 'bg-green-500 border-green-500'
                    : 'bg-[hsl(var(--card))] border-[hsl(var(--muted-foreground))]'
                }`}
              />

              {/* Content */}
              <div className="flex-1 p-3 rounded-lg bg-[hsl(var(--accent))]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{entry.version}</span>
                    {index === 0 && (
                      <span className="px-2 py-0.5 text-xs rounded bg-green-500/10 text-green-600 border border-green-500/20">
                        当前
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {entry.timestamp && (
                      <span className="text-xs text-[hsl(var(--muted-foreground))]">
                        {new Date(entry.timestamp).toLocaleString('zh-CN')}
                      </span>
                    )}
                    {index !== 0 && (
                      <button
                        onClick={() => handleRollback(entry.version)}
                        disabled={rollingBack !== null}
                        className="text-xs text-[hsl(var(--primary))] hover:underline disabled:opacity-50"
                      >
                        {rollingBack === entry.version ? '回滚中...' : '回滚'}
                      </button>
                    )}
                  </div>
                </div>

                {entry.changes && entry.changes.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {entry.changes.map((change, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                        <span className="text-[hsl(var(--primary))]">•</span>
                        <span>{change}</span>
                      </li>
                    ))}
                  </ul>
                )}

                {entry.author && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">
                    by {entry.author}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Show more/less */}
      {versions.length > 5 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full py-2 text-sm text-[hsl(var(--primary))] hover:underline"
        >
          {isExpanded ? '收起' : `显示全部 ${versions.length} 个版本`}
        </button>
      )}
    </div>
  );
}
