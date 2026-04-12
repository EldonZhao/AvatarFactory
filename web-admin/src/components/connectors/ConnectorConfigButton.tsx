'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { ConnectorConfigModal } from './ConnectorConfigModal';
import type { ConnectorDetail } from '../../lib/api/client';

interface ConnectorConfigButtonProps {
  platform: string;
  buttonText?: string;
  className?: string;
}

export function ConnectorConfigButton({ platform, buttonText = 'Configure', className = '' }: ConnectorConfigButtonProps) {
  const [connector, setConnector] = useState<ConnectorDetail | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadConnectorConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/connectors/${platform}`);
      if (response.ok) {
        const data = await response.json();
        setConnector(data);
        setShowModal(true);
      }
    } catch (err) {
      console.error('Failed to load connector config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClick = () => {
    loadConnectorConfig();
  };

  const handleClose = () => {
    setShowModal(false);
    setConnector(null);
  };

  const handleSaved = () => {
    setShowModal(false);
    setConnector(null);
    // Reload the page to reflect changes
    window.location.reload();
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={loading}
        className={className || `inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity text-sm disabled:opacity-50`}
      >
        {loading ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        )}
        {buttonText}
      </button>

      {showModal && connector && (
        <ConnectorConfigModal
          connector={connector}
          onClose={handleClose}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
