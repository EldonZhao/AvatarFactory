'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  saveConnectorConfig,
  deleteConnectorConfig,
  testConnector,
  type ConnectorDetail,
  type ConnectorConfigField,
} from '../../lib/api/client';

interface ConnectorConfigModalProps {
  connector: ConnectorDetail;
  onClose: () => void;
  onSaved: () => void;
}

export function ConnectorConfigModal({ connector, onClose, onSaved }: ConnectorConfigModalProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // Initialize with current values
    const initial: Record<string, string> = {};
    connector.config_fields.forEach((field) => {
      initial[field.name] = connector.current_values[field.name] || '';
    });
    setValues(initial);
  }, [connector]);

  const handleChange = (name: string, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
    setTestResult(null);
    setError(null);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      await saveConnectorConfig(connector.platform, values);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      setError(null);

      // Save first if there are changes
      const hasChanges = connector.config_fields.some(
        (f) => values[f.name] !== connector.current_values[f.name]
      );
      if (hasChanges) {
        await saveConnectorConfig(connector.platform, values);
      }

      const result = await testConnector(connector.platform);
      setTestResult({ status: result.status, message: result.message });
    } catch (err) {
      setTestResult({ status: 'error', message: err instanceof Error ? err.message : 'Test failed' });
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this configuration?')) return;

    try {
      setSaving(true);
      await deleteConnectorConfig(connector.platform);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete configuration');
    } finally {
      setSaving(false);
    }
  };

  const renderField = (field: ConnectorConfigField) => {
    const value = values[field.name] || '';
    const isPassword = field.field_type === 'password';
    const showPwd = showPassword[field.name];

    const baseInputClass = `w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))]
      bg-[hsl(var(--background))] text-[hsl(var(--foreground))]
      focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] focus:border-transparent
      placeholder:text-[hsl(var(--muted-foreground))]`;

    if (field.field_type === 'textarea') {
      return (
        <textarea
          value={value}
          onChange={(e) => handleChange(field.name, e.target.value)}
          placeholder={field.placeholder}
          rows={4}
          className={`${baseInputClass} resize-y`}
        />
      );
    }

    return (
      <div className="relative">
        <input
          type={isPassword && !showPwd ? 'password' : 'text'}
          value={value}
          onChange={(e) => handleChange(field.name, e.target.value)}
          placeholder={field.placeholder}
          className={baseInputClass}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => ({ ...prev, [field.name]: !prev[field.name] }))}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
          >
            {showPwd ? (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
          </button>
        )}
      </div>
    );
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-lg mx-4 bg-[hsl(var(--card))] rounded-xl shadow-xl border border-[hsl(var(--border))] max-h-[90vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-[hsl(var(--border))]">
            <div>
              <h2 className="text-lg font-semibold">{connector.display_name}</h2>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                Configure connection settings
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[hsl(var(--accent))] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {connector.description}
            </p>

            {/* Config Fields */}
            {connector.config_fields.map((field) => (
              <div key={field.name} className="space-y-1.5">
                <label className="block text-sm font-medium">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>
                {field.description && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{field.description}</p>
                )}
                {renderField(field)}
                {field.env_var && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">
                    Environment variable: <code className="bg-[hsl(var(--accent))] px-1 rounded">{field.env_var}</code>
                  </p>
                )}
              </div>
            ))}

            {/* Test Result */}
            {testResult && (
              <div
                className={`p-3 rounded-lg ${
                  testResult.status === 'success'
                    ? 'bg-green-500/10 text-green-600 border border-green-500/20'
                    : 'bg-red-500/10 text-red-600 border border-red-500/20'
                }`}
              >
                <div className="flex items-center gap-2">
                  {testResult.status === 'success' ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                  <span className="font-medium">{testResult.message}</span>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 text-red-600 border border-red-500/20">
                {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-[hsl(var(--border))] flex items-center justify-between">
            <div>
              {connector.configured && (
                <button
                  onClick={handleDelete}
                  disabled={saving}
                  className="px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
                >
                  Delete Config
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleTest}
                disabled={testing || saving}
                className="px-4 py-2 text-sm bg-[hsl(var(--accent))] rounded-lg hover:bg-[hsl(var(--accent))]/80 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {testing && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                Test Connection
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 text-sm bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
              >
                {saving && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
                Save
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
