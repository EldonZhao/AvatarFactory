'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface ConnectorStatus {
  platform: string;
  configured: boolean;
  connected?: boolean;
  description?: string;
  last_checked?: string;
}

interface ConnectorListProps {
  connectors: ConnectorStatus[];
  title?: string;
}

export function ConnectorList({ connectors, title = 'Connector 状态' }: ConnectorListProps) {
  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'bluesky':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 19.5h20L12 2zm0 4l6.5 11.5h-13L12 6z" />
          </svg>
        );
      case 'twitter':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
          </svg>
        );
      case 'xiaohongshu':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z" />
          </svg>
        );
      case 'wecom':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        );
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {connectors.length === 0 ? (
          <p className="text-center py-8 text-[hsl(var(--muted-foreground))]">暂无连接器</p>
        ) : (
          <div className="space-y-2">
            {connectors.map((connector, index) => (
              <motion.div
                key={connector.platform}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--accent))]"
              >
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${connector.configured ? 'bg-green-500' : 'bg-gray-400'}`} />
                  <div className="flex items-center gap-2">
                    <span className="text-[hsl(var(--muted-foreground))]">
                      {getPlatformIcon(connector.platform)}
                    </span>
                    <div>
                      <p className="font-medium capitalize">{connector.platform}</p>
                      {connector.description && (
                        <p className="text-xs text-[hsl(var(--muted-foreground))]">{connector.description}</p>
                      )}
                    </div>
                  </div>
                </div>
                <Badge variant={connector.configured ? 'success' : 'secondary'}>
                  {connector.configured ? '已配置' : '未配置'}
                </Badge>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
