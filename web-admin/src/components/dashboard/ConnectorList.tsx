'use client';

import * as React from 'react';
import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ConnectorConfigModal } from '../connectors/ConnectorConfigModal';
import {
  getConnectorConfig,
  type ConnectorDetail,
} from '../../lib/api/client';

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

export function ConnectorList({ connectors: initialConnectors, title = 'Connector 状态' }: ConnectorListProps) {
  const [connectors, setConnectors] = useState(initialConnectors);
  const [selectedConnector, setSelectedConnector] = useState<ConnectorDetail | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

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
      case 'linkedin':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
          </svg>
        );
      case 'threads':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.332-3.023.9-.746 2.13-1.178 3.462-1.215 1.078-.03 2.07.137 2.954.5.026-.447.014-.91-.034-1.392-.112-1.13-.489-1.97-1.087-2.425-.637-.485-1.59-.73-2.833-.73h-.025c-.996.006-2.121.239-2.848.658l-.97-1.716c1.017-.583 2.44-.9 3.848-.91h.031c1.788 0 3.212.46 4.23 1.368 1.098.978 1.7 2.397 1.738 4.103.008.337.004.682-.01 1.034a8.1 8.1 0 0 1 2.145 1.625c.9 1.023 1.36 2.31 1.326 3.72-.024.99-.277 1.927-.779 2.79-.527.909-1.29 1.678-2.27 2.288-1.583.983-3.602 1.49-6.003 1.506zm-.14-8.198c-.984.027-1.807.272-2.378.706-.507.386-.766.9-.728 1.445.036.527.31.989.767 1.3.515.351 1.254.535 2.134.49 1.087-.059 1.91-.455 2.482-1.163.508-.629.788-1.473.87-2.477-.96-.327-2.003-.329-3.148-.301z" />
          </svg>
        );
      case 'instagram':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
          </svg>
        );
      case 'mastodon':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 00.023-.043v-1.809a.052.052 0 00-.02-.041.053.053 0 00-.046-.01 20.282 20.282 0 01-4.709.545c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 01-.319-1.433.053.053 0 01.066-.054c1.517.363 3.072.546 4.632.546.376 0 .75 0 1.125-.01 1.57-.044 3.224-.124 4.768-.422.038-.008.077-.015.11-.024 2.435-.464 4.753-1.92 4.989-5.604.008-.145.03-1.52.03-1.67.002-.512.167-3.63-.024-5.545zm-3.748 9.195h-2.561V8.29c0-1.309-.55-1.976-1.67-1.976-1.23 0-1.846.79-1.846 2.35v3.403h-2.546V8.663c0-1.56-.617-2.35-1.848-2.35-1.112 0-1.668.668-1.668 1.977v6.218H4.822V8.102c0-1.31.337-2.35 1.011-3.12.696-.77 1.608-1.164 2.74-1.164 1.311 0 2.302.5 2.962 1.498l.638 1.06.638-1.06c.66-.999 1.65-1.498 2.96-1.498 1.13 0 2.043.395 2.74 1.164.675.77 1.012 1.81 1.012 3.12z" />
          </svg>
        );
      case 'toutiao':
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9v-2h2v2zm0-4H9V7h2v5zm4 4h-2v-2h2v2zm0-4h-2V7h2v5z" />
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

  const handleConnectorClick = useCallback(async (platform: string) => {
    try {
      setLoading(platform);
      const detail = await getConnectorConfig(platform);
      setSelectedConnector(detail);
    } catch (error) {
      console.error('Failed to load connector config:', error);
    } finally {
      setLoading(null);
    }
  }, []);

  const handleModalClose = useCallback(() => {
    setSelectedConnector(null);
  }, []);

  const handleConfigSaved = useCallback(async () => {
    // Refresh the connector status after saving
    if (selectedConnector) {
      try {
        const detail = await getConnectorConfig(selectedConnector.platform);
        // Update local state
        setConnectors((prev) =>
          prev.map((c) =>
            c.platform === detail.platform ? { ...c, configured: detail.configured } : c
          )
        );
      } catch (error) {
        console.error('Failed to refresh connector status:', error);
      }
    }
    setSelectedConnector(null);
  }, [selectedConnector]);

  return (
    <>
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
                <motion.button
                  key={connector.platform}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  onClick={() => handleConnectorClick(connector.platform)}
                  disabled={loading === connector.platform}
                  className="w-full flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--accent))] hover:bg-[hsl(var(--accent))]/80 transition-colors cursor-pointer disabled:opacity-50 text-left"
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
                  <div className="flex items-center gap-2">
                    {loading === connector.platform ? (
                      <svg className="w-4 h-4 animate-spin text-[hsl(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4 text-[hsl(var(--muted-foreground))]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    )}
                    <Badge variant={connector.configured ? 'success' : 'secondary'}>
                      {connector.configured ? '已配置' : '未配置'}
                    </Badge>
                  </div>
                </motion.button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Config Modal */}
      {selectedConnector && (
        <ConnectorConfigModal
          connector={selectedConnector}
          onClose={handleModalClose}
          onSaved={handleConfigSaved}
        />
      )}
    </>
  );
}
