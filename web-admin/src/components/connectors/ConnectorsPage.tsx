'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ConnectorConfigModal } from './ConnectorConfigModal';
import {
  getConnectorsList,
  type ConnectorDetail,
} from '../../lib/api/client';

export function ConnectorsPage() {
  const [connectors, setConnectors] = useState<ConnectorDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedConnector, setSelectedConnector] = useState<ConnectorDetail | null>(null);
  const [filter, setFilter] = useState<'all' | 'configured' | 'unconfigured'>('all');

  const loadConnectors = async () => {
    try {
      setLoading(true);
      const data = await getConnectorsList();
      setConnectors(data.connectors);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load connectors');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConnectors();
  }, []);

  const filteredConnectors = connectors.filter((c) => {
    if (filter === 'configured') return c.configured;
    if (filter === 'unconfigured') return !c.configured;
    return true;
  });

  const getPlatformIcon = (platform: string) => {
    const icons: Record<string, JSX.Element> = {
      bluesky: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2L2 19.5h20L12 2zm0 4l6.5 11.5h-13L12 6z" />
        </svg>
      ),
      twitter: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      ),
      instagram: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
        </svg>
      ),
      linkedin: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
        </svg>
      ),
      threads: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.33-3.024.858-.713 2.042-1.146 3.425-1.252.948-.073 1.889-.03 2.799.128.02-.94-.09-1.753-.332-2.42-.347-.953-1.008-1.478-2.027-1.605-.778-.098-1.483.098-1.975.548l-.137.134c-.251.27-.58.634-1.197.634H9.28c-.494 0-.962-.194-1.32-.544-.359-.352-.557-.822-.557-1.323 0-1.03.838-1.867 1.877-1.867h.002c.26 0 .52.053.76.157.787-.593 1.835-.852 2.972-.852h.091c1.674.027 3.014.625 3.882 1.732.729.929 1.16 2.2 1.288 3.785 1.073.553 1.943 1.307 2.561 2.214.898 1.316 1.178 2.873.833 4.631-.447 2.274-1.702 4.017-3.73 5.181C15.83 23.587 14.1 24 12.186 24zm-.09-7.592c-.09 0-.18.002-.268.007-.763.041-1.347.27-1.688.663-.296.34-.43.779-.396 1.303.06 1.078 1.081 1.678 2.73 1.589 1.048-.057 1.857-.41 2.405-1.05.368-.43.64-1.003.817-1.72-.553-.1-1.104-.182-1.64-.24-.643-.07-1.29-.092-1.96-.067v-.485z" />
        </svg>
      ),
      mastodon: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 0 0 .023-.043v-1.809a.052.052 0 0 0-.02-.041.053.053 0 0 0-.046-.01 20.282 20.282 0 0 1-4.709.545c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 0 1-.319-1.433.053.053 0 0 1 .066-.054c1.517.363 3.072.546 4.632.546.376 0 .75 0 1.125-.01 1.57-.044 3.224-.124 4.768-.422.038-.008.077-.015.11-.024 2.435-.464 4.753-1.92 4.989-5.604.008-.145.03-1.52.03-1.67.002-.512.167-3.63-.024-5.545zm-3.748 9.195h-2.561V8.29c0-1.309-.55-1.976-1.67-1.976-1.23 0-1.846.79-1.846 2.35v3.403h-2.546V8.663c0-1.56-.617-2.35-1.848-2.35-1.112 0-1.668.668-1.67 1.977v6.218H4.822V8.102c0-1.31.337-2.35 1.011-3.12.696-.77 1.608-1.164 2.74-1.164 1.311 0 2.302.5 2.962 1.498l.638 1.06.638-1.06c.66-.999 1.65-1.498 2.96-1.498 1.13 0 2.043.395 2.74 1.164.675.77 1.012 1.81 1.012 3.12z" />
        </svg>
      ),
      weibo: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M10.098 20.323c-3.977.391-7.414-1.406-7.672-4.02-.259-2.609 2.759-5.047 6.74-5.441 3.979-.394 7.413 1.404 7.671 4.018.259 2.6-2.759 5.049-6.739 5.443z" />
        </svg>
      ),
      xiaohongshu: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z" />
        </svg>
      ),
      wecom: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
        </svg>
      ),
      brave_search: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0L1.605 6v12L12 24l10.395-6V6zm0 3.6l7.23 4.2-2.572 1.486L12 6.6l-4.658 2.686L4.77 7.8z" />
        </svg>
      ),
      bing_search: (
        <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
          <path d="M5 3v18l4-2.5V14l6 3.5-6 3.5V12l6 3.5V6.5z" />
        </svg>
      ),
    };
    return icons[platform.toLowerCase()] || (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    );
  };

  const getCapabilityBadges = (connector: ConnectorDetail) => {
    const badges = [];
    if (connector.supports_publishing) {
      badges.push(<Badge key="pub" variant="secondary" className="text-xs">Publishing</Badge>);
    }
    if (connector.supports_topic_discovery) {
      badges.push(<Badge key="topic" variant="secondary" className="text-xs">Topics</Badge>);
    }
    if (connector.supports_persona_discovery) {
      badges.push(<Badge key="persona" variant="secondary" className="text-xs">Personas</Badge>);
    }
    if (connector.supports_fetching) {
      badges.push(<Badge key="fetch" variant="secondary" className="text-xs">Fetching</Badge>);
    }
    return badges;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[hsl(var(--primary))]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-red-500">
            <p>{error}</p>
            <button
              onClick={loadConnectors}
              className="mt-4 px-4 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg"
            >
              Retry
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const configuredCount = connectors.filter((c) => c.configured).length;
  const hasPersonaDiscovery = connectors.some((c) => c.configured && c.supports_persona_discovery);

  return (
    <>
      <div className="space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101" />
                  </svg>
                </div>
                <div>
                  <p className="text-2xl font-bold">{connectors.length}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Total Connectors</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <p className="text-2xl font-bold">{configuredCount}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Configured</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div>
                  <p className="text-2xl font-bold">{connectors.length - configuredCount}</p>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">Not Configured</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recommended Personas Card */}
          <Card
            className={`cursor-pointer transition-colors ${hasPersonaDiscovery ? 'hover:border-[hsl(var(--primary))]' : 'opacity-60'}`}
            onClick={() => hasPersonaDiscovery && (window.location.href = '/recommendations')}
          >
            <CardContent className="py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold">推荐 Personas</p>
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    {hasPersonaDiscovery ? '查看发现的推荐' : '需要配置 Connector'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filter */}
        <div className="flex gap-2">
          {(['all', 'configured', 'unconfigured'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                  : 'bg-[hsl(var(--accent))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--accent))]/80'
              }`}
            >
              {f === 'all' ? 'All' : f === 'configured' ? 'Configured' : 'Not Configured'}
            </button>
          ))}
        </div>

        {/* Connector Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {filteredConnectors.map((connector, index) => (
              <motion.div
                key={connector.platform}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.2, delay: index * 0.05 }}
              >
                <Card
                  className="cursor-pointer hover:border-[hsl(var(--primary))] transition-colors"
                  onClick={() => setSelectedConnector(connector)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                          connector.configured
                            ? 'bg-green-500/10 text-green-500'
                            : 'bg-[hsl(var(--accent))] text-[hsl(var(--muted-foreground))]'
                        }`}>
                          {getPlatformIcon(connector.platform)}
                        </div>
                        <div>
                          <h3 className="font-semibold">{connector.display_name}</h3>
                          <p className="text-xs text-[hsl(var(--muted-foreground))]">
                            {connector.platform}
                          </p>
                        </div>
                      </div>
                      <Badge variant={connector.configured ? 'success' : 'secondary'}>
                        {connector.configured ? 'Configured' : 'Not Set'}
                      </Badge>
                    </div>

                    <p className="text-sm text-[hsl(var(--muted-foreground))] mb-3 line-clamp-2">
                      {connector.description}
                    </p>

                    <div className="flex flex-wrap gap-1">
                      {getCapabilityBadges(connector)}
                    </div>

                    {connector.config_source && (
                      <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">
                        Source: {connector.config_source === 'env' ? 'Environment Variables' : 'Local Config'}
                      </p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Config Modal */}
      {selectedConnector && (
        <ConnectorConfigModal
          connector={selectedConnector}
          onClose={() => setSelectedConnector(null)}
          onSaved={() => {
            setSelectedConnector(null);
            loadConnectors();
          }}
        />
      )}
    </>
  );
}
