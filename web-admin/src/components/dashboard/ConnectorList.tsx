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
      case 'weibo':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M10.098 20.323c-3.977.391-7.414-1.406-7.672-4.02-.259-2.609 2.759-5.047 6.74-5.441 3.979-.394 7.413 1.404 7.671 4.018.259 2.6-2.759 5.049-6.739 5.443zM9.05 17.219c-.384.616-1.208.884-1.829.602-.612-.279-.793-.991-.406-1.593.379-.595 1.176-.861 1.793-.601.622.263.82.972.442 1.592zm1.27-1.627c-.141.237-.449.353-.689.253-.236-.09-.313-.361-.177-.586.138-.227.436-.346.672-.24.239.09.315.36.194.573zm.176-2.719c-1.893-.493-4.033.45-4.857 2.118-.836 1.704-.026 3.591 1.886 4.21 1.983.64 4.318-.341 5.132-2.179.8-1.793-.201-3.642-2.161-4.149zm7.563-1.224c-.346-.105-.577-.176-.4-.638.388-1.022.429-1.903.008-2.532-.789-1.18-2.945-1.116-5.378-.032 0 0-.77.337-.573-.274.377-1.199.32-2.203-.267-2.784-1.334-1.32-4.885.047-7.927 3.06-2.279 2.251-3.6 4.649-3.6 6.73 0 3.973 5.07 6.386 10.042 6.386 6.512 0 10.838-3.784 10.838-6.788 0-1.814-1.527-2.843-2.743-3.128z" />
          </svg>
        );
      case 'zhihu':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5.721 0C2.251 0 0 2.25 0 5.719V18.28C0 21.751 2.252 24 5.721 24h12.56C21.751 24 24 21.75 24 18.281V5.72C24 2.249 21.75 0 18.281 0zM6.95 7.42h4.48v9.458h-.94l-.94.84-1.96-1.18-.48.36v-1.02H6.95zm5.94 0h2.92l.48-1.32.84.24-.24.96h3.12l.6.6c-.36.48-.72 1.08-1.08 1.68h1.56v.72h-8.16v-.72h1.8c.12-.48.24-1.08.36-1.68H10.1zm-.6 5.88h8.16v.72H12.29zm0 2.28h8.16v.72H12.29zm-4.4-8.16v8.28h3.6V7.42z" />
          </svg>
        );
      case 'brave_search':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 0L1.605 6v12L12 24l10.395-6V6zm0 3.6l7.23 4.2-2.572 1.486L12 6.6l-4.658 2.686L4.77 7.8zM4.77 16.2V9.6l4.658 2.686v6.228zm9.888 2.514v-6.228L19.23 9.6v6.6z" />
          </svg>
        );
      case 'bing_search':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M5 3v18l4-2.5V14l6 3.5-6 3.5V12l6 3.5V6.5z" />
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
